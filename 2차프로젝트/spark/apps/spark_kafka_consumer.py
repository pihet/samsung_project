# spark/apps/spark_kafka_consumer.py
"""
[실전 PySpark 분산 처리 애플리케이션]
Kafka [my-topic]에서 SCRAM-SHA-512 보안 인증을 거쳐 실시간 주문 데이터를 읽어온 뒤,
유저별 총 주문 금액 집계 및 인기 상품 매출 통계를 분산 병렬 계산하는 Spark Job
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, LongType

def main():
    print("=========================================================")
    print("🚀 Starting Spark Kafka Distributed Processing Application")
    print("=========================================================")

    # 1. SparkSession 생성
    spark = SparkSession.builder \
        .appName("KafkaOrderDistributedAnalytics") \
        .getOrCreate()

    # 로그 레벨 조정 (불필요한 WARN 축소)
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

    # 4. JSON 바이너리 데이터를 문자열 및 컬럼으로 파싱
    parsed_df = kafka_df.selectExpr("CAST(value AS STRING) as json_str") \
        .select(from_json(col("json_str"), order_schema).alias("data")) \
        .select("data.*") \
        .filter(col("order_id").isNotNull())

    print("\n📦 [1단계] Kafka my-topic에서 추출한 원천 주문 데이터 목록:")
    parsed_df.show(truncate=False)

    print("\n👤 [2단계] 고객(User)별 총 구매 금액 및 주문 횟수 분산 집계:")
    user_summary = parsed_df.groupBy("user") \
        .agg({"amount": "sum", "order_id": "count"}) \
        .withColumnRenamed("sum(amount)", "total_spent_krw") \
        .withColumnRenamed("count(order_id)", "order_count") \
        .orderBy(col("total_spent_krw").desc())
    user_summary.show(truncate=False)

    print("\n🏆 [3단계] 상품(Item)별 총 매출 순위 집계 (인기 상품 랭킹):")
    item_summary = parsed_df.groupBy("item") \
        .sum("amount") \
        .withColumnRenamed("sum(amount)", "total_sales_krw") \
        .orderBy(col("total_sales_krw").desc())
    item_summary.show(truncate=False)

    print("=========================================================")
    print("✅ All Spark Distributed Processing Completed Successfully!")
    print("=========================================================")

    spark.stop()

if __name__ == "__main__":
    main()
