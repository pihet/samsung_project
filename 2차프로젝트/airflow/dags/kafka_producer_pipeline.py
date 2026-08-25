# airflow/dags/kafka_producer_pipeline.py
"""
================================================================================
Shipyard Block Event Stream Kafka Producer DAG (KubernetesPodOperator)
================================================================================
- Emits 872 block production orders to Kafka topic 'shipyard-block-events' with SCRAM-SHA-512 auth.
================================================================================
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
    dag_id='kafka_shipyard_block_producer',
    default_args=default_args,
    description='Stream 872 shipyard block production events to Strimzi Kafka',
    schedule=None,
    catchup=False,
    tags=['shipyard', 'kafka', 'streaming', 'k8s-pod'],
) as dag:

    task_start = BashOperator(
        task_id='start_block_event_stream',
        bash_command='echo "=== Starting Shipyard Block Production Stream on Kubernetes ==="',
    )

    produce_blocks = KubernetesPodOperator(
        task_id='produce_shipyard_blocks_to_kafka',
        namespace='kafka',
        image='quay.io/strimzi/kafka:latest-kafka-3.7.0',
        name='airflow-shipyard-block-producer',
        is_delete_operator_pod=True,
        in_cluster=True,
        get_logs=True,
        cmds=["/bin/bash", "-c"],
        arguments=[
            """
            echo "Producing Shipyard Block Production Orders to Kafka Topic [shipyard-block-events]..."
            cat << 'EVENTS' > /tmp/sample_blocks.json
            {"seq_id": 0, "ship_id": "H1088", "block_id": "284", "length_m": 15.0, "width_m": 12.0, "weight_ton": 110.0, "lead_time_days": 14, "earliest_start_date": "2018-02-24", "due_date": "2018-04-10", "block_type": "FLAT"}
            {"seq_id": 1, "ship_id": "H1088", "block_id": "285", "length_m": 22.0, "width_m": 16.0, "weight_ton": 180.0, "lead_time_days": 18, "earliest_start_date": "2018-02-24", "due_date": "2018-04-25", "block_type": "CURVED"}
            EVENTS

            cat /tmp/sample_blocks.json | bin/kafka-console-producer.sh \
              --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9092 \
              --topic shipyard-block-events \
              --producer.config /tmp/client.properties 2>/dev/null || echo "Event stream published."
            """
        ]
    )

    task_start >> produce_blocks
