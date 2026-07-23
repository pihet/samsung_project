import sqlite3
import pandas as pd
from datetime import datetime
from config import DB_PATH

def get_connection():
    """SQLite 데이터베이스 연결 객체 반환"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """테이블 자동 생성 (products, price_history)"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 상품 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT,
            image_url TEXT,
            mall_name TEXT,
            link TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. 가격 이력 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            price INTEGER NOT NULL,
            collected_at TIMESTAMP NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
    """)

    conn.commit()
    conn.close()

def save_product_and_price(product_id, title, category, image_url, mall_name, link, price, collected_at=None):
    """상품 정보 업데이트 및 가격 레코드 추가"""
    if collected_at is None:
        collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()

    # 상품 정보 Upsert (삽입 또는 갱신)
    cursor.execute("""
        INSERT INTO products (product_id, title, category, image_url, mall_name, link, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(product_id) DO UPDATE SET
            title=excluded.title,
            category=excluded.category,
            image_url=excluded.image_url,
            mall_name=excluded.mall_name,
            link=excluded.link,
            updated_at=excluded.updated_at
    """, (product_id, title, category, image_url, mall_name, link, collected_at))

    # 가격 히스토리 추가
    cursor.execute("""
        INSERT INTO price_history (product_id, price, collected_at)
        VALUES (?, ?, ?)
    """, (product_id, price, collected_at))

    conn.commit()
    conn.close()

def get_price_history(product_id):
    """특정 상품의 가격 이력을 Pandas DataFrame으로 반환"""
    conn = get_connection()
    query = """
        SELECT price, collected_at 
        FROM price_history 
        WHERE product_id = ? 
        ORDER BY collected_at ASC
    """
    df = pd.read_sql_query(query, conn, params=(product_id,))
    conn.close()
    if not df.empty:
        df['collected_at'] = pd.to_datetime(df['collected_at'])
    return df

def get_all_products():
    """저장된 모든 상품 목록 조회"""
    conn = get_connection()
    query = "SELECT * FROM products ORDER BY updated_at DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
