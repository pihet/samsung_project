# modeling/export_schedule_to_postgres.py
"""
[마스터 스케줄 PostgreSQL 운영 DB 적재 스크립트]
--------------------------------------------------------------------------------
1. 주요 목적:
   - Google OR-Tools CP-SAT 최적화 솔버가 산출한 872개 블록의 마스터 공정표 데이터를
     PostgreSQL 운영 데이터베이스('shipyard_db' / 'master_schedules' 테이블)에 적재합니다.
   - 1차 프로젝트(5432 포트, buyorwait_db)와의 충돌을 방지하기 위해 5433 포트를 우선 지원합니다.

2. 데이터 아키텍처 상의 위치:
   - OR-Tools Solver -> [PostgreSQL shipyard_db] -> React 간트 차트 대시보드
--------------------------------------------------------------------------------
"""

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import execute_values

# 1. 프로젝트 루트 경로 및 중앙 경로(utils.paths) 연동
cur_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(cur_dir)
sys.path.append(project_root)

from utils.paths import SCHEDULES_DIR

# 2. PostgreSQL 접속 정보 (포트 5433 우선, 5432 폴백)
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "postgres")
PG_TARGET_DB = os.environ.get("PG_DB", "shipyard_db")

# 포트 자동 탐색 (5433 우선 시도, 실패 시 5432 시도)
ports_to_try = [int(os.environ.get("PG_PORT", 5433)), 5432]

print("=" * 80)
print(" 마스터 스케줄 -> PostgreSQL 2차 프로젝트 전용 DB 적재 파이프라인")
print(f" - Host: {PG_HOST}, Target DB: {PG_TARGET_DB}, User: {PG_USER}")
print("=" * 80)

# 3. 마스터 스케줄 CSV 로드
schedule_file = os.path.join(SCHEDULES_DIR, "ortools_scheduling_results.csv")
if not os.path.exists(schedule_file):
    print(f"[오류] 스케줄 결과 파일을 찾을 수 없습니다: {schedule_file}")
    sys.exit(1)

df_sched = pd.read_csv(schedule_file)
print(f"\n[Step 1/3] OR-Tools 마스터 스케줄 로드 완료 ({len(df_sched)}개 배정 레코드)")

# 4. PostgreSQL 연결 및 shipyard_db 자동 생성
conn = None
active_port = None

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

# shipyard_db 데이터베이스 존재 여부 확인 및 자동 생성
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

# 5. shipyard_db 데이터베이스에 접속하여 master_schedules 테이블 생성 및 적재
print(f"\n[Step 2/3] '{PG_TARGET_DB}' 데이터베이스에 master_schedules 테이블 생성 및 연결...")
conn_target = psycopg2.connect(
    host=PG_HOST,
    port=active_port,
    user=PG_USER,
    password=PG_PASSWORD,
    dbname=PG_TARGET_DB
)
cur_target = conn_target.cursor()

create_table_query = """
CREATE TABLE IF NOT EXISTS master_schedules (
    seq_id INT PRIMARY KEY,
    block_id VARCHAR(50),
    ship_id VARCHAR(50),
    platen_idx INT,
    platen_id VARCHAR(50),
    platen_name VARCHAR(100),
    planned_start_day INT,
    planned_end_day INT,
    due_date_day INT,
    delay_days INT,
    processing_time_days INT,
    is_feasible BOOLEAN,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
cur_target.execute(create_table_query)
conn_target.commit()

# 6. Bulk Insert
print("\n[Step 3/3] 872개 마스터 스케줄 레코드 일괄 적재 중...")
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

execute_values(cur_target, insert_query, records)
conn_target.commit()

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
