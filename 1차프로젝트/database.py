import pandas as pd
from datetime import datetime
import db_manager

def get_connection(db_pass=None):
    """PostgreSQL 데이터베이스 연결 객체 반환"""
    return db_manager.get_db_connection(password=db_pass)

def init_db(db_pass=None):
    """PostgreSQL 테이블 자동 생성 (products, price_history 및 인덱스)"""
    try:
        conn = get_connection(db_pass=db_pass)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT,
                image_url TEXT,
                mall_name TEXT,
                link TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id SERIAL PRIMARY KEY,
                product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
                price INT NOT NULL,
                collected_at TIMESTAMP NOT NULL
            );
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_pid_date ON price_history(product_id, collected_at);
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopping_sales_events (
                event_id SERIAL PRIMARY KEY,
                event_name TEXT NOT NULL,
                mall_name TEXT NOT NULL,
                event_type TEXT,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                discount_rate_avg INT DEFAULT 15,
                recommend_action TEXT DEFAULT 'WAIT'
            );
        """)

        # 테이블이 비어있거나 세일 이벤트가 없으면 샘플 세일 캘린더 자동 팝퓰레이트
        cursor.execute("SELECT COUNT(*) FROM shopping_sales_events;")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO shopping_sales_events (event_name, mall_name, event_type, start_date, end_date, discount_rate_avg, recommend_action)
                VALUES 
                ('G마켓/옥션 빅스마일데이', 'G마켓', '대형 브랜드 세일', CURRENT_DATE + INTERVAL '2 days', CURRENT_DATE + INTERVAL '9 days', 20, 'WAIT'),
                ('쿠팡 와우 빅세일', '쿠팡', '와우회원 전용 세일', CURRENT_DATE + INTERVAL '4 days', CURRENT_DATE + INTERVAL '11 days', 18, 'WAIT'),
                ('11번가 십일절 브랜드위크', '11번가', '월간 정기 세일', CURRENT_DATE + INTERVAL '6 days', CURRENT_DATE + INTERVAL '13 days', 15, 'WAIT');
            """)

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[database.py] init_db PostgreSQL error: {e}")

def save_product_and_price(product_id, title, category, image_url, mall_name, link, price, collected_at=None, db_pass=None):
    """PostgreSQL 상품 정보 Upsert 및 가격 레코드 추가"""
    if collected_at is None:
        collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = get_connection(db_pass=db_pass)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO products (product_id, title, category, image_url, mall_name, link, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id) DO UPDATE SET
                title = EXCLUDED.title,
                category = EXCLUDED.category,
                image_url = EXCLUDED.image_url,
                mall_name = EXCLUDED.mall_name,
                link = EXCLUDED.link,
                updated_at = EXCLUDED.updated_at
        """, (product_id, title, category, image_url, mall_name, link, collected_at))

        cursor.execute("""
            INSERT INTO price_history (product_id, price, collected_at)
            VALUES (%s, %s, %s)
        """, (product_id, price, collected_at))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[database.py] save_product_and_price PostgreSQL error: {e}")

def bulk_save_price_history(product_id, title, category, image_url, mall_name, link, history_records, db_pass=None):
    """PostgreSQL 상품 정보 1회 Upsert 및 가격 히스토리 일괄(Bulk) 삽입"""
    if not history_records:
        return
        
    try:
        conn = get_connection(db_pass=db_pass)
        cursor = conn.cursor()

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO products (product_id, title, category, image_url, mall_name, link, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id) DO UPDATE SET
                title = EXCLUDED.title,
                category = EXCLUDED.category,
                image_url = EXCLUDED.image_url,
                mall_name = EXCLUDED.mall_name,
                link = EXCLUDED.link,
                updated_at = EXCLUDED.updated_at
        """, (product_id, title, category, image_url, mall_name, link, now_str))

        cursor.executemany("""
            INSERT INTO price_history (product_id, price, collected_at)
            VALUES (%s, %s, %s)
        """, [(product_id, rec[0], rec[1]) for rec in history_records])

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[database.py] bulk_save_price_history PostgreSQL error: {e}")

def get_price_history(product_id, db_pass=None):
    """PostgreSQL 특정 상품의 시계열 가격 이력을 Pandas DataFrame으로 초고속 반환"""
    try:
        conn = get_connection(db_pass=db_pass)
        query = """
            SELECT price, collected_at 
            FROM price_history 
            WHERE product_id = %s 
            ORDER BY collected_at ASC
        """
        df = pd.read_sql_query(query, conn, params=(product_id,))
        conn.close()
        if not df.empty:
            df['collected_at'] = pd.to_datetime(df['collected_at'])
        return df
    except Exception as e:
        print(f"[database.py] get_price_history PostgreSQL error: {e}")
        return pd.DataFrame()

def get_all_products(db_pass=None):
    """PostgreSQL 저장된 모든 상품 목록 조회"""
    try:
        conn = get_connection(db_pass=db_pass)
        query = "SELECT * FROM products ORDER BY updated_at DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"[database.py] get_all_products PostgreSQL error: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    init_db()
    print("PostgreSQL Database initialized successfully!")
