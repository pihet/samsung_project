import urllib.request
import urllib.parse
import json
import random
from datetime import datetime, timedelta
from database import save_product_and_price, get_price_history

import urllib.error

def search_naver_shopping(query, client_id, client_secret, display=40):
    """네이버 쇼핑 API 호출 함수 (items, error_message 반환)"""
    client_id = client_id.strip() if client_id else ""
    client_secret = client_secret.strip() if client_secret else ""

    if not client_id or not client_secret:
        return [], "네이버 Client ID와 Secret을 사이드바에 입력해 주세요."

    if not query or not query.strip():
        return [], "검색어를 입력해 주세요."

    enc_text = urllib.parse.quote(query.strip())
    url = f"https://openapi.naver.com/v1/search/shop.json?query={enc_text}&display={display}"

    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)

    try:
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            data = json.loads(response.read().decode('utf-8'))
            items = []
            for item in data.get('items', []):
                clean_title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"').replace('&amp;', '&')
                items.append({
                    'product_id': item['productId'],
                    'title': clean_title,
                    'category': f"{item.get('category1', '')} > {item.get('category2', '')}",
                    'image_url': item['image'],
                    'mall_name': item['mallName'],
                    'link': item['link'],
                    'lprice': int(item['lprice']) if item['lprice'] else 0
                })
            return items, None
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return [], f"API 인증 실패 (401 Unauthorized): Client ID 또는 Secret이 잘못되었습니다. (ncloud.com이 아닌 developers.naver.com 발급 키인지 확인하세요)"
        elif e.code == 403:
            return [], f"API 권한 오류 (403 Forbidden): 네이버 개발자 센터에서 '검색(쇼핑)' API 권한이 추가되었는지 확인해 주세요."
        elif e.code == 400:
            return [], f"잘못된 요청 (400 Bad Request): 파라미터를 확인해 주세요."
        else:
            return [], f"HTTP 에러 발생 ({e.code}): {e.reason}"
    except Exception as e:
        return [], f"API 호출 중 예외 발생: {str(e)}"

def generate_mock_price_history(product_id, base_price, days=1095, pattern="auto"):
    """
    3년치(최대 1095일) 시계열 가상 데이터 생성기
    
    pattern:
    - 'auto': product_id 해시 기반으로 자동 패턴 할당 (상품마다 각기 다른 할인 양상)
    - 'real_discount_drop': 최근 30일 내 역대 최저가 폭락
    - 'constant_discount': 매일 같은 상시 할인 (Fake Discount)
    - 'fake_hike_before_sale': 할인 직전 가격 인상 후 할인 생색
    - 'price_increase': 최근 가격 상승세
    """
    existing_df = get_price_history(product_id)
    if len(existing_df) >= 10:
        return

    # auto 패턴 결정
    if pattern == "auto":
        patterns = ["real_discount_drop", "constant_discount", "fake_hike_before_sale", "price_increase"]
        pid_hash = sum(ord(c) for c in str(product_id))
        pattern = patterns[pid_hash % len(patterns)]

    now = datetime.now()
    random.seed(int(product_id) if str(product_id).isdigit() else 42)

    # 3년(1095일) 전부터 데이터 생성 (1~3일 간격으로 생성하여 데이터 품질 유지)
    step = 2 if days > 365 else 1
    for i in range(days, 0, -step):
        target_date = (now - timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")
        
        if pattern == "constant_discount":
            # 상시 할인: ±1% 이내 미세 변동만 존재
            multiplier = 1.0 + random.uniform(-0.015, 0.015)
        elif pattern == "real_discount_drop":
            # 역대 최저가: 과거엔 15~35% 더 비쌌다가 최근(7일 전~) 역대 최저가로 하락
            if i > 7:
                multiplier = random.uniform(1.15, 1.35)
            else:
                multiplier = random.uniform(0.98, 1.02)
        elif pattern == "fake_hike_before_sale":
            # 할인 착시: 최근 30일 전 30% 올렸다가 최근 5% 깎아준 척함
            if 7 <= i <= 40:
                multiplier = random.uniform(1.30, 1.45)
            else:
                multiplier = random.uniform(1.10, 1.20)
        elif pattern == "price_increase":
            # 최근 인플레이션/인기 상승으로 꾸준한 가격 상승세
            progress = (days - i) / days  # 0 -> 1
            multiplier = 0.85 + (progress * 0.35) + random.uniform(-0.03, 0.03)
        else:
            multiplier = 1.0

        simulated_price = max(100, int(base_price * multiplier))

        save_product_and_price(
            product_id=product_id,
            title="Sample Product",
            category="Sample",
            image_url="",
            mall_name="Sample Mall",
            link="",
            price=simulated_price,
            collected_at=target_date
        )
    random.seed()  # 시드 초기화
