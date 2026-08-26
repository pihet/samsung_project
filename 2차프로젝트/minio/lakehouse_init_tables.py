# minio/lakehouse_init_tables.py
"""
[MinIO 및 레이크하우스(Lakehouse) 초기화 스크립트]
--------------------------------------------------------------------------------
1. 주요 목적:
   - 로컬/쿠버네티스 MinIO S3 스토리지에 필수 버킷('warehouse', 'features', 'schedules')을 자동 점검 및 생성합니다.
   - 전처리된 조선소 블록(featured_blocks.csv), 정반(featured_platens.csv),
     마스터 스케줄(ortools_scheduling_results.csv) 데이터를 읽어옵니다.
   - 대규모 분산 처리에 최적화된 컬럼형 스토리지 포맷인 Parquet로 변환한 뒤,
     MinIO 레이크하우스 경로(s3://warehouse/shipyard/...)에 초기 적재합니다.

2. 데이터 아키텍처 상의 위치:
   - MES/데이터셋 -> MinIO (Raw Landing & Warehouse Parquet) -> Apache Iceberg / Spark / Airflow
--------------------------------------------------------------------------------
"""

import os
import sys
import pandas as pd
import boto3
from botocore.client import Config
import pyarrow as pa
import pyarrow.parquet as pq

# ==============================================================================
# 1. 프로젝트 루트 경로 계산 및 중앙 경로 모듈(utils.paths) 연동
# ==============================================================================
# 현재 파일 위치: /home/kjc/workspace/samsung_project/2차프로젝트/minio/
cur_dir = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 루트: /home/kjc/workspace/samsung_project/2차프로젝트
project_root = os.path.dirname(cur_dir)
sys.path.append(project_root)

# 프로젝트 내 표준화된 디렉토리 경로 import
from utils.paths import FEATURES_DIR, SCHEDULES_DIR

# ==============================================================================
# 2. MinIO S3 연결 환경변수 설정
# ==============================================================================
# - 로컬 포트포워딩(pfstart) 기준 S3 API 엔드포인트: http://localhost:9000
# - 기본 관리자 계정: minioadmin / minioadmin123 (minio.yaml Secret 기준)
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")

print("=" * 80)
print(" MinIO S3 스토리지 및 레이크하우스(Lakehouse) 초기화 시작")
print("=" * 80)

# ==============================================================================
# 3. MinIO S3 클라이언트(boto3) 초기화
# ==============================================================================
# AWS S3 호환 프로토콜(v4 시그니처)을 사용하여 MinIO 서버와 통신합니다.
s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1"
)

# ==============================================================================
# 4. 필수 S3 버킷 존재 여부 확인 및 자동 생성
# ==============================================================================
# - warehouse : Apache Iceberg 테이블 및 Parquet 데이터가 저장되는 메인 웨어하우스 버킷
# - features  : 머신러닝/강화학습 전처리 피처 데이터셋 백업 버킷
# - schedules : OR-Tools 및 휴리스틱 알고리즘의 최종 스케줄 결과 백업 버킷
required_buckets = ["warehouse", "features", "schedules"]
print("\n[Step 1/3] MinIO 버킷 상태 점검 및 생성...")

try:
    existing_buckets = [b["Name"] for b in s3_client.list_buckets().get("Buckets", [])]
    print(f" - 현재 존재하는 MinIO 버킷 목록: {existing_buckets}")

    for bucket in required_buckets:
        if bucket not in existing_buckets:
            print(f" -> 필수 버킷 누락 감지, 신규 생성 중: '{bucket}'")
            s3_client.create_bucket(Bucket=bucket)
            print(f"    버킷 '{bucket}' 생성 완료.")
        else:
            print(f" -> 버킷 '{bucket}' 정상 확인 (이미 존재함).")
except Exception as e:
    print(f"[오류] MinIO 서버에 연결할 수 없습니다. (포트포워딩 확인 필요: pfstart)")
    print(f"상세 에러: {e}")
    sys.exit(1)

# ==============================================================================
# 5. 로컬 가공 데이터셋 로드
# ==============================================================================
# 전처리 완료된 블록 피처, 정반 제원, OR-Tools 결정론적 마스터 스케줄을 읽어옵니다.
blocks_csv = os.path.join(FEATURES_DIR, "featured_blocks.csv")
platens_csv = os.path.join(FEATURES_DIR, "featured_platens.csv")
schedule_csv = os.path.join(SCHEDULES_DIR, "ortools_scheduling_results.csv")

print("\n[Step 2/3] 로컬 전처리 데이터셋 로드...")
df_blocks = pd.read_csv(blocks_csv)
df_platens = pd.read_csv(platens_csv)
df_schedules = pd.read_csv(schedule_csv)

print(f" - 블록 데이터 로드 완료: {len(df_blocks)}개 블록 (K-Means 군집 및 긴급도 피처 포함)")
print(f" - 정반 데이터 로드 완료: {len(df_platens)}개 정반 (치수 및 크레인 용량 포함)")
print(f" - 스케줄 데이터 로드 완료: {len(df_schedules)}개 배정 레코드 (OR-Tools 마스터 결과)")

# ==============================================================================
# 6. DataFrame -> Parquet 변환 및 MinIO 업로드 함수 정의
# ==============================================================================
def upload_df_as_parquet(df: pd.DataFrame, bucket: str, s3_key: str):
    """
    Pandas DataFrame을 PyArrow 테이블로 변환한 후,
    디스크에 임시 파일을 쓰지 않고 메모리 버퍼(BufferOutputStream)에서
    직접 Parquet 바이너리로 압축하여 MinIO S3 버킷에 업로드합니다.
    """
    # 1) Pandas DataFrame -> PyArrow Table 변환
    table = pa.Table.from_pandas(df)
    
    # 2) 메모리 스트림 버퍼에 Parquet 형식으로 쓰기 (Snappy 압축 기본 적용)
    buf = pa.BufferOutputStream()
    pq.write_table(table, buf)
    parquet_bytes = buf.getvalue().to_pybytes()
    
    # 3) S3 API를 통해 MinIO 버킷에 업로드
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=parquet_bytes,
        ContentType="application/octet-stream"
    )
    file_size_kb = len(parquet_bytes) / 1024
    print(f" -> 업로드 성공: s3://{bucket}/{s3_key} ({len(df)}건, {file_size_kb:.1f} KB)")

# ==============================================================================
# 7. 레이크하우스(Warehouse) 및 백업 버킷에 Parquet 테이블 적재
# ==============================================================================
print("\n[Step 3/3] MinIO 레이크하우스 저장소에 Parquet 테이블 업로드...")

# 1) warehouse 버킷 (Apache Iceberg 및 분산 엔진이 접근하는 메인 레이크하우스 경로)
upload_df_as_parquet(df_blocks, "warehouse", "shipyard/blocks/data/blocks.parquet")
upload_df_as_parquet(df_platens, "warehouse", "shipyard/platens/data/platens.parquet")
upload_df_as_parquet(df_schedules, "warehouse", "shipyard/master_schedules/data/ortools_master.parquet")

# 2) features 및 schedules 버킷 (도메인별 백업 및 서빙 연동용 Parquet 복사본)
upload_df_as_parquet(df_blocks, "features", "featured_blocks.parquet")
upload_df_as_parquet(df_platens, "features", "featured_platens.parquet")
upload_df_as_parquet(df_schedules, "schedules", "master_schedule_ortools.parquet")

print("\n" + "=" * 80)
print(" MinIO 레이크하우스 테이블 초기 적재가 성공적으로 완료되었습니다!")
print(" - 블록 테이블 경로   : s3://warehouse/shipyard/blocks/data/blocks.parquet")
print(" - 정반 테이블 경로   : s3://warehouse/shipyard/platens/data/platens.parquet")
print(" - 마스터 스케줄 경로 : s3://warehouse/shipyard/master_schedules/data/ortools_master.parquet")
print("=" * 80)
