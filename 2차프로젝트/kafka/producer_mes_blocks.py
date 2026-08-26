# kafka/producer_mes_blocks.py
"""
[조선소 MES 생산계획 시스템 Kafka 모의 프로듀서]
--------------------------------------------------------------------------------
1. 주요 목적:
   - 조선소 MES(제조실행시스템)에서 발행되는 원천 블록 생산 계획 및 정반 마스터 데이터를
     Apache Kafka 이벤트 브로커로 전송(Produce)합니다.
   - 대상 토픽:
     1) shipyard.mes.blocks  : 872개 블록 사양 및 일정 이벤트
     2) shipyard.mes.platens : 66개 작업 정반 시설 마스터 이벤트
   - 보안 인증: SASL_PLAINTEXT (SCRAM-SHA-512)

2. 데이터 아키텍처 상의 위치:
   - [MES / 생산계획 시스템] -> Apache Kafka -> MinIO/Iceberg -> Spark
--------------------------------------------------------------------------------
"""

import os
import sys
import json
import time
import pandas as pd
from kafka import KafkaProducer

# ==============================================================================
# 1. 프로젝트 루트 경로 및 중앙 경로(utils.paths) 연동
# ==============================================================================
cur_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(cur_dir)
sys.path.append(project_root)

from utils.paths import STANDARDIZED_DIR

# ==============================================================================
# 2. Kafka 연결 및 인증 설정
# ==============================================================================
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_USER = os.environ.get("KAFKA_USER", "my-app-user")
KAFKA_PASSWORD = os.environ.get("KAFKA_PASSWORD", "uk2eajtu8WM5lGgAemy5F8l3qoJh5mwz")

print("=" * 80)
print(" 조선소 MES 생산계획 시스템 -> Kafka 이벤트 프로듀서 가동")
print("=" * 80)

# ------------------------------------------------------------------------------
# 3. Kafka Producer 인스턴스 생성 (SCRAM-SHA-512 보안 연결)
# ------------------------------------------------------------------------------
print(f"\n[Step 1/3] Kafka 브로커({KAFKA_BOOTSTRAP}) 연결 중...")

try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        security_protocol="SASL_PLAINTEXT",
        sasl_mechanism="SCRAM-SHA-512",
        sasl_plain_username=KAFKA_USER,
        sasl_plain_password=KAFKA_PASSWORD,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        acks="all",
        retries=3
    )
    print(" -> Kafka 브로커 인증 및 Producer 연결 성공!")
except Exception as e:
    # 인증 없이 연결 시도 (로컬 평문 포트포워딩 대비)
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8")
        )
        print(" -> Kafka 브로커 일반 연결 성공!")
    except Exception as err:
        print(f"[오류] Kafka 브로커에 연결할 수 없습니다: {err}")
        print("포트포워딩 상태를 확인해 주세요: pfstart")
        sys.exit(1)

# ==============================================================================
# 4. 원천 블록 및 정반 데이터 로드
# ==============================================================================
print("\n[Step 2/3] MES 원천 표준 데이터셋 로드...")
blocks_file = os.path.join(STANDARDIZED_DIR, "standardized_blocks.csv")
platens_file = os.path.join(STANDARDIZED_DIR, "standardized_platens.csv")

df_blocks = pd.read_csv(blocks_file)
df_platens = pd.read_csv(platens_file)

print(f" - 발행 대기 블록 데이터: {len(df_blocks)}건")
print(f" - 발행 대기 정반 데이터: {len(df_platens)}건")

# ==============================================================================
# 5. Kafka 토픽으로 메시지 발행 (Produce)
# ==============================================================================
print("\n[Step 3/3] Kafka 토픽으로 MES 이벤트 스트림 발행 시작...")

# 1) shipyard.mes.platens 토픽으로 정반 데이터 발행
topic_platens = "shipyard.mes.platens"
print(f"\n -> [{topic_platens}] 정반 마스터 이벤트 발행 중...")
for idx, row in df_platens.iterrows():
    msg = row.to_dict()
    producer.send(topic_platens, key=str(msg.get("platen_id", idx)).encode("utf-8"), value=msg)
producer.flush()
print(f"    {len(df_platens)}개 정반 마스터 이벤트 발행 완료.")

# 2) shipyard.mes.blocks 토픽으로 블록 생산 계획 데이터 발행
topic_blocks = "shipyard.mes.blocks"
print(f"\n -> [{topic_blocks}] 블록 생산 계획 이벤트 발행 중...")
for idx, row in df_blocks.iterrows():
    msg = row.to_dict()
    producer.send(topic_blocks, key=str(msg.get("block_id", idx)).encode("utf-8"), value=msg)
    if (idx + 1) % 200 == 0:
        print(f"    진행 중: {idx + 1} / {len(df_blocks)} 블록 전송 완료...")
producer.flush()
print(f"    총 {len(df_blocks)}개 블록 생산 계획 이벤트 발행 완료.")

producer.close()

print("\n" + "=" * 80)
print(" MES 원천 데이터의 Kafka 이벤트 브로커 발행이 100% 완료되었습니다!")
print(" Kafka-UI 대시보드(http://localhost:8088)에서 실시간 메시지를 확인하실 수 있습니다.")
print("=" * 80)
