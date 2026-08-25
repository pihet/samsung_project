# airflow/dags/kafka_producer_pipeline.py
"""
[실전 파이프라인] Airflow에서 KubernetesPodOperator를 사용하여
Strimzi Kafka 공식 이미지로 일꾼 파드를 띄우고, SCRAM-SHA-512 보안 인증을 거쳐
실시간 주문 데이터를 Kafka [my-topic]으로 발행하는 K8s-Native DAG
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'pihet',
    'start_date': datetime(2026, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}

with DAG(
    dag_id='kafka_order_producer_pipeline',
    default_args=default_args,
    description='카프카로 실시간 주문 이벤트 데이터를 전송하는 KubernetesPodOperator 파이프라인',
    schedule=None,
    catchup=False,
    tags=['kafka', 'commerce', 'realtime', 'k8s-pod'],
) as dag:

    # 1. 시작 알림
    task_start = BashOperator(
        task_id='start_order_generation',
        bash_command='echo "=== Starting E-Commerce Order Event Stream on Kubernetes ==="',
    )

    # 2. KubernetesPodOperator: Strimzi Kafka 전용 파드를 띄워 my-topic으로 메시지 보안 발행 
    task_send_to_kafka = KubernetesPodOperator(
        task_id='send_orders_to_kafka',
        namespace='airflow',
        image='quay.io/strimzi/kafka:1.2.0-kafka-4.3.1',
        cmds=['/bin/bash', '-c'],
        arguments=[
            """
printf 'security.protocol=SASL_PLAINTEXT\\nsasl.mechanism=SCRAM-SHA-512\\nsasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required username="my-app-user" password="uk2eajtu8WM5lGgAemy5F8l3qoJh5mwz";\\n' > /tmp/client.properties

ORDER_1='{"order_id": "ORD-1001", "user": "user_kim", "item": "MacBook Pro M3", "amount": 3200000, "timestamp": "'$(date -Iseconds)'"}'
ORDER_2='{"order_id": "ORD-1002", "user": "user_lee", "item": "Sony WH-1000XM5", "amount": 450000, "timestamp": "'$(date -Iseconds)'"}'
ORDER_3='{"order_id": "ORD-1003", "user": "user_park", "item": "Keychron K2", "amount": 120000, "timestamp": "'$(date -Iseconds)'"}'

echo "Sending Order 1: $ORDER_1"
echo "$ORDER_1" | bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9092 --topic my-topic --command-config /tmp/client.properties

echo "Sending Order 2: $ORDER_2"
echo "$ORDER_2" | bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9092 --topic my-topic --command-config /tmp/client.properties

echo "Sending Order 3: $ORDER_3"
echo "$ORDER_3" | bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9092 --topic my-topic --command-config /tmp/client.properties

echo "=== Successfully Published 3 Orders to Kafka topic [my-topic]! ==="
            """
        ],
        name='airflow-kafka-producer-pod',
        is_delete_operator_pod=True,
        get_logs=True,
    )

    # 3. 완료 알림
    task_end = BashOperator(
        task_id='finish_pipeline',
        bash_command='echo "=== Pipeline Completed: Orders are now in Kafka & ready for Spark/Flink processing! ==="',
    )

    task_start >> task_send_to_kafka >> task_end
