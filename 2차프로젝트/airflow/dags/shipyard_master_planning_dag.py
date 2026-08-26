# airflow/dags/shipyard_master_planning_dag.py
"""
[Apache Airflow 조선소 마스터 스케줄링 배치 파이프라인 DAG]
--------------------------------------------------------------------------------
1. 주요 파이프라인 아키텍처:
   [1. Spark 피처 가공] ➔ [2. OR-Tools CP-SAT 수리최적화] ➔ [3. PostgreSQL 운영 DB 적재 & MinIO 보존] ➔ [4. React 대시보드 알림]

2. 세부 태스크 구성:
   - task_1_spark_feature_engineering : Iceberg 원천 데이터를 Spark로 분산 가공하여 MinIO features/ 에 적재
   - task_2_ortools_master_scheduler   : 872개 블록 전수 대상 Google OR-Tools CP-SAT 최적화 스케줄링 실행
   - task_3_export_to_postgres_minio  : 확정된 마스터 스케줄을 PostgreSQL(master_schedules) 및 MinIO(schedules/)에 저장
   - task_4_notify_dashboard_ready    : React 프론트엔드 대시보드 서빙 준비 완료 알림
--------------------------------------------------------------------------------
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import sys

default_args = {
    'owner': 'shipyard-data-team',
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

with DAG(
    dag_id='shipyard_master_planning_batch_pipeline',
    default_args=default_args,
    description='Automated Shipyard Platen Master Scheduling Pipeline (Spark -> OR-Tools -> PostgreSQL -> MinIO)',
    schedule='0 2 * * *',  # 매일 새벽 02:00 정기 배치 실행
    catchup=False,
    tags=['shipyard', 'lakehouse', 'spark', 'ortools', 'postgres', 'minio', 'batch'],
) as dag:

    # --------------------------------------------------------------------------
    # Task 1: Apache Spark 기반 분산 피처 가공
    # --------------------------------------------------------------------------
    task_spark_features = BashOperator(
        task_id='task_1_spark_feature_engineering',
        bash_command='python /home/kjc/workspace/samsung_project/2차프로젝트/spark/apps/spark_feature_pipeline.py || python spark/apps/spark_feature_pipeline.py'
    )

    # --------------------------------------------------------------------------
    # Task 2: Google OR-Tools CP-SAT 결정론적 마스터 최적화 스케줄링 실행
    # --------------------------------------------------------------------------
    task_ortools_solve = BashOperator(
        task_id='task_2_ortools_master_scheduler',
        bash_command='python /home/kjc/workspace/samsung_project/2차프로젝트/modeling/solver_ortools.py || python modeling/solver_ortools.py'
    )

    # --------------------------------------------------------------------------
    # Task 3: 마스터 스케줄 PostgreSQL 운영 DB 및 MinIO S3 영구 적재
    # --------------------------------------------------------------------------
    task_export_db = BashOperator(
        task_id='task_3_export_to_postgres_minio',
        bash_command='python /home/kjc/workspace/samsung_project/2차프로젝트/modeling/export_schedule_to_postgres.py || python modeling/export_schedule_to_postgres.py'
    )

    # --------------------------------------------------------------------------
    # Task 4: React 대시보드 서빙 완료 알림
    # --------------------------------------------------------------------------
    task_notify = BashOperator(
        task_id='task_4_notify_dashboard_ready',
        bash_command='echo "[Airflow Batch] Master Schedule is now LIVE in PostgreSQL and React Dashboard (http://localhost:3000)!"'
    )

    # 태스크 의존성 연결 (순차 실행)
    task_spark_features >> task_ortools_solve >> task_export_db >> task_notify
