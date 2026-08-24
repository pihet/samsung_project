# airflow/dags/hello_k8s_dag.py
"""
[Airflow 실전 가이드] 
Kubernetes 환경에서 동작하는 데이터 파이프라인(DAG)의 핵심 구조와 실무 기능 총정리
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

# ==============================================================================
# 1. default_args: DAG에 속한 모든 태스크(Task)에 공통으로 적용되는 기본 정책
# ==============================================================================
default_args = {
    'owner': 'pihet',                       # 파이프라인 관리자 이름
    'depends_on_past': False,               # 이전 날짜의 실행이 실패했어도 오늘 실행할지 여부 (False: 독립 실행)
    'start_date': datetime(2026, 1, 1),     # 스케줄 기준 시작 날짜
    'email': ['wjdcks524@naver.com'],       # 실패/성공 알림을 받을 이메일 주소
    'email_on_failure': False,              # 작업 실패 시 이메일 발송 여부
    'email_on_retry': False,                # 재시도 시 이메일 발송 여부
    'retries': 2,                           # 작업 실패 시 최대 재시도 횟수 (실무 필수 ⭐)
    'retry_delay': timedelta(minutes=1),    # 재시도 전 대기 시간 (1분 후 재시도)
    'execution_timeout': timedelta(minutes=10), # 태스크가 무한 루프에 빠져 서버를 마비시키는 것을 방지 (10분 초과 시 강제 종료)
}

# ==============================================================================
# 2. PythonOperator에서 실행할 커스텀 파이썬 비즈니스 로직 함수
# ==============================================================================
def process_data_logic(**context):
    """
    실제 데이터 정제, API 호출, DB 쿼리 등의 파이썬 로직을 작성하는 영역
    - context: Airflow가 제공하는 메타데이터 (실행 시간, DAG ID 등)
    """
    execution_date = context.get('ds') # '2026-08-24' 형태의 실행 날짜 문자열
    print(f"[{execution_date}] 파이썬 데이터 처리 함수가 성공적으로 실행되었습니다!")
    
    # 태스크 간에 작은 데이터(결과값)를 넘겨줄 때는 XCom을 사용 (return 값)
    return {"status": "success", "processed_records": 100}

# ==============================================================================
# 3. DAG 정의 (전체 파이프라인 메타데이터 및 스케줄링)
# ==============================================================================
with DAG(
    dag_id='hello_kubernetes_dag',          # 웹 UI 화면에 노출될 고유 식별자 (영어, 밑줄 권장)
    default_args=default_args,
    description='쿠버네티스 파드로 실행되는 첫 번째 데이터 파이프라인',
    schedule=None,                          # 실행 주기: None(수동/API 트리거), '@daily'(매일 자정), '*/5 * * * *'(5분마다)
    catchup=False,                          # 과거 시작일부터 현재까지의 밀린 주기들을 한 번에 실행할지 여부 (False 권장)
    max_active_runs=1,                      # 동시에 실행될 수 있는 이 DAG의 최대 실행 수 (동시 실행 충돌 방지)
    tags=['study', 'k8s', 'kafka', 'spark'], # 웹 UI에서 필터링하여 검색하기 위한 태그들
) as dag:

    # ==========================================================================
    # 4. 태스크(Task / Operator) 정의: 실제 실행될 단위 작업들
    # ==========================================================================

    # [Task 1: BashOperator] 리눅스 쉘 명령어 / 스크립트 실행
    task_start = BashOperator(
        task_id='print_start',
        bash_command='echo "=== Airflow on Kubernetes Pipeline Started! ==="',
    )

    # [Task 2: PythonOperator] 파이썬 함수 실행 (가장 많이 쓰임 ⭐)
    task_python_process = PythonOperator(
        task_id='run_python_processing',
        python_callable=process_data_logic,
    )

    # [Task 3: BashOperator] 병렬 처리 테스트 작업 A (날짜 확인)
    task_parallel_a = BashOperator(
        task_id='check_current_date',
        bash_command='echo "Current Date: $(date)"',
    )

    # [Task 4: BashOperator] 병렬 처리 테스트 작업 B (메모리 확인)
    task_parallel_b = BashOperator(
        task_id='check_system_status',
        bash_command='echo "System OK. KubernetesExecutor Pod is Running!"',
    )

    # [Task 5: BashOperator] 최종 완료 정리 작업
    task_end = BashOperator(
        task_id='pipeline_finished',
        bash_command='echo "=== All Pipeline Tasks Completed Successfully! ==="',
    )

    # ==========================================================================
    # 5. 의존성(Dependency / 순서) 연결: 순차 실행 및 분기/병렬 실행 구성
    # ==========================================================================
    #
    #                 ┌──► [Task 3: parallel_a] ──┐
    # [Task 1] ──► [Task 2]                      ├──► [Task 5: end]
    #                 └──► [Task 4: parallel_b] ──┘
    #
    # 1번 완료 후 ➔ 2번 실행
    # 2번 완료 후 ➔ 3번과 4번이 쿠버네티스 파드 2대로 "동시에 병렬(Parallel) 실행!"
    # 3번과 4번이 둘 다 끝나야 ➔ 최종 5번 실행!
    #
    task_start >> task_python_process >> [task_parallel_a, task_parallel_b] >> task_end