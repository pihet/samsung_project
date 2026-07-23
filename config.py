import os
from dotenv import load_dotenv

load_dotenv()

# 환경 변수 또는 직접 설정값 로드
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# SQLite 데이터베이스 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "price_tracker.db")
