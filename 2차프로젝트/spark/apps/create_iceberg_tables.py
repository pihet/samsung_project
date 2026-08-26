# spark/apps/create_iceberg_tables.py
"""
[Apache Iceberg 정식 레이크하우스 테이블 생성 및 카탈로그 등록 스크립트]
--------------------------------------------------------------------------------
1. 주요 목적:
   - MinIO S3 저장소(s3://warehouse/iceberg/...)와 연동되는 Apache Iceberg 카탈로그를 생성합니다.
   - 3대 핵심 도메인 테이블을 생성하고 메타데이터 스냅샷을 커밋합니다:
     1) shipyard.blocks           : 872개 블록 제원 및 K-Means 군집/긴급도 피처
     2) shipyard.platens          : 66개 정반 치수, 면적 및 크레인 인양 용량
     3) shipyard.master_schedules : OR-Tools 결정론적 마스터 스케줄 배정 결과
   - Iceberg 테이블의 스키마, 메타데이터 파일(.metadata.json), 스냅샷 ID를 확인하고
     데이터 조회(Scan)를 검증합니다.

2. 데이터 아키텍처 상의 위치:
   - MinIO S3 -> [Apache Iceberg Lakehouse Catalog] -> Spark Batch / Airflow / Flink
--------------------------------------------------------------------------------
"""

import os
import sys
import pandas as pd
import pyarrow as pa
from pyiceberg.catalog.sql import SqlCatalog

# ==============================================================================
# 1. 프로젝트 루트 경로 및 중앙 경로(utils.paths) 연동
# ==============================================================================
cur_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(cur_dir))
sys.path.append(project_root)

from utils.paths import FEATURES_DIR, SCHEDULES_DIR, PROCESSED_DIR

# ==============================================================================
# 2. MinIO S3 및 Iceberg 카탈로그 DB 경로 설정
# ==============================================================================
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")

# 카탈로그 메타데이터를 관리할 로컬 SQLite DB 파일 경로
catalog_db_path = os.path.join(PROCESSED_DIR, "iceberg_catalog.db")

print("=" * 80)
print(" Apache Iceberg 레이크하우스 테이블 정식 등록 파이프라인 가동")
print("=" * 80)

# ==============================================================================
# 3. Apache Iceberg SqlCatalog 인스턴스 초기화 (MinIO S3 연동)
# ==============================================================================
# - Catalog Name: lakehouse
# - Warehouse Path: s3://warehouse/iceberg/ (MinIO S3 버킷 내부)
# - S3 FileIO: pyiceberg.io.pyarrow.PyArrowFileIO를 통해 MinIO와 S3 통신
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

# ==============================================================================
# 4. Iceberg 네임스페이스(Namespace: shipyard) 생성
# ==============================================================================
namespace_name = "shipyard"
try:
    catalog.create_namespace(namespace_name)
    print(f"\n[Step 1/4] Iceberg 네임스페이스 '{namespace_name}' 신규 생성 완료.")
except Exception:
    print(f"\n[Step 1/4] Iceberg 네임스페이스 '{namespace_name}' 확인 완료 (기존 존재).")

# ==============================================================================
# 5. Iceberg 테이블 생성 및 데이터 적재 함수 정의
# ==============================================================================
def create_and_populate_iceberg_table(table_identifier: str, csv_file_path: str, description: str):
    """
    1) CSV 데이터셋을 Pandas로 읽어 PyArrow Table로 변환합니다.
    2) 기존 테이블이 있으면 스키마 갱신을 위해 Drop 후 신규 생성합니다.
    3) Iceberg 테이블 스키마를 정의하고 데이터를 Append(스냅샷 커밋)합니다.
    4) 생성된 .metadata.json 위치와 스냅샷 ID를 출력합니다.
    """
    print(f"\n[테이블 생성] {table_identifier} ({description})")
    
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"데이터셋 파일을 찾을 수 없습니다: {csv_file_path}")
        
    df = pd.read_csv(csv_file_path)
    arrow_table = pa.Table.from_pandas(df)
    
    # 기존 테이블이 존재하면 초기화(Drop)
    if catalog.table_exists(table_identifier):
        catalog.drop_table(table_identifier)
        print(f" -> 기존 {table_identifier} 테이블 초기화 완료.")
        
    # 1) Iceberg 테이블 생성
    iceberg_table = catalog.create_table(
        identifier=table_identifier,
        schema=arrow_table.schema
    )
    
    # 2) 데이터 Append (Iceberg Snapshot 생성 및 S3 커밋)
    iceberg_table.append(arrow_table)
    
    # 3) 결과 및 메타데이터 확인
    snapshot = iceberg_table.current_snapshot()
    snapshot_id = snapshot.snapshot_id if snapshot else "N/A"
    
    print(f" -> 적재 건수: {len(df)} 행")
    print(f" -> 스냅샷 ID: {snapshot_id}")
    print(f" -> 메타데이터 위치: {iceberg_table.metadata_location}")
    return iceberg_table

# ==============================================================================
# 6. 3대 핵심 Iceberg 테이블 생성 실행
# ==============================================================================
print("\n[Step 2/4] 3대 도메인 Iceberg 테이블 생성 및 스냅샷 커밋...")

# 1) shipyard.blocks 테이블 생성
blocks_csv = os.path.join(FEATURES_DIR, "featured_blocks.csv")
table_blocks = create_and_populate_iceberg_table(
    "shipyard.blocks",
    blocks_csv,
    "872개 블록 제원 및 K-Means 피처"
)

# 2) shipyard.platens 테이블 생성
platens_csv = os.path.join(FEATURES_DIR, "featured_platens.csv")
table_platens = create_and_populate_iceberg_table(
    "shipyard.platens",
    platens_csv,
    "66개 정반 치수 및 크레인 용량"
)

# 3) shipyard.master_schedules 테이블 생성
schedule_csv = os.path.join(SCHEDULES_DIR, "ortools_scheduling_results.csv")
table_schedules = create_and_populate_iceberg_table(
    "shipyard.master_schedules",
    schedule_csv,
    "OR-Tools 마스터 스케줄 배정 결과"
)

# ==============================================================================
# 7. Iceberg 테이블 조회(Scan) 검증
# ==============================================================================
print("\n[Step 3/4] Iceberg 테이블 쿼리 및 데이터 스캔 검증...")

# shipyard.blocks 테이블에서 상위 3건 스캔
scan_blocks = table_blocks.scan(limit=3).to_arrow().to_pandas()
print("\n--- [조회 결과] shipyard.blocks 상위 3건 ---")
print(scan_blocks[["seq_id", "ship_id", "block_id", "block_type", "weight_ton", "due_date", "cluster_name"]])

# shipyard.master_schedules 테이블에서 상위 3건 스캔
scan_schedules = table_schedules.scan(limit=3).to_arrow().to_pandas()
print("\n--- [조회 결과] shipyard.master_schedules 상위 3건 ---")
print(scan_schedules[["seq_id", "block_id", "ship_id", "platen_name", "planned_start_day", "planned_end_day", "delay_days", "status"]])

# ==============================================================================
# 8. 최종 완료 요약
# ==============================================================================
print("\n" + "=" * 80)
print(" [완료] Apache Iceberg 3대 테이블이 MinIO 레이크하우스에 정식 등록되었습니다!")
print(f" 1. lakehouse.shipyard.blocks           (872건, 스냅샷 ID: {table_blocks.current_snapshot().snapshot_id})")
print(f" 2. lakehouse.shipyard.platens          (66건,  스냅샷 ID: {table_platens.current_snapshot().snapshot_id})")
print(f" 3. lakehouse.shipyard.master_schedules (872건, 스냅샷 ID: {table_schedules.current_snapshot().snapshot_id})")
print("=" * 80)
