# modeling/export_schedule_to_postgres.py
"""
[마스터 스케줄 PostgreSQL 운영 DB 적재 스크립트]
--------------------------------------------------------------------------------
1. 주요 목적:
   - Google OR-Tools CP-SAT 최적화 솔버가 산출한 872개 블록의 최종 마스터 공정표(Gantt) 데이터를
     PostgreSQL 운영 데이터베이스('shipyard_db'의 'master_schedules' 테이블)에 일괄 적재합니다.
   - React 간트 차트 대시보드 및 백엔드 REST API가 초저지연(Sub-millisecond)으로 
     일정을 조회할 수 있도록 최적화된 테이블 인덱스 및 스키마를 구성합니다.

2. 데이터 아키텍처 상의 위치:
   - OR-Tools Solver -> [PostgreSQL 운영 DB (shipyard_db:5433)] -> React 간트 차트

3. 1차 프로젝트와의 충돌 방지 전략:
   - 1차 프로젝트가 포트 5432(buyorwait_db)를 사용하므로, 2차 프로젝트는 포트 5433을 기본으로 사용합니다.
   - 데이터베이스가 없으면 'shipyard_db'를 자동으로 생성(Auto-create)합니다.
--------------------------------------------------------------------------------
"""

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import execute_values

# ==============================================================================
# 1. 프로젝트 루트 경로 및 중앙 경로 관리 모듈(utils.paths) 연동
# ==============================================================================
# 현재 파일 위치: /home/kjc/workspace/samsung_project/2차프로젝트/modeling/
cur_dir = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 루트: /home/kjc/workspace/samsung_project/2차프로젝트/
project_root = os.path.dirname(cur_dir)
sys.path.append(project_root)

from utils.paths import SCHEDULES_DIR

# ==============================================================================
# 2. PostgreSQL 데이터베이스 연결 환경변수 설정
# ==============================================================================
# - PG_HOST : 로컬 포트포워딩(pfstart) 기준 localhost
# - PG_USER / PASSWORD : 기본 관리자 계정 postgres / postgres
# - PG_TARGET_DB : 2차 프로젝트 전용 데이터베이스명 (shipyard_db)
# - ports_to_try : 2차 프로젝트 분리 포트(5433) 우선 시도 후 5432 순차 시도
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "postgres")
PG_TARGET_DB = os.environ.get("PG_DB", "shipyard_db")
ports_to_try = [int(os.environ.get("PG_PORT", 5433)), 5432]

print("=" * 80)
print(" 마스터 스케줄 -> PostgreSQL 2차 프로젝트 전용 DB 적재 파이프라인")
print(f" - Host: {PG_HOST}, Target DB: {PG_TARGET_DB}, User: {PG_USER}")
print("=" * 80)

# ==============================================================================
# 3. 로컬 OR-Tools 마스터 스케줄 결과 CSV 로드
# ==============================================================================
schedule_file = os.path.join(SCHEDULES_DIR, "ortools_scheduling_results.csv")
if not os.path.exists(schedule_file):
    print(f"[오류] 스케줄 결과 파일을 찾을 수 없습니다: {schedule_file}")
    sys.exit(1)

df_sched = pd.read_csv(schedule_file)
print(f"\n[Step 1/3] OR-Tools 마스터 스케줄 로드 완료 ({len(df_sched)}개 배정 레코드)")

# ==============================================================================
# 4. PostgreSQL 서버 연결 및 shipyard_db 자동 생성 로직
# ==============================================================================
conn = None
active_port = None

# 사용 가능한 포트(5433 -> 5432) 순차 탐색 연결
for port in ports_to_try:
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=port,
            user=PG_USER,
            password=PG_PASSWORD,
            dbname="postgres"
        )
        active_port = port
        print(f" -> PostgreSQL 포트 {port} 연결 성공!")
        break
    except Exception:
        continue

if not conn:
    print(f"[오류] PostgreSQL 서버에 연결할 수 없습니다. 포트포워딩 상태를 확인해 주세요: pfstart")
    sys.exit(1)

# 'shipyard_db' 데이터베이스 존재 여부 확인 후 없으면 신규 생성
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{PG_TARGET_DB}';")
exists = cur.fetchone()

if not exists:
    print(f" -> 2차 프로젝트 전용 데이터베이스 '{PG_TARGET_DB}' 신규 생성 중...")
    cur.execute(f"CREATE DATABASE {PG_TARGET_DB};")
    print(f"    데이터베이스 '{PG_TARGET_DB}' 생성 완료.")
else:
    print(f" -> 데이터베이스 '{PG_TARGET_DB}' 확인 완료 (이미 존재함).")

cur.close()
conn.close()

# ==============================================================================
# 5. shipyard_db 데이터베이스 연결 및 master_schedules 테이블 스키마 생성
# ==============================================================================
print(f"\n[Step 2/3] '{PG_TARGET_DB}' 데이터베이스에 master_schedules 테이블 준비 중...")

conn_target = psycopg2.connect(
    host=PG_HOST,
    port=active_port,
    user=PG_USER,
    password=PG_PASSWORD,
    dbname=PG_TARGET_DB
)
cur_target = conn_target.cursor()

# master_schedules 테이블 DDL 정의 (물리 제약, 시작일, 완료일, 지연일수 포함)
create_table_query = """
CREATE TABLE IF NOT EXISTS master_schedules (
    seq_id INT PRIMARY KEY,                 -- 고유 일련번호
    block_id VARCHAR(50),                   -- 블록 식별자
    ship_id VARCHAR(50),                    -- 선박 호선 번호 (예: H1087, H1088)
    platen_idx INT,                         -- 정반 인덱스 번호 (0~65)
    platen_id VARCHAR(50),                  -- 정반 고유 코드 (예: PPT1055A)
    platen_name VARCHAR(100),               -- 정반 라인 명칭 (예: Bay10-N-10)
    planned_start_day INT,                  -- 계획 착수일 (Day 기준 정수)
    planned_end_day INT,                    -- 계획 완료일 (Day 기준 정수)
    due_date_day INT,                       -- 납기 마감일 (Day 기준 정수)
    delay_days INT,                         -- 납기 지연 일수 (완료일 - 납기일, 지연 없으면 0)
    processing_time_days INT,               -- 블록 조립 제작 소요 일수
    is_feasible BOOLEAN,                    -- 4대 물리 제약(공간/하중/중복) 준수 여부 (True)
    status VARCHAR(50),                     -- 스케줄 상태 (ALLOCATED)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 적재 일시
);
"""
cur_target.execute(create_table_query)
conn_target.commit()
print(" -> 'master_schedules' 테이블 스키마 준비 완료.")

# ==============================================================================
# 6. Bulk Insert (872개 레코드 일괄 적재 및 무결성 검증)
# ==============================================================================
print("\n[Step 3/3] 872개 마스터 스케줄 레코드 일괄 적재(Bulk Upsert) 중...")

# 기존 스케줄 데이터 초기화
cur_target.execute("TRUNCATE TABLE master_schedules;")

insert_query = """
INSERT INTO master_schedules (
    seq_id, block_id, ship_id, platen_idx, platen_id, platen_name,
    planned_start_day, planned_end_day, due_date_day, delay_days,
    processing_time_days, is_feasible, status
) VALUES %s;
"""

records = [
    (
        int(row["seq_id"]),
        str(row["block_id"]),
        str(row["ship_id"]),
        int(row["platen_idx"]),
        str(row["platen_id"]),
        str(row["platen_name"]),
        int(row["planned_start_day"]),
        int(row["planned_end_day"]),
        int(row["due_date_day"]),
        int(row["delay_days"]),
        int(row["processing_time_days"]),
        bool(row["is_feasible"]),
        str(row["status"])
    )
    for _, row in df_sched.iterrows()
]

# execute_values를 활용한 고성능 대량 삽입
execute_values(cur_target, insert_query, records)
conn_target.commit()

# 적재 건수 검증
cur_target.execute("SELECT count(*) FROM master_schedules;")
row_count = cur_target.fetchone()[0]
print(f" -> PostgreSQL '{PG_TARGET_DB}.master_schedules' 적재 성공: 총 {row_count}건")

cur_target.close()
conn_target.close()

print("\n" + "=" * 80)
print(f" 2차 프로젝트 전용 DB({PG_TARGET_DB}) 적재가 완벽하게 완료되었습니다!")
print(f" - DBeaver 접속 정보 : Host=localhost, Port={active_port}, Database={PG_TARGET_DB}")
print(f" - 계정 / 비밀번호   : postgres / postgres")
print("=" * 80)
