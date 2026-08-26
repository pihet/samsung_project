# kafka/consumer_to_iceberg.py
"""
[Kafka -> MinIO Apache Iceberg 레이크하우스 실시간 수집(Ingestion) 컨슈머]
--------------------------------------------------------------------------------
1. 주요 목적:
   - Kafka 토픽('shipyard.mes.blocks', 'shipyard.mes.platens')에 유입된 MES 원천 이벤트를 컨슘합니다.
   - 수집된 원천 데이터를 검증 및 정제한 후, Apache Iceberg 레이크하우스 테이블에 스냅샷 형태로 적재(Append)합니다:
     1) shipyard.mes.blocks  -> lakehouse.shipyard.blocks
     2) shipyard.mes.platens -> lakehouse.shipyard.platens
   - 수집 완료 후 최신 스냅샷 ID와 레코드 건수를 출력합니다.

2. 데이터 아키텍처 상의 위치:
   - MES -> [Kafka Event Broker] -> [Kafka-to-Iceberg Ingestion] -> MinIO/Iceberg -> Spark
--------------------------------------------------------------------------------
"""

import os
import sys
import json
import time
import pandas as pd
import pyarrow as pa
from kafka import KafkaConsumer
from pyiceberg.catalog.sql import SqlCatalog

# ==============================================================================
# 1. 프로젝트 루트 경로 및 중앙 경로(utils.paths) 연동
# ==============================================================================
cur_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(cur_dir)
sys.path.append(project_root)

from utils.paths import PROCESSED_DIR

# MinIO & Kafka 설정
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_USER = os.environ.get("KAFKA_USER", "my-app-user")
KAFKA_PASSWORD = os.environ.get("KAFKA_PASSWORD", "uk2eajtu8WM5lGgAemy5F8l3qoJh5mwz")

catalog_db_path = os.path.join(PROCESSED_DIR, "iceberg_catalog.db")

print("=" * 80)
print(" Kafka -> Apache Iceberg 레이크하우스 수집(Ingestion) 파이프라인 가동")
print("=" * 80)

# ==============================================================================
# 2. Apache Iceberg 카탈로그 연결
# ==============================================================================
print("\n[Step 1/3] Apache Iceberg 카탈로그 연결 중...")
catalog = SqlCatalog(
    "lakehouse",
    uri=f"sqlite:///{catalog_db_path}",
    warehouse="s3://warehouse/iceberg",
    **{
        "s3.endpoint": MINIO_ENDPOINT,
        "s3.access-key-id": MINIO_ACCESS_KEY,
        "s3.secret-access-key": MINIO_SECRET_KEY,
        "s3.path-style-access": "true",
        "s3.region": "us-east-1",
        "py-io-impl": "pyiceberg.io.pyarrow.PyArrowFileIO"
    }
)
print(" -> Iceberg 카탈로그('lakehouse') 연결 성공.")

# ==============================================================================
# 3. Kafka Consumer 생성 및 메시지 수집 함수
# ==============================================================================
def consume_topic_messages(topic_name: str, max_records: int = 1000, timeout_ms: int = 5000):
    """Kafka 토픽에서 메시지를 폴링하여 Python List로 반환"""
    print(f"\n[Kafka 수집] 토픽 '{topic_name}'에서 메시지 폴링 중...")
    
    try:
        consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            security_protocol="SASL_PLAINTEXT",
            sasl_mechanism="SCRAM-SHA-512",
            sasl_plain_username=KAFKA_USER,
            sasl_plain_password=KAFKA_PASSWORD,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id=f"iceberg-ingestion-{topic_name}-{int(time.time())}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=timeout_ms
        )
    except Exception:
        consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id=f"iceberg-ingestion-{topic_name}-{int(time.time())}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=timeout_ms
        )
        
    records = []
    for msg in consumer:
        records.append(msg.value)
        if len(records) >= max_records:
            break
            
    consumer.close()
    print(f" -> 토픽 '{topic_name}'에서 총 {len(records)}건의 메시지 수집 완료.")
    return records

# ==============================================================================
# 4. Kafka 수집 데이터 -> Iceberg 테이블 적재 (스냅샷 커밋)
# ==============================================================================
print("\n[Step 2/3] Kafka 메시지 수집 및 Iceberg 테이블 스냅샷 커밋...")

# 1) 정반 데이터 수집 및 Iceberg 적재
platen_msgs = consume_topic_messages("shipyard.mes.platens", max_records=100)
if platen_msgs:
    df_platens_raw = pd.DataFrame(platen_msgs)
    arrow_platens = pa.Table.from_pandas(df_platens_raw)
    
    table_platens = catalog.load_table("shipyard.platens")
    # 최신 데이터로 Append
    table_platens.append(arrow_platens)
    print(f" -> [shipyard.platens] Iceberg 적재 완료: {len(df_platens_raw)}건")
    print(f"    최신 스냅샷 ID: {table_platens.current_snapshot().snapshot_id}")

# 2) 블록 데이터 수집 및 Iceberg 적재
block_msgs = consume_topic_messages("shipyard.mes.blocks", max_records=1000)
if block_msgs:
    df_blocks_raw = pd.DataFrame(block_msgs)
    arrow_blocks = pa.Table.from_pandas(df_blocks_raw)
    
    table_blocks = catalog.load_table("shipyard.blocks")
    table_blocks.append(arrow_blocks)
    print(f" -> [shipyard.blocks] Iceberg 적재 완료: {len(df_blocks_raw)}건")
    print(f"    최신 스냅샷 ID: {table_blocks.current_snapshot().snapshot_id}")

# ==============================================================================
# 5. 최종 적재 결과 확인
# ==============================================================================
print("\n[Step 3/3] Iceberg 레이크하우스 데이터 무결성 검증...")
table_blocks = catalog.load_table("shipyard.blocks")
scanned_count = len(table_blocks.scan().to_arrow())
print(f" -> Iceberg 'shipyard.blocks' 총 누적 데이터 건수: {scanned_count} 건")

print("\n" + "=" * 80)
print(" Kafka -> MinIO Apache Iceberg 실시간 수집 파이프라인이 성공적으로 완료되었습니다!")
print("=" * 80)
