# utils/view_parquet.py
"""
[Parquet 파일 뷰어 유틸리티]
터미널에서 Parquet 데이터 파일의 컬럼, 행 수, 데이터 내용을 표 형태로 즉시 조회합니다.

사용법:
  python utils/view_parquet.py blocks
  python utils/view_parquet.py platens
  python utils/view_parquet.py schedules
  python utils/view_parquet.py <파일경로.parquet>
"""

import os
import sys
import pandas as pd

# Pandas 터미널 출력 옵션 설정 (모든 컬럼을 줄바꿈 없이 넓게 표시)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.max_rows", 20)

cur_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(cur_dir)

shortcuts = {
    "blocks": os.path.join(project_root, "data", "processed", "features", "featured_blocks.parquet"),
    "platens": os.path.join(project_root, "data", "processed", "features", "featured_platens.parquet"),
    "schedules": os.path.join(project_root, "data", "processed", "schedules", "master_schedule_ortools.parquet")
}

target = sys.argv[1] if len(sys.argv) > 1 else "blocks"
file_path = shortcuts.get(target, target)

if not os.path.isabs(file_path):
    file_path = os.path.join(project_root, file_path)

if not os.path.exists(file_path):
    print(f"[오류] 파일을 찾을 수 없습니다: {file_path}")
    print(f"사용 가능한 단축키: {list(shortcuts.keys())}")
    sys.exit(1)

print("=" * 100)
print(f" Parquet 파일 내용 미리보기: {os.path.basename(file_path)}")
print(f" 경로: {file_path}")
print("=" * 100)

df = pd.read_parquet(file_path)
print(f" - 전체 데이터 크기: {len(df)} 행 × {len(df.columns)} 열")
print(f" - 컬럼 목록: {list(df.columns)}")
print("\n[상위 5개 행 데이터 미리보기]:")
print(df.head(5))
print("=" * 100)
