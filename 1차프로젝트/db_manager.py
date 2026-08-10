import os
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt

# ============================================================
# PostgreSQL DB 기본 접속 정보 설정
# (환경 변수 또는 기본값 localhost:5432/buyorwait_db)
# ============================================================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "buyorwait_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "1111")

def get_db_connection(host=None, port=None, dbname=None, user=None, password=None):
    """PostgreSQL 데이터베이스 연결 객체 생성"""
    try:
        conn = psycopg2.connect(
            host=host or DB_HOST,
            port=port or DB_PORT,
            dbname=dbname or DB_NAME,
            user=user or DB_USER,
            password=password or DB_PASS,
            connect_timeout=3
        )
        return conn
    except Exception as e:
        return None

def test_db_connection(host=None, port=None, dbname=None, user=None, password=None):
    """DB 연결 시도 후 상세 에러 결과 반환"""
    try:
        conn = psycopg2.connect(
            host=host or DB_HOST,
            port=port or DB_PORT,
            dbname=dbname or DB_NAME,
            user=user or DB_USER,
            password=password or DB_PASS,
            connect_timeout=3
        )
        conn.close()
        return True, "PostgreSQL 'buyorwait_db' 연결 성공!"
    except Exception as e:
        return False, f"연결 실패: {str(e)}"

def register_user(email, password, nickname, db_pass=None):
    """회원가입 처리 (비밀번호 bcrypt 암호화 저장)"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return False, "데이터베이스 연결에 실패했습니다. DB 설정 및 비밀번호를 확인해 주세요."

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_id FROM users WHERE email = %s;", (email.strip().lower(),))
            if cur.fetchone():
                return False, "이미 가입된 이메일 주소입니다."

            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            cur.execute("""
                INSERT INTO users (email, password_hash, nickname)
                VALUES (%s, %s, %s)
                RETURNING user_id, email, nickname, created_at;
            """, (email.strip().lower(), hashed_pw, nickname.strip()))
            
            new_user = cur.fetchone()
            conn.commit()
            return True, dict(new_user)
    except Exception as e:
        conn.rollback()
        return False, f"회원가입 처리 중 오류 발생: {str(e)}"
    finally:
        conn.close()

def login_user(email, password, db_pass=None):
    """로그인 검증 처리"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return False, "데이터베이스 연결에 실패했습니다. DB 접속 상태를 확인해 주세요."

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_id, email, password_hash, nickname, created_at FROM users WHERE email = %s;", (email.strip().lower(),))
            user = cur.fetchone()
            if not user:
                return False, "존재하지 않는 이메일 주소입니다."

            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                user_dict = dict(user)
                del user_dict['password_hash']
                return True, user_dict
            else:
                return False, "비밀번호가 일치하지 않습니다."
    except Exception as e:
        return False, f"로그인 처리 중 오류 발생: {str(e)}"
    finally:
        conn.close()

def save_product(conn, product):
    """상품 기본 정보 저장/업데이트 (UPSERT)"""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO products (product_id, title, category, image_url, mall_name, current_price, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (product_id) DO UPDATE SET
                title = EXCLUDED.title,
                category = EXCLUDED.category,
                image_url = EXCLUDED.image_url,
                mall_name = EXCLUDED.mall_name,
                current_price = EXCLUDED.current_price,
                updated_at = CURRENT_TIMESTAMP;
        """, (
            str(product.get('product_id')),
            product.get('title', ''),
            product.get('category', ''),
            product.get('image_url', ''),
            product.get('mall_name', '다나와'),
            int(product.get('lprice', 0))
        ))

def add_favorite(user_id, product, target_price=None, db_pass=None):
    """찜한 상품 추가 (products 저장 후 favorites 연결)"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return False, "DB 연결 실패"

    try:
        save_product(conn, product)

        with conn.cursor() as cur:
            p_id = str(product.get('product_id'))
            cur.execute("""
                INSERT INTO favorites (user_id, product_id, target_price)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, product_id) DO UPDATE SET
                    target_price = EXCLUDED.target_price,
                    alert_enabled = TRUE;
            """, (user_id, p_id, target_price))

            cur.execute("""
                INSERT INTO price_history (product_id, price)
                VALUES (%s, %s);
            """, (p_id, int(product.get('lprice', 0))))

            conn.commit()
            return True, "찜한 상품에 추가되었습니다."
    except Exception as e:
        conn.rollback()
        return False, f"찜 추가 실패: {str(e)}"
    finally:
        conn.close()

def remove_favorite(user_id, product_id, db_pass=None):
    """찜한 상품 제거"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return False, "DB 연결 실패"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM favorites
                WHERE user_id = %s AND product_id = %s;
            """, (user_id, str(product_id)))
            conn.commit()
            return True, "찜한 상품에서 삭제되었습니다."
    except Exception as e:
        conn.rollback()
        return False, f"찜 삭제 실패: {str(e)}"
    finally:
        conn.close()

def get_user_favorites(user_id, db_pass=None):
    """특정 회원의 찜한 상품 목록 및 현재 최저가 조회"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT f.favorite_id, f.target_price, f.alert_enabled, f.created_at as favorited_at,
                       p.product_id, p.title, p.category, p.image_url, p.mall_name, p.current_price as lprice
                FROM favorites f
                JOIN products p ON f.product_id = p.product_id
                WHERE f.user_id = %s
                ORDER BY f.created_at DESC;
            """, (user_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()

def is_favorite(user_id, product_id, db_pass=None):
    """특정 상품 찜 여부 확인"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM favorites WHERE user_id = %s AND product_id = %s;
            """, (user_id, str(product_id)))
            return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        conn.close()

def get_upcoming_sales_events(db_pass=None):
    """PostgreSQL shopping_sales_events 테이블에서 다가오는 세일 이벤트 목록 조회"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT event_id, event_name, mall_name, event_type, start_date, end_date, 
                       discount_rate_avg, recommend_action,
                       (start_date - CURRENT_DATE) as days_left
                FROM shopping_sales_events
                WHERE end_date >= CURRENT_DATE
                ORDER BY start_date ASC;
            """)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()
