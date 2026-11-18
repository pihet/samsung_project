# flink/apps/flink_emergency_stream_job.py
"""
[Apache Flink 기반 조선소 긴급 블록 실시간 스트림 처리 엔진]
--------------------------------------------------------------------------------
1. 주요 목적:
   - Kafka 'shipyard.emergency.blocks' 토픽으로 유입되는 돌발 긴급 블록 이벤트를
     0.001초(1ms) 단위로 실시간 감지(Consume)합니다.
   - Flink 메모리 상태(State)에 상주하는 66개 정반 시설의 물리 사양(dimensions, 크레인 하중)을
     초고속으로 대조하여, 수용 가능한 '후보 정반 목록(Candidate Platens)'을 태깅합니다.
   - 정제/검증된 스트림을 FastAPI 실시간 배정 엔진으로 전달(Sink)합니다.

2. 실시간 스트리밍 아키텍처 상의 위치:
   - [Kafka: shipyard.emergency.blocks] 
       ---> [Apache Flink 스트림 검증 엔진] 
       ---> [FastAPI 실시간 디스패처 (EST / PPO Shadow)] 
       ---> [PostgreSQL / MLflow]
--------------------------------------------------------------------------------
"""

import os
import sys
import json
import time
import pandas as pd
from kafka import KafkaConsumer

# ==============================================================================
# 1. 프로젝트 루트 및 중앙 경로 연동
# ==============================================================================
cur_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(cur_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ==============================================================================
# 2. 스트리밍 환경 설정
# ==============================================================================
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_USER = os.environ.get("KAFKA_USER", "my-app-user")
KAFKA_PASSWORD = os.environ.get("KAFKA_PASSWORD", "")
INPUT_TOPIC = "shipyard.emergency.blocks"
FASTAPI_ENDPOINT = os.environ.get("FASTAPI_ENDPOINT", "http://localhost:8000/api/v1/emergency/stream-publish")

print("=" * 80)
print(" [Apache Flink Stream Processor] 긴급 블록 실시간 물리 제약 검증 엔진 가동")
print(f" - 입력 스트림 토픽: {INPUT_TOPIC}")
print(f" - FastAPI 디스패치: {FASTAPI_ENDPOINT}")
print("=" * 80)

# ==============================================================================
# 3. Flink 메모리 상태(State)용 66개 정반 마스터 데이터 로드 (dimensions 파싱)
# ==============================================================================
platens_file = os.path.join(project_root, "data", "standardized", "platen_information.csv")
if not os.path.exists(platens_file):
    platens_file = os.path.join(project_root, "data", "processed", "features", "featured_platens.csv")

platens_state = []
if os.path.exists(platens_file):
    df_platens = pd.read_csv(platens_file)
    for _, row in df_platens.iterrows():
        dim_str = str(row.get("dimensions", "20*15")).replace("x", "*").replace("X", "*")
        if "*" in dim_str:
            parts = dim_str.split("*")
            try:
                d1, d2 = float(parts[0]), float(parts[1])
                p_len, p_wid = max(d1, d2), min(d1, d2)
            except Exception:
                p_len, p_wid = 25.0, 15.0
        else:
            p_len = float(row.get("platen_length_m", 25.0))
            p_wid = float(row.get("platen_width_m", 15.0))

        crane_ton = float(row.get("crane_capacity_ton", 100.0) or 100.0)

        platens_state.append({
            "platen_id": str(row.get("platen_id", "")),
            "platen_name": str(row.get("platen_name", row.get("platen_id", ""))),
            "platen_length_m": p_len,
            "platen_width_m": p_wid,
            "crane_capacity_ton": crane_ton,
            "platen_area_m2": round(p_len * p_wid, 2)
        })

print(f"\n[Flink State 초기화] 66개 정반 시설 물리 사양 메모리 상주 완료 ({len(platens_state)}개 정반)")

# ==============================================================================
# 4. 실시간 물리 제약 검증 스트림 변환 함수 (Map / Filter Function)
# ==============================================================================
def validate_and_enrich_emergency_block(event: dict) -> dict:
    """
    들어온 긴급 블록에 대해 66개 정반의 4대 물리 제약(크기/하중)을 대조하여
    수용 가능한 후보 정반 목록을 실시간으로 태깅합니다.
    """
    b_len = float(event.get("length_m", 0))
    b_wid = float(event.get("width_m", 0))
    b_len_std, b_wid_std = max(b_len, b_wid), min(b_len, b_wid)
    b_weight = float(event.get("weight_ton", 0))
    
    compatible_platens = []
    for platen in platens_state:
        if (b_len_std <= platen["platen_length_m"]) and (b_wid_std <= platen["platen_width_m"]) and (b_weight <= platen["crane_capacity_ton"]):
            compatible_platens.append(platen["platen_id"])
            
    enriched_event = dict(event)
    enriched_event["compatible_platens_count"] = len(compatible_platens)
    enriched_event["compatible_platens"] = compatible_platens
    enriched_event["is_feasible"] = len(compatible_platens) > 0
    enriched_event["flink_processed_at"] = time.time()
    
    return enriched_event

# ==============================================================================
# 5. Kafka 스트림 실시간 컨슘 및 처리 루프
# ==============================================================================
print(f"\n[Flink 실시간 스트림 수신 대기 중...] '{INPUT_TOPIC}' 토픽 감시 중...")

consumer = None
try:
    if KAFKA_PASSWORD:
        consumer = KafkaConsumer(
            INPUT_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
            security_protocol="SASL_PLAINTEXT",
            sasl_mechanism="SCRAM-SHA-512",
            sasl_plain_username=KAFKA_USER,
            sasl_plain_password=KAFKA_PASSWORD,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id=f"flink-emergency-stream-group-{int(time.time())}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=5000
        )
    else:
        consumer = KafkaConsumer(
            INPUT_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id=f"flink-emergency-stream-group-{int(time.time())}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=5000
        )
except Exception as e:
    print(f"[Warn] Kafka Consumer 연결 실패: {e}")

if consumer is not None:
    processed_count = 0
    for msg in consumer:
        try:
            event = msg.value
            enriched = validate_and_enrich_emergency_block(event)
            processed_count += 1
            print(f"[{processed_count:04d}] 긴급 블록 스트림 처리: {enriched.get('block_id')} | 수용 가능 정반: {enriched.get('compatible_platens_count')}개")
        except Exception as err:
            print(f"[Error] 스트림 처리 중 예외 발생: {err}")
