# airflow/dags/shipyard_master_planning_dag.py
"""
[Apache Airflow 조선소 마스터 스케줄링 배치 파이프라인 DAG]
--------------------------------------------------------------------------------
1. 주요 파이프라인 아키텍처:
   [1. Spark 분산 피처 가공] ➔ [2. OR-Tools CP-SAT 수리최적화] ➔ [3. PostgreSQL 운영 DB 적재 & MinIO 보존] ➔ [4. React 대시보드 알림]

2. 세부 태스크 구성 및 동작 원리:
   - task_1_spark_feature_engineering :
     MinIO/Iceberg의 원천 블록 및 정반 데이터를 PySpark로 분산 로드하여
     4대 피처 마트(호선 부하, 군집 특성, 정반 수용력, 우선순위 스코어)를 가공한 뒤
     MinIO의 'features/' 버킷에 Parquet 형식으로 적재합니다.
   
   - task_2_ortools_master_scheduler :
     872개 블록 전수를 대상으로 Google OR-Tools CP-SAT 결정론적 수리최적화 솔버를 실행하여
     4대 물리 제약(공간/하중/동일베이/시간중복)을 100% 만족하는 최적 마스터 공정표를 산출합니다.
   
   - task_3_export_to_postgres_minio :
     산출된 마스터 공정표를 PostgreSQL 운영 데이터베이스('shipyard_db'의 'master_schedules' 테이블)에
     일괄 적재하고, MinIO 'schedules/' 버킷에도 Parquet 아카이브를 보존합니다.
   
   - task_4_notify_dashboard_ready :
     React 간트 차트 대시보드(http://localhost:3000) 및 외부 시스템에 배치가 완료되었음을 알립니다.

3. 스케줄 주기:
   - 매일 새벽 02:00 정기 자동 실행 ('0 2 * * *')
--------------------------------------------------------------------------------
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os
import sys

# 기본 DAG 설정 파라미터 정의
default_args = {
    'owner': 'shipyard-data-team',
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

# ==============================================================================
# DAG 인스턴스 정의
# ==============================================================================
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

    # --------------------------------------------------------------------------
    # 태스크 의존성(Pipeline DAG Workflow) 정의: 순차 실행 보장
    # --------------------------------------------------------------------------
    task_spark_features >> task_ortools_solve >> task_export_db >> task_notify
