# kafka/producer_emergency_stream.py
"""
[조선소 돌발 긴급 블록 실시간 스트리밍 프로듀서]
--------------------------------------------------------------------------------
1. 주요 목적:
   - 조선소 야드 현장에서 예기치 않게 발생하는 '긴급/수정 블록(Emergency Block)' 생산 요청을
     가상으로 생성하여 Kafka의 'shipyard.emergency.blocks' 실시간 토픽으로 스트리밍 발행합니다.
   - 각 긴급 블록은 크기(가로, 세로), 무게(톤), 즉시 착수 납기일 등의 물리 제약 속성을 포함합니다.

2. 데이터 아키텍처 상의 위치:
   - [긴급 블록 발생기 (Producer)] -> [Kafka: shipyard.emergency.blocks] -> [Apache Flink] -> [FastAPI]

3. 연동 토픽 및 보안:
   - 대상 토픽: shipyard.emergency.blocks
   - 보안 인증: SASL_PLAINTEXT (SCRAM-SHA-512)
--------------------------------------------------------------------------------
"""

import os
import sys
import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

# ==============================================================================
# 1. Kafka 브로커 연결 및 인증 정보
# ==============================================================================
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_USER = os.environ.get("KAFKA_USER", "my-app-user")
KAFKA_PASSWORD = os.environ.get("KAFKA_PASSWORD", "uk2eajtu8WM5lGgAemy5F8l3qoJh5mwz")
TOPIC_NAME = "shipyard.emergency.blocks"

print("=" * 80)
print(" 조선소 돌발 긴급 블록 실시간 이벤트 스트림 프로듀서 가동")
print(f" - Kafka 브로커: {KAFKA_BOOTSTRAP}, 토픽: {TOPIC_NAME}")
print("=" * 80)

# ==============================================================================
# 2. Kafka Producer 인스턴스 초기화
# ==============================================================================
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
    print(" -> Kafka 브로커 SCRAM-SHA-512 보안 연결 성공!")
except Exception as e:
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8")
        )
        print(" -> Kafka 브로커 일반 연결 성공!")
    except Exception as err:
        print(f"[오류] Kafka 브로커 연결 실패: {err}")
        print("포트포워딩(pfstart) 또는 클러스터 상태를 확인해 주세요.")
        sys.exit(1)

# ==============================================================================
# 3. 긴급 블록 실시간 이벤트 모의 스트리밍 생성 함수
# ==============================================================================
def generate_emergency_block(seq: int) -> dict:
    """
    현장 상황에 맞는 현실적인 긴급 블록 속성 생성:
    - 선박 호선: H1087, H1088, H1089 중 무작위
    - 가로/세로: 10m ~ 25m
    - 무게: 30톤 ~ 85톤
    - 작업 소요기간: 5일 ~ 15일
    """
    ship_id = random.choice(["H1087", "H1088", "H1089"])
    block_id = f"EMG_{ship_id}_{seq:03d}"
    
    length_m = round(random.uniform(12.0, 24.0), 2)
    width_m = round(random.uniform(8.0, 16.0), 2)
    area_m2 = round(length_m * width_m, 2)
    weight_ton = round(random.uniform(25.0, 80.0), 1)
    processing_time_days = random.randint(5, 14)
    due_date_day = random.randint(30, 90)
    
    event = {
        "event_id": f"EVT-{int(time.time()*1000)}-{seq}",
        "timestamp": datetime.now().isoformat(),
        "block_id": block_id,
        "ship_id": ship_id,
        "length_m": length_m,
        "width_m": width_m,
        "area_m2": area_m2,
        "weight_ton": weight_ton,
        "processing_time_days": processing_time_days,
        "due_date_day": due_date_day,
        "priority_level": "CRITICAL_EMERGENCY",
        "status": "UNASSIGNED"
    }
    return event

# ==============================================================================
# 4. 실시간 긴급 이벤트 전송 루프 (기본: 10개 이벤트 순차 발행)
# ==============================================================================
NUM_EVENTS = int(os.environ.get("EMERGENCY_EVENTS_COUNT", 10))
print(f"\n[실시간 스트림 시작] 총 {NUM_EVENTS}건의 긴급 블록 이벤트를 실시간 발행합니다...")

for i in range(1, NUM_EVENTS + 1):
    event = generate_emergency_block(i)
    producer.send(TOPIC_NAME, key=event["block_id"].encode("utf-8"), value=event)
    print(f" [발행 {i:02d}/{NUM_EVENTS:02d}] 블록: {event['block_id']:<15} | 크기: {event['length_m']}m x {event['width_m']}m | 무게: {event['weight_ton']}톤 | 납기: Day {event['due_date_day']}")
    time.sleep(0.5) # 0.5초 간격 실시간 스트림 시뮬레이션

producer.flush()
producer.close()

print("\n" + "=" * 80)
print(f" 총 {NUM_EVENTS}건의 긴급 블록 이벤트가 '{TOPIC_NAME}' 토픽으로 성공적으로 발행되었습니다!")
print(" Apache Flink 스트림 프로세서가 이 이벤트를 즉시 감지하여 실시간 검증을 수행합니다.")
print("=" * 80)
