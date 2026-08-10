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

def get_user_by_id(user_id, db_pass=None):
    """user_id로 회원 정보 조회 (세션 유지 복원용)"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_id, email, nickname, created_at FROM users WHERE user_id = %s;", (user_id,))
            user = cur.fetchone()
            return dict(user) if user else None
    except Exception:
        return None
    finally:
        conn.close()

def save_product(conn, product):
    """상품 기본 정보 저장/업데이트 (UPSERT)"""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO products (product_id, title, category, image_url, mall_name, link, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (product_id) DO UPDATE SET
                title = EXCLUDED.title,
                category = EXCLUDED.category,
                image_url = EXCLUDED.image_url,
                mall_name = EXCLUDED.mall_name,
                link = EXCLUDED.link,
                updated_at = CURRENT_TIMESTAMP;
        """, (
            str(product.get('product_id')),
            product.get('title', ''),
            product.get('category', ''),
            product.get('image_url', ''),
            product.get('mall_name', ''),
            product.get('link', '')
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
                INSERT INTO price_history (product_id, price, collected_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP);
            """, (p_id, int(product.get('lprice', 0))))

            conn.commit()
            return True, "찜한 상품에 추가되었습니다."
    except Exception as e:
        conn.rollback()
        return False, f"찜 추가 실패: {str(e)}"
    finally:
        conn.close()

def update_favorite_target_price(user_id, product_id, target_price, db_pass=None):
    """찜한 상품의 목표 알림가 업데이트 (알림 재발송 플래그 리셋)"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return False, "DB 연결 실패"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE favorites
                SET target_price = %s, alert_enabled = TRUE, is_alert_sent = FALSE
                WHERE user_id = %s AND product_id = %s;
            """, (target_price, user_id, str(product_id)))
            conn.commit()
            return True, "목표 알림가가 변경되었습니다."
    except Exception as e:
        conn.rollback()
        return False, f"목표가 변경 실패: {str(e)}"
    finally:
        conn.close()

import requests

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.naver.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

def send_price_alert_email(to_email, nickname, product_title, current_price, target_price, link="https://www.danawa.com"):
    """목표가 달성 시 회원 이메일로 HTML 이메일 알림 발송 (Resend API 우선 지원, SMTP 하이브리드)"""
    from analyzer import clean_product_name
    display_title = clean_product_name(product_title)
    subject = f"[BuyOrWait] 축하합니다! 찜하신 '{display_title[:20]}...' 상품이 목표가에 도달했습니다!"
    
    html_body = f"""
    <html>
    <body style="font-family: 'Pretendard', sans-serif; background-color: #F8FAFC; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #FFFFFF; border: 2px solid #115DCE; border-radius: 12px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
            <h2 style="color: #115DCE; margin-top: 0;">BuyOrWait 목표가 달성 알림</h2>
            <p style="font-size: 16px; color: #334155;">안녕하세요, <b>{nickname}</b>님!</p>
            <p style="font-size: 15px; color: #475569; line-height: 1.6;">
                찜하신 관심 상품의 가격이 설정하신 <b>목표 알림가 이하로 하락</b>하였습니다.<br>
                지금이 최적의 구매 찬스입니다!
            </p>
            <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 20px 0;" />
            <div style="background: #F1F5F9; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
                <div style="font-weight: 800; font-size: 18px; color: #0F172A; margin-bottom: 10px;">{display_title}</div>
                <div style="font-size: 15px; color: #64748B; margin-bottom: 6px;">
                    목표 알림가: <span style="font-weight: 700; color: #059669;">{target_price:,}원</span>
                </div>
                <div style="font-size: 17px; color: #0F172A;">
                    현재 실시간 최저가: <span style="font-size: 22px; font-weight: 900; color: #115DCE;">{current_price:,}원</span>
                </div>
            </div>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{link}" target="_blank" style="background: #115DCE; color: #FFFFFF; font-size: 16px; font-weight: 800; padding: 14px 28px; border-radius: 8px; text-decoration: none; display: inline-block;">
                    최저가 구매하러 가기
                </a>
            </div>
        </div>
    </body>
    </html>
    """

    # 1. Resend API 우선 발송 시도 (개인 비밀번호 없는 기업형 API)
    resend_key = os.getenv("RESEND_API_KEY", RESEND_API_KEY)
    if resend_key:
        try:
            headers = {
                'Authorization': f'Bearer {resend_key.strip()}',
                'Content-Type': 'application/json'
            }
            payload = {
                'from': 'BuyOrWait <onboarding@resend.dev>',
                'to': [to_email],
                'subject': subject,
                'html': html_body
            }
            res = requests.post('https://api.resend.com/emails', headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                print(f"[Resend Email Success] 수신자: {to_email}, Response ID: {res.json().get('id')}")
                return True, "Resend API로 이메일 알림이 전송되었습니다!"
        except Exception as e:
            print(f"[Resend Email Warning] Resend 발송 실패, SMTP fallback 시도: {e}")

    # 2. SMTP fallback 시도
    if SMTP_USER and SMTP_PASS:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = to_email
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())
            server.quit()
            return True, "SMTP로 이메일 알림이 전송되었습니다!"
        except Exception as e:
            print(f"[SMTP Email Error]: {e}")

    # 3. 시뮬레이션 처리
    print(f"[Email Notification Simulator] 수신자: {to_email}, 상품: {product_title}, 현재가: {current_price:,}원, 목표가: {target_price:,}원")
    return True, "가상 이메일 알림 처리 완료"

def check_and_send_target_price_alerts(user_id, db_pass=None):
    """특정 회원의 찜 목록 중 목표 알림가 이하로 하락한 상품을 탐지하여 이메일 발송 및 갱신"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return 0, "DB 연결 실패"

    sent_count = 0
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT email, nickname FROM users WHERE user_id = %s;", (user_id,))
            user_info = cur.fetchone()
            if not user_info:
                return 0, "회원 정보를 찾을 수 없습니다."

            user_email = user_info['email']
            nickname = user_info['nickname']

            cur.execute("""
                SELECT f.favorite_id, f.target_price, f.product_id, p.title, p.link,
                       COALESCE((
                           SELECT price FROM price_history ph 
                           WHERE ph.product_id = p.product_id 
                           ORDER BY collected_at DESC LIMIT 1
                       ), 0) as lprice
                FROM favorites f
                JOIN products p ON f.product_id = p.product_id
                WHERE f.user_id = %s 
                  AND f.target_price IS NOT NULL 
                  AND f.target_price > 0
                  AND f.alert_enabled = TRUE
                  AND (f.is_alert_sent IS FALSE OR f.is_alert_sent IS NULL);
            """, (user_id,))

            alerts = cur.fetchall()

            for item in alerts:
                lprice = item['lprice']
                target_p = item['target_price']
                if lprice > 0 and lprice <= target_p:
                    success, msg = send_price_alert_email(
                        to_email=user_email,
                        nickname=nickname,
                        product_title=item['title'],
                        current_price=lprice,
                        target_price=target_p,
                        link=item['link'] if item['link'] else "https://www.danawa.com"
                    )
                    if success:
                        cur.execute("UPDATE favorites SET is_alert_sent = TRUE WHERE favorite_id = %s;", (item['favorite_id'],))
                        sent_count += 1

            conn.commit()
            return sent_count, f"{sent_count}건의 목표가 달성 알림 메일 처리 완료"
    except Exception as e:
        conn.rollback()
        print(f"[check_and_send_target_price_alerts error]: {e}")
        return 0, f"알림 처리 실패: {str(e)}"
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
                       p.product_id, p.title, p.category, p.image_url, p.mall_name, p.link,
                       COALESCE((
                           SELECT price FROM price_history ph 
                           WHERE ph.product_id = p.product_id 
                           ORDER BY collected_at DESC LIMIT 1
                       ), 0) as lprice
                FROM favorites f
                JOIN products p ON f.product_id = p.product_id
                WHERE f.user_id = %s
                ORDER BY f.created_at DESC;
            """, (user_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"[get_user_favorites error]: {e}")
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

def get_top_trend_products(limit=4, db_pass=None):
    """PostgreSQL DB에서 실제 유효한 이미지를 가진 최근 수집/인기 상품 N개 조회"""
    conn = get_db_connection(password=db_pass)
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT p.product_id, p.title, p.category, p.image_url, p.mall_name, p.link,
                       COALESCE((
                           SELECT price FROM price_history ph 
                           WHERE ph.product_id = p.product_id 
                           ORDER BY collected_at DESC LIMIT 1
                       ), 0) as lprice
                FROM products p
                WHERE p.image_url IS NOT NULL 
                  AND p.image_url != ''
                  AND p.image_url LIKE 'http%%'
                ORDER BY p.updated_at DESC
                LIMIT %s;
            """, (limit,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"[get_top_trend_products error]: {e}")
        return []
    finally:
        conn.close()
