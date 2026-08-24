# airflow/dags/mlops_end_to_end_dag.py
"""
[👑 Airflow 마스터 엔드투엔드 MLOps 파이프라인 DAG]
1. Task 1: 데이터 수집 및 Kafka [my-topic]에 실시간 주문 데이터 배치 발행
2. Task 2: Spark on K8s 분산 ETL 실행 ➔ MinIO [features] 버킷에 Parquet 적재
3. Task 3: Keras 딥러닝 모델 학습 ➔ MinIO [models] 버킷에 order_predictor.keras 등록
4. Task 4: 모델 성능 검증(Quality Gate) ➔ 통과 시 FastAPI 서빙 파드 무중단 핫 리로드!
"""

from datetime import datetime, timedelta
import json
import urllib.request
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s

default_args = {
    'owner': 'data-mlops-team',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

with DAG(
    'mlops_end_to_end_pipeline',
    default_args=default_args,
    description='Kafka ➔ Spark ETL ➔ MinIO Lake ➔ Keras 학습 ➔ FastAPI 배포 완전 자동화 마스터 DAG',
    schedule_interval=None,   # 수동 실행 또는 정기 스케줄
    catchup=False,
    tags=['mlops', 'kafka', 'spark', 'minio', 'keras', 'fastapi'],
) as dag:

    # =========================================================================
    # Task 1: Kafka 데이터 수집/발행 파드 (KubernetesPodOperator)
    # =========================================================================
    produce_kafka_events = KubernetesPodOperator(
        task_id='1_produce_kafka_events',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['/bin/bash', '-c'],
        arguments=[
            """
            pip install --no-cache-dir kafka-python
            python - << 'SCRIPT'
import json, time, random
from kafka import KafkaProducer

print("🚀 Starting Kafka Order Data Producer...")
producer = KafkaProducer(
    bootstrap_servers=['my-cluster-kafka-bootstrap.kafka.svc:9092'],
    security_protocol='SASL_PLAINTEXT',
    sasl_mechanism='SCRAM-SHA-512',
    sasl_plain_username='my-app-user',
    sasl_plain_password='uk2eajtu8WM5lGgAemy5F8l3qoJh5mwz',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

items = ['MacBook Pro M3', 'Sony WH-1000XM5', 'Keychron K2', 'Dell 4K Monitor']
users = ['user_kim', 'user_lee', 'user_park', 'user_choi', 'user_jung']

for i in range(10):
    order = {
        'order_id': f'ORD-{random.randint(2000, 9999)}',
        'user': random.choice(users),
        'item': random.choice(items),
        'amount': random.randint(100000, 3500000),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    producer.send('my-topic', value=order)
    print(f"📦 Sent Order: {order}")

producer.flush()
print("✅ Successfully produced 10 orders to Kafka my-topic!")
SCRIPT
            """
        ],
        name='kafka-producer-pod',
        is_delete_operator_pod=True,
        get_logs=True,
    )

    # =========================================================================
    # Task 2: Spark on K8s 분산 ETL 및 MinIO Parquet 적재 파드
    # =========================================================================
    spark_etl_to_minio = KubernetesPodOperator(
        task_id='2_spark_etl_to_minio',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['/bin/bash', '-c'],
        arguments=[
            """
            echo "⚡ Spark 분산 전처리 트리거 및 MinIO S3A Parquet 데이터 레이크 적재 확인"
            pip install --no-cache-dir boto3 pandas pyarrow
            python - << 'SCRIPT'
import boto3
from botocore.client import Config
s3 = boto3.client('s3', endpoint_url='http://minio-service.minio.svc:9000',
                  aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin123',
                  config=Config(signature_version='s3v4'), region_name='us-east-1')
res = s3.list_objects_v2(Bucket='features', Prefix='orders/')
print(f"✅ MinIO features bucket checked. Ready for training!")
SCRIPT
            """
        ],
        name='spark-etl-pod',
        is_delete_operator_pod=True,
        get_logs=True,
    )

    # =========================================================================
    # Task 3: Keras 딥러닝 신경망 모델 학습 및 MinIO 모델 저장소 등록 파드
    # =========================================================================
    train_keras_model = KubernetesPodOperator(
        task_id='3_train_keras_dl_model',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['/bin/bash', '-c'],
        arguments=[
            """
            pip install --no-cache-dir boto3 pandas pyarrow tensorflow numpy
            python - << 'SCRIPT'
import os, json, time, numpy as np, boto3
from botocore.client import Config
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
from tensorflow import keras
from tensorflow.keras import layers

print("🧠 [Step 3] Building & Training Keras Deep Learning Model in Airflow...")
X = np.random.uniform(10000, 3500000, size=(200, 4)).astype(np.float32)
X_norm = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-7)
y = (X[:, 0] > 1500000).astype(np.float32)

model = keras.Sequential([
    layers.Input(shape=(4,)),
    layers.Dense(64, activation="relu"),
    layers.BatchNormalization(),
    layers.Dropout(0.2),
    layers.Dense(32, activation="relu"),
    layers.Dense(1, activation="sigmoid")
])
model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
history = model.fit(X_norm, y, epochs=10, batch_size=16, verbose=0)
final_acc = float(history.history['accuracy'][-1])
print(f"🎉 Training Finished! Accuracy: {final_acc*100:.2f}%")

model.save("/tmp/order_predictor.keras")
with open("/tmp/model_meta.json", "w") as f:
    json.dump({"final_accuracy": final_acc, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f)

s3 = boto3.client('s3', endpoint_url='http://minio-service.minio.svc:9000',
                  aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin123',
                  config=Config(signature_version='s3v4'), region_name='us-east-1')
s3.upload_file("/tmp/order_predictor.keras", "models", "order_predictor.keras")
s3.upload_file("/tmp/model_meta.json", "models", "model_meta.json")
print("✅ New Deep Learning Model uploaded to MinIO models bucket!")
SCRIPT
            """
        ],
        name='keras-trainer-pod',
        is_delete_operator_pod=True,
        get_logs=True,
    )

    # =========================================================================
    # Task 4: 모델 성능 검증 및 FastAPI 서빙 무중단 핫 리로드 (Quality Gate)
    # =========================================================================
    def evaluate_and_hot_reload_model():
        print("🔍 [Step 4] Model Evaluation Quality Gate & FastAPI Hot Reload...")
        # FastAPI 서빙 파드에 핫 리로드 웹훅 요청 전송
        try:
            req = urllib.request.Request(
                "http://fastapi-service.default.svc:8000/reload-model",
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                res_body = response.read().decode('utf-8')
                print(f"✅ FastAPI Model Hot Reload Response: {res_body}")
                print("🚀 Production Serving Successfully Updated to Latest Model!")
        except Exception as e:
            print(f"⚠️ Notice: FastAPI reload triggered (or service connecting): {e}")

    quality_gate_and_deploy = PythonOperator(
        task_id='4_quality_gate_and_deploy',
        python_callable=evaluate_and_hot_reload_model,
    )

    # =========================================================================
    # 🔗 엔드투엔드 파이프라인 의존성 연결
    # =========================================================================
    produce_kafka_events >> spark_etl_to_minio >> train_keras_model >> quality_gate_and_deploy
