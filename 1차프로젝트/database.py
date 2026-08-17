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

        # 3계층 DW Layer 1: raw_price_logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_price_logs (
                log_id SERIAL PRIMARY KEY,
                product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
                raw_price INT NOT NULL,
                seller_name TEXT DEFAULT '다나와/오픈마켓',
                crawled_at TIMESTAMP NOT NULL
            );
        """)

        # 3계층 DW Layer 2: dm_daily_price_clean (5단계 전처리 완료 데이터 마트)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dm_daily_price_clean (
                product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
                dt DATE NOT NULL,
                price_clean INT NOT NULL,
                is_interpolated BOOLEAN DEFAULT FALSE,
                is_spike_corrected BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (product_id, dt)
            );
        """)

        # 3계층 DW Layer 2: dm_model_forecasts (ML 14일 예측 마트)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dm_model_forecasts (
                product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
                forecast_date DATE NOT NULL,
                predicted_price INT NOT NULL,
                best_model_name TEXT DEFAULT 'Auto-ARIMA',
                model_mape FLOAT DEFAULT 1.24,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (product_id, forecast_date)
            );
        """)

        # 3계층 DW Layer 3: product_price_summary (실시간 서빙 요약 마트)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_price_summary (
                product_id TEXT PRIMARY KEY REFERENCES products(product_id) ON DELETE CASCADE,
                current_price INT NOT NULL,
                lowest_price_ever INT NOT NULL,
                recommend_badge TEXT DEFAULT '지금이 진짜 최저가!',
                trend_pct FLOAT DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_raw_logs_pid_date ON raw_price_logs(product_id, crawled_at);
            CREATE INDEX IF NOT EXISTS idx_dm_clean_pid_dt ON dm_daily_price_clean(product_id, dt);
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
    """PostgreSQL 상품 정보 Upsert 및 가격 레코드 추가 (raw_price_logs)"""
    if collected_at is None:
        collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = get_connection(db_pass=db_pass)
        if not conn:
            return
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
            INSERT INTO raw_price_logs (product_id, raw_price, crawled_at)
            VALUES (%s, %s, %s)
        """, (product_id, price, collected_at))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[database.py] save_product_and_price PostgreSQL error: {e}")

def bulk_save_price_history(product_id, title, category, image_url, mall_name, link, history_records, db_pass=None):
    """PostgreSQL 상품 정보 1회 Upsert 및 가격 히스토리 일괄(Bulk) 삽입 (raw_price_logs)"""
    if not history_records:
        return
        
    try:
        conn = get_connection(db_pass=db_pass)
        if not conn:
            return
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
            INSERT INTO raw_price_logs (product_id, raw_price, crawled_at)
            VALUES (%s, %s, %s)
        """, [(product_id, rec[0], rec[1]) for rec in history_records])

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[database.py] bulk_save_price_history PostgreSQL error: {e}")

def get_price_history(product_id, db_pass=None):
    """PostgreSQL 특정 상품의 시계열 가격 이력을 Pandas DataFrame으로 초고속 반환 (Data Mart 우선)"""
    try:
        conn = get_connection(db_pass=db_pass)
        if not conn:
            return pd.DataFrame()
        query_mart = """
            SELECT price_clean as price, dt as collected_at 
            FROM dm_daily_price_clean 
            WHERE product_id = %s 
            ORDER BY dt ASC
        """
        df = pd.read_sql_query(query_mart, conn, params=(product_id,))
        if df.empty:
            query_raw = """
                SELECT raw_price as price, crawled_at as collected_at 
                FROM raw_price_logs 
                WHERE product_id = %s 
                ORDER BY crawled_at ASC
            """
            df = pd.read_sql_query(query_raw, conn, params=(product_id,))
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
        if not conn:
            return pd.DataFrame()
        query = "SELECT * FROM products ORDER BY updated_at DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"[database.py] get_all_products PostgreSQL error: {e}")
        return pd.DataFrame()

def update_data_mart(db_pass=None):
    """raw_price_logs ➔ dm_daily_price_clean 5단계 전처리 데이터 마트 자동 동기화 가공 배치"""
    try:
        conn = get_connection(db_pass=db_pass)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT product_id FROM raw_price_logs;")
        pids = [r[0] for r in cursor.fetchall()]

        for pid in pids:
            df_p = pd.read_sql_query("SELECT raw_price as price, crawled_at FROM raw_price_logs WHERE product_id=%s ORDER BY crawled_at ASC;", conn, params=(pid,))
            if df_p.empty:
                continue
            df_p['crawled_at'] = pd.to_datetime(df_p['crawled_at'])
            daily = df_p.set_index('crawled_at').resample('D')['price'].mean().to_frame()
            daily['price_clean'] = daily['price'].interpolate(method='linear', limit=3)
            daily['is_interpolated'] = daily['price'].isna() & daily['price_clean'].notna()
            daily['price_clean'] = daily['price_clean'].ffill().bfill().astype(int)

            Q1 = daily['price_clean'].quantile(0.25)
            Q3 = daily['price_clean'].quantile(0.75)
            IQR = Q3 - Q1
            lower_b = Q1 - 2.5 * IQR
            upper_b = Q3 + 2.5 * IQR
            daily['is_outlier'] = (daily['price_clean'] < lower_b) | (daily['price_clean'] > upper_b)
            daily['price_final'] = daily['price_clean'].copy()
            daily['is_spike_corrected'] = False

            idx_list = daily.index
            for i in range(1, len(daily) - 1):
                curr_idx = idx_list[i]
                if daily.loc[curr_idx, 'is_outlier']:
                    prev_p = daily.loc[idx_list[i-1], 'price_clean']
                    next_p = daily.loc[idx_list[i+1], 'price_clean']
                    curr_p = daily.loc[curr_idx, 'price_clean']
                    if abs(prev_p - next_p) < 0.05 * prev_p and abs(curr_p - prev_p) > 0.15 * prev_p:
                        daily.loc[curr_idx, 'price_final'] = int((prev_p + next_p) / 2)
                        daily.loc[curr_idx, 'is_spike_corrected'] = True

            for dt_val, row in daily.iterrows():
                dt_str = dt_val.strftime('%Y-%m-%d')
                cursor.execute("""
                    INSERT INTO dm_daily_price_clean (product_id, dt, price_clean, is_interpolated, is_spike_corrected)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (product_id, dt) DO UPDATE SET
                        price_clean = EXCLUDED.price_clean,
                        is_interpolated = EXCLUDED.is_interpolated,
                        is_spike_corrected = EXCLUDED.is_spike_corrected;
                """, (pid, dt_str, int(row['price_final']), bool(row['is_interpolated']), bool(row['is_spike_corrected'])))

        conn.commit()
        cursor.close()
        conn.close()
        print(f"[database.py] Data Mart dm_daily_price_clean 동기화 배치 완료 ({len(pids)}개 상품)")
    except Exception as e:
        print(f"[database.py] update_data_mart error: {e}")

if __name__ == "__main__":
    init_db()
    print("PostgreSQL Database initialized successfully!")

