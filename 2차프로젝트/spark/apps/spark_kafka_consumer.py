# spark/apps/spark_kafka_consumer.py
"""
[실전 PySpark 분산 처리 & MinIO 데이터 레이크 적재 파이프라인]
1. Kafka [my-topic]에서 SCRAM-SHA-512 보안 인증을 거쳐 실시간 주문 데이터를 읽어옴
2. 고객별/상품별 분산 통계 집계 수행
3. MinIO S3 스토리지 [s3a://features/orders]에 Parquet 포맷으로 고속 영속 저장
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, LongType

def main():
    print("=========================================================")
    print("🚀 Starting Spark Kafka ➔ MinIO Data Lake Pipeline")
    print("=========================================================")

    # 1. SparkSession 생성 (MinIO S3A 설정 포함)
    spark = SparkSession.builder \
        .appName("KafkaToMinIOOrderPipeline") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio-service.minio.svc:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # 2. 주문 데이터 JSON 스키마 정의
    order_schema = StructType([
        StructField("order_id", StringType(), True),
        StructField("user", StringType(), True),
        StructField("item", StringType(), True),
        StructField("amount", LongType(), True),
        StructField("timestamp", StringType(), True)
    ])

    # 3. Kafka my-topic에서 데이터 읽기 (SCRAM-SHA-512 보안 연결)
    kafka_df = spark.read \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "my-cluster-kafka-bootstrap.kafka.svc:9092") \
        .option("subscribe", "my-topic") \
        .option("startingOffsets", "earliest") \
        .option("kafka.security.protocol", "SASL_PLAINTEXT") \
        .option("kafka.sasl.mechanism", "SCRAM-SHA-512") \
        .option("kafka.sasl.jaas.config", 'org.apache.kafka.common.security.scram.ScramLoginModule required username="my-app-user" password="uk2eajtu8WM5lGgAemy5F8l3qoJh5mwz";') \
        .load()

    # 4. JSON 바이너리 데이터를 구조화된 테이블로 파싱
    parsed_df = kafka_df.selectExpr("CAST(value AS STRING) as json_str") \
        .select(from_json(col("json_str"), order_schema).alias("data")) \
        .select("data.*") \
        .filter(col("order_id").isNotNull())

    print("\n📦 [1단계] Kafka에서 읽어온 원천 주문 데이터 목록:")
    parsed_df.show(truncate=False)

    print("\n👤 [2단계] 고객(User)별 총 구매 금액 및 주문 횟수 분산 집계:")
    user_summary = parsed_df.groupBy("user") \
        .agg({"amount": "sum", "order_id": "count"}) \
        .withColumnRenamed("sum(amount)", "total_spent_krw") \
        .withColumnRenamed("count(order_id)", "order_count") \
        .orderBy(col("total_spent_krw").desc())
    user_summary.show(truncate=False)

    # 5. MinIO 로컬 S3 [features] 버킷에 Parquet 포맷으로 영속 저장 ⭐
    print("\n💾 [3단계] MinIO 로컬 S3 스토리지(s3a://features/orders)에 Parquet 저장 시작...")
    
    parsed_df.write \
        .mode("overwrite") \
        .parquet("s3a://features/orders")

    user_summary.write \
        .mode("overwrite") \
        .parquet("s3a://features/user_summary")

    print("=========================================================")
    print("✅ All Spark Data Successfully Saved to MinIO S3 (features Bucket)!")
    print("=========================================================")

    spark.stop()

if __name__ == "__main__":
    main()
