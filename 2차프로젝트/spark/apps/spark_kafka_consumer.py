# spark/apps/spark_kafka_consumer.py
"""
================================================================================
PySpark Distributed Shipyard Block Feature Engineering & MinIO Lakehouse Ingestion
================================================================================
- Pipeline:
  1. Consumes raw shipyard block production events from Kafka topic 'shipyard-block-events'.
  2. Performs distributed Domain Feature Engineering (slack_days, urgency_ratio, area_m2, aspect_ratio).
  3. Writes high-performance Parquet format to MinIO S3 Data Lake (s3a://shipyard-mlops/features/blocks).
================================================================================
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, when, to_date, datediff, lit
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType

def main():
    print("=" * 80)
    print("Starting PySpark Shipyard Block Processing & MinIO Lakehouse Pipeline")
    print("=" * 80)

    # 1. Initialize SparkSession with S3A MinIO credentials
    spark = SparkSession.builder \
        .appName("ShipyardBlockFeaturePipeline") \
        .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio-service.minio.svc:9000")) \
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", "minioadmin")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "minioadmin123")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # 2. Define Shipyard Block Event Schema
    block_schema = StructType([
        StructField("seq_id", IntegerType(), True),
        StructField("ship_id", StringType(), True),
        StructField("block_id", StringType(), True),
        StructField("length_m", DoubleType(), True),
        StructField("width_m", DoubleType(), True),
        StructField("weight_ton", DoubleType(), True),
        StructField("lead_time_days", IntegerType(), True),
        StructField("earliest_start_date", StringType(), True),
        StructField("due_date", StringType(), True),
        StructField("block_type", StringType(), True)
    ])

    # 3. Read stream or batch from Kafka
    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "my-cluster-kafka-bootstrap.kafka.svc:9092")
    topic_name = "shipyard-block-events"

    print(f"Connecting to Kafka: {kafka_bootstrap}, Topic: {topic_name}")

    # Fallback to direct dataframe if running in local test mode
    try:
        raw_df = spark.read \
            .format("kafka") \
            .option("kafka.bootstrap.servers", kafka_bootstrap) \
            .option("subscribe", topic_name) \
            .option("startingOffsets", "earliest") \
            .load()

        parsed_df = raw_df.select(from_json(col("value").cast("string"), block_schema).alias("data")).select("data.*")
    except Exception as e:
        print(f"Kafka connection skipped (test mode): {e}")
        parsed_df = spark.createDataFrame([], block_schema)

    # 4. Feature Engineering
    if parsed_df.count() > 0:
        featured_df = parsed_df \
            .withColumn("block_area_m2", col("length_m") * col("width_m")) \
            .withColumn("aspect_ratio", col("length_m") / when(col("width_m") == 0, 1.0).otherwise(col("width_m"))) \
            .withColumn("total_window_days", datediff(to_date(col("due_date")), to_date(col("earliest_start_date")))) \
            .withColumn("slack_days", col("total_window_days") - col("lead_time_days")) \
            .withColumn("urgency_ratio", col("lead_time_days") / when(col("total_window_days") <= 0, 1.0).otherwise(col("total_window_days")))

        # 5. Write to MinIO S3A
        output_s3 = "s3a://shipyard-mlops/features/blocks"
        print(f"Writing {featured_df.count()} featured blocks to MinIO Lakehouse: {output_s3}")
        featured_df.write.mode("overwrite").parquet(output_s3)
        print("Write successfully completed.")
    else:
        print("No incoming Kafka events. Pipeline ready.")

    spark.stop()

if __name__ == "__main__":
    main()
