# spark/apps/spark_feature_pipeline.py
"""
[Apache Spark 기반 조선소 블록/정반 분산 피처 엔지니어링 파이프라인]
--------------------------------------------------------------------------------
1. 주요 목적:
   - 레이크하우스의 조선소 블록(872개) 및 정반(66개) 데이터를 로드합니다.
   - Apache Spark의 분산 연산 엔진(PySpark)을 활용하여 4대 다차원 피처 마트를 가공합니다:
     1) 호선별 공정 부하 요약 (Ship Workload Summary)
     2) 군집별 특성 및 긴급도 지표 (Cluster Metrics Mart)
     3) 정반 시설 수용력 분석 (Platen Capacity Mart)
     4) 블록-정반 적합도 및 우선순위 스코어링 (Master Feature Table)
   - 가공된 최종 피처셋을 MinIO S3(s3://features/...) 및 로컬에 Parquet로 적재합니다.

2. 데이터 아키텍처 상의 위치:
   - Iceberg/MinIO -> [Apache Spark Feature Pipeline] -> Feature Table -> Airflow -> OR-Tools
--------------------------------------------------------------------------------
"""

import os
import sys
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType

# ==============================================================================
# 1. 프로젝트 루트 경로 및 중앙 경로(utils.paths) 연동
# ==============================================================================
cur_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(cur_dir))
sys.path.append(project_root)

from utils.paths import FEATURES_DIR

# MinIO 환경변수
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")

print("=" * 80)
print(" Apache Spark 분산 피처 엔지니어링 파이프라인 가동")
print("=" * 80)

# ==============================================================================
# 2. PySpark SparkSession 초기화
# ==============================================================================
print("\n[Step 1/5] SparkSession 초기화 중...")
spark = SparkSession.builder \
    .appName("ShipyardFeatureEngineering") \
    .master("local[*]") \
    .config("spark.driver.memory", "2g") \
    .config("spark.ui.enabled", "false") \
    .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
    .getOrCreate()

# 로그 레벨 축소
spark.sparkContext.setLogLevel("ERROR")
print(f" -> Spark Version: {spark.version} 초기화 완료.")

# ==============================================================================
# 3. 원천 블록 및 정반 데이터 로드 (Spark DataFrame 생성)
# ==============================================================================
print("\n[Step 2/5] 원천 블록 및 정반 데이터 로드...")

blocks_csv_path = os.path.join(FEATURES_DIR, "featured_blocks.csv")
platens_csv_path = os.path.join(FEATURES_DIR, "featured_platens.csv")

df_blocks = spark.read.csv(blocks_csv_path, header=True, inferSchema=True)
df_platens = spark.read.csv(platens_csv_path, header=True, inferSchema=True)

# 숫자형 컬럼 명시적 캐스팅 (안정성 보장)
df_blocks = df_blocks.withColumn("length_m", F.col("length_m").cast("double")) \
                     .withColumn("width_m", F.col("width_m").cast("double")) \
                     .withColumn("weight_ton", F.col("weight_ton").cast("double")) \
                     .withColumn("block_area_m2", F.col("block_area_m2").cast("double")) \
                     .withColumn("lead_time_days", F.col("lead_time_days").cast("double")) \
                     .withColumn("slack_days", F.col("slack_days").cast("double")) \
                     .withColumn("urgency_ratio", F.col("urgency_ratio").cast("double")) \
                     .withColumn("total_window_days", F.col("total_window_days").cast("double"))

df_platens = df_platens.withColumn("platen_length_m", F.col("platen_length_m").cast("double")) \
                       .withColumn("platen_width_m", F.col("platen_width_m").cast("double")) \
                       .withColumn("platen_area_m2", F.col("platen_area_m2").cast("double")) \
                       .withColumn("crane_capacity_ton", F.col("crane_capacity_ton").cast("double"))

print(f" -> 블록 Spark DataFrame 생성: {df_blocks.count()}개 행, {len(df_blocks.columns)}개 열")
print(f" -> 정반 Spark DataFrame 생성: {df_platens.count()}개 행, {len(df_platens.columns)}개 열")

# ==============================================================================
# 4. 분산 피처 엔지니어링 및 데이터 마트 가공
# ==============================================================================
print("\n[Step 3/5] Spark 분산 집계 및 파생 피처 연산 수행...")

# ------------------------------------------------------------------------------
# Mart 1. 호선별 공정 부하 요약 (Ship Workload Summary)
# ------------------------------------------------------------------------------
df_ship_workload = df_blocks.groupBy("ship_id").agg(
    F.count("block_id").alias("total_blocks"),
    F.round(F.sum("weight_ton"), 2).alias("total_weight_ton"),
    F.round(F.avg("weight_ton"), 2).alias("avg_block_weight_ton"),
    F.round(F.avg("lead_time_days"), 1).alias("avg_lead_time_days"),
    F.min("earliest_start_date").alias("project_start_date"),
    F.max("due_date").alias("project_due_date")
).orderBy("ship_id")

# ------------------------------------------------------------------------------
# Mart 2. 군집별 특성 및 긴급도 지표 (Cluster Metrics Mart)
# ------------------------------------------------------------------------------
df_cluster_metrics = df_blocks.groupBy("cluster_id", "cluster_name").agg(
    F.count("block_id").alias("block_count"),
    F.round(F.avg("block_area_m2"), 1).alias("avg_area_m2"),
    F.round(F.avg("weight_ton"), 1).alias("avg_weight_ton"),
    F.round(F.avg("slack_days"), 1).alias("avg_slack_days"),
    F.round(F.avg("urgency_ratio"), 3).alias("avg_urgency_ratio")
).orderBy("cluster_id")

# ------------------------------------------------------------------------------
# Mart 3. 정반 시설 수용력 분석 (Platen Capacity Mart)
# ------------------------------------------------------------------------------
df_platen_capacity = df_platens.groupBy("primary_area").agg(
    F.count("platen_id").alias("platen_count"),
    F.round(F.avg("platen_area_m2"), 1).alias("avg_platen_area_m2"),
    F.max("crane_capacity_ton").alias("max_crane_capacity_ton"),
    F.round(F.avg("crane_capacity_ton"), 1).alias("avg_crane_capacity_ton")
).orderBy("primary_area")

# ------------------------------------------------------------------------------
# Mart 4. 통합 최적화 피처셋 (Master Feature Table)
# 블록별 물리 제약 적합성(수용 가능한 정반 개수) 및 종합 우선순위 스코어 계산
# ------------------------------------------------------------------------------
platens_pdf = df_platens.toPandas()

def compute_compatibility_stats(length, width, weight):
    """블록의 길이, 폭, 중량을 수용할 수 있는 정반의 개수를 계산"""
    if length is None or width is None or weight is None:
        return 0
    compatible = platens_pdf[
        (platens_pdf["platen_length_m"] >= length) &
        (platens_pdf["platen_width_m"] >= width) &
        (platens_pdf["crane_capacity_ton"] >= weight)
    ]
    return int(len(compatible))

compat_udf = F.udf(compute_compatibility_stats, IntegerType())

df_master_features = df_blocks.withColumn(
    "compatible_platens_count",
    compat_udf(F.col("length_m"), F.col("width_m"), F.col("weight_ton"))
).withColumn(
    "urgency_priority_score",
    F.round((1.0 - (F.col("slack_days") / (F.col("total_window_days") + 1.0))) * 100.0, 2)
)

# ==============================================================================
# 5. 연산 결과 콘솔 출력 검증
# ==============================================================================
print("\n[Step 4/5] 분산 연산 결과 미리보기:")

print("\n--- [Mart 1] 호선별 공정 부하 요약 ---")
df_ship_workload.show(truncate=False)

print("\n--- [Mart 2] 군집별 특성 및 긴급도 지표 ---")
df_cluster_metrics.show(truncate=False)

print("\n--- [Mart 3] 정반 시설 수용력 분석 ---")
df_platen_capacity.show(truncate=False)

print("\n--- [Mart 4] Master Feature Table (상위 5건) ---")
df_master_features.select(
    "block_id", "ship_id", "weight_ton", "cluster_name", 
    "slack_days", "compatible_platens_count", "urgency_priority_score"
).show(5, truncate=False)

# ==============================================================================
# 6. MinIO S3 및 로컬 디렉토리에 결과 Parquet 저장
# ==============================================================================
print("\n[Step 5/5] 가공된 Feature Table을 Parquet로 저장 및 MinIO 업로드...")

# 1) 로컬 Parquet 저장
out_master_parquet = os.path.join(FEATURES_DIR, "master_feature_table.parquet")
out_ship_parquet = os.path.join(FEATURES_DIR, "ship_workload_summary.parquet")
out_cluster_parquet = os.path.join(FEATURES_DIR, "cluster_metrics_summary.parquet")

df_master_features.toPandas().to_parquet(out_master_parquet, index=False)
df_ship_workload.toPandas().to_parquet(out_ship_parquet, index=False)
df_cluster_metrics.toPandas().to_parquet(out_cluster_parquet, index=False)

print(f" -> 로컬 저장 완료: {out_master_parquet}")
print(f" -> 로컬 저장 완료: {out_ship_parquet}")
print(f" -> 로컬 저장 완료: {out_cluster_parquet}")

# 2) MinIO S3 업로드
import boto3
from botocore.client import Config

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1"
)

for file_path, s3_key in [
    (out_master_parquet, "master_feature_table.parquet"),
    (out_ship_parquet, "ship_workload_summary.parquet"),
    (out_cluster_parquet, "cluster_metrics_summary.parquet")
]:
    with open(file_path, "rb") as f:
        s3.put_object(Bucket="features", Key=s3_key, Body=f.read())
    print(f" -> MinIO s3://features/{s3_key} 업로드 완료.")

# SparkSession 종료
spark.stop()

print("\n" + "=" * 80)
print(" Apache Spark 피처 엔지니어링 파이프라인이 성공적으로 완료되었습니다!")
print("=" * 80)
