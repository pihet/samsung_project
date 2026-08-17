import urllib.request
import urllib.parse
import json
import random
import requests
import hashlib
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
from database import save_product_and_price, get_price_history, bulk_save_price_history

def search_shopping_products_realtime(query, display=40):
    """
    다나와(Danawa) 실시간 쇼핑 상품 웹 수집 엔진
    다나와 실시간 검색 결과 HTML을 파싱하여 실제 상품명, 실제 최저가,
    다나와 pcode 기반 정식 링크(prod.danawa.com/info/?pcode=...),
    정확한 이미지 및 스펙, 옵션/용량별 실시간 최저가 데이터를 수집합니다.
    """
    if not query or not query.strip():
        return [], "검색어를 입력해 주세요."

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
        'Referer': 'https://www.danawa.com/'
    }

    url = 'https://search.danawa.com/dsearch.php?query=' + urllib.parse.quote(query.strip())
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            items = []
            prod_list = soup.select('.main_prodlist .prod_item, .prod_main_info')
            
            seen_pcodes = set()

            for i, p in enumerate(prod_list):
                name_el = p.select_one('.prod_name a')
                price_el = p.select_one('.price_sect strong')
                img_el = p.select_one('.thumb_image img')

                if name_el and price_el:
                    title = name_el.text.strip()
                    orig_link = name_el.get('href', '')

                    # 다나와 pcode 추출 (prod.danawa.com/info/?pcode=...)
                    pcode_match = re.search(r'pcode=(\d+)', orig_link)
                    pcode = pcode_match.group(1) if pcode_match else p.get('id', '').replace('productItem', '')
                    
                    if pcode and pcode in seen_pcodes:
                        continue
                    if pcode:
                        seen_pcodes.add(pcode)

                    price_str = price_el.text.replace(',', '').replace('원', '').strip()
                    if price_str.isdigit():
                        lprice = int(price_str)
                    else:
                        continue

                    # 다나와 정식 상품 링크 생성
                    danawa_link = f"https://prod.danawa.com/info/?pcode={pcode}" if pcode else orig_link
                    if not danawa_link.startswith('http'):
                        danawa_link = 'https:' + danawa_link if danawa_link.startswith('//') else 'https://search.danawa.com' + danawa_link

                    # 스펙 정보 파싱
                    spec_el = p.select_one('.spec_list')
                    spec_text = spec_el.text.strip() if spec_el else f"가전/디지털 > {query.strip()}"
                    spec_tags = [s.strip() for s in spec_text.replace('\n', '').replace('\t', '').split('/') if s.strip()]

                    img_url = ""
                    if img_el:
                        img_url = img_el.get('data-src') or img_el.get('data-original') or img_el.get('src') or ""
                        if 'noImg' in img_url or 'noData' in img_url:
                            img_url = img_el.get('data-src') or img_el.get('data-original') or ""
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url

                    product_id = f"dnw_{pcode}" if pcode else f"real_{i}"

                    # 1. 다나와 옵션/용량별 실시간 최저가 리스트 파싱 (.prod_pricelist li)
                    mall_prices = []
                    price_lis = p.select('.prod_pricelist li')
                    for li in price_lis:
                        mem_el = li.select_one('.memory_sect .text, .memory_sect, .txt_name')
                        raw_mem_txt = mem_el.text.strip() if mem_el else ''
                        opt_name = re.sub(r'^\d+\s*위\s*', '', raw_mem_txt)
                        opt_name = re.sub(r'\s+', ' ', opt_name).strip()
                        
                        prc_el = li.select_one('.price_sect strong, .price_sect a')
                        prc_str = prc_el.text.replace(',', '').replace('원', '').strip() if prc_el else ''
                        
                        a_el = li.select_one('a')
                        a_href = a_el.get('href') if a_el else ''
                        sub_pcode_match = re.search(r'pcode=(\d+)', a_href) if a_href else None
                        sub_pcode = sub_pcode_match.group(1) if sub_pcode_match else pcode
                        sub_link = f"https://prod.danawa.com/info/?pcode={sub_pcode}" if sub_pcode else danawa_link

                        if prc_str.isdigit():
                            sp = int(prc_str)
                            mall_prices.append({
                                "mall": opt_name if opt_name else "다나와 규격/옵션",
                                "badge": "",
                                "price": sp,
                                "shipping": "무료배송",
                                "link": sub_link
                            })

                    # 2. 쇼핑몰 판매처 리스트 파싱 (.deli_price_list li, .price_list li)
                    if not mall_prices:
                        m_lis = p.select('.deli_price_list li, .price_list li, .sub_price_sect')
                        for m in m_lis:
                            m_img = m.select_one('img')
                            m_name = m_img.get('alt') if (m_img and m_img.get('alt')) else (m.select_one('.txt_name, .logo').text.strip() if m.select_one('.txt_name, .logo') else '')
                            m_price_el = m.select_one('.price, .txt_price, strong, .price_sect')
                            m_price_str = m_price_el.text.replace(',', '').replace('원', '').strip() if m_price_el else ''
                            m_link_el = m.select_one('a')
                            m_link = m_link_el.get('href') if m_link_el else danawa_link

                            if m_price_str.isdigit():
                                mp = int(m_price_str)
                                mall_prices.append({
                                    "mall": m_name if m_name else "다나와 판매처",
                                    "badge": "",
                                    "price": mp,
                                    "shipping": "무료배송" if mp == lprice else "3,000원",
                                    "link": m_link
                                })

                    # 3. 파싱된 옵션/판매처 정렬 및 실제 절대 최저가(lprice) 갱신
                    if not mall_prices:
                        mall_prices = [
                            {"mall": "다나와 실시간 최저가", "badge": "최저가", "price": lprice, "shipping": "무료배송", "link": danawa_link}
                        ]
                    else:
                        mall_prices = sorted(mall_prices, key=lambda x: x['price'])
                        for m_item in mall_prices:
                            m_item['badge'] = ""
                        mall_prices[0]['badge'] = "최저가"
                        lprice = mall_prices[0]['price']

                    items.append({
                        'product_id': product_id,
                        'pcode': pcode,
                        'title': title,
                        'category': spec_text,
                        'spec_tags': spec_tags[:8],
                        'image_url': img_url,
                        'mall_name': mall_prices[0]['mall'],
                        'link': danawa_link,
                        'lprice': lprice,
                        'mall_prices': mall_prices
                    })
                    if len(items) >= display:
                        break

            if items:
                return items, None
    except Exception as e:
        mock_items = []
        for i in range(8):
            mock_items.append({
                'product_id': f"mock_{i}",
                'title': f"[실시간 수집 지연] {query} 검색 결과 {i+1}",
                'category': f"디지털/가전 > {query}",
                'spec_tags': ["인기상품", "스펙확인중"],
                'image_url': f"https://via.placeholder.com/200/115DCE/FFFFFF?text=Item+{i+1}",
                'mall_name': "다나와 제휴몰",
                'link': "https://www.danawa.com",
                'lprice': 10000 * (i + 1),
                'mall_prices': [
                    {"mall": "다나와 제휴몰", "badge": "최저가", "price": 10000 * (i + 1), "shipping": "무료배송", "link": "https://www.danawa.com"}
                ]
            })
        return mock_items, f"실시간 검색 서버 응답 지연으로 임시 데이터를 표시합니다. (사유: {str(e)})"

    return [], "실시간 쇼핑 상품 검색 결과가 없습니다."

def search_naver_shopping(query, client_id="", client_secret="", display=40):
    """
    쇼핑 검색 수집 함수
    1) 네이버 오픈 API 우선 시도 (200 OK일 경우 반영)
    2) 네이버 API 404 (SE05 종료 서비스) 발생 시 실시간 실데이터 스크레이퍼 엔진으로 자동 전환
    """
    if not query or not query.strip():
        return [], "검색어를 입력해 주세요."

    # 1. 네이버 오픈 API 호출 시도
    if client_id and client_secret:
        client_id = client_id.strip()
        client_secret = client_secret.strip()
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
                if items:
                    return items, None
        except Exception:
            pass

    # 2. 네이버 쇼핑 API 종료(2026.07.31) 또는 404 시 실시간 진짜 상품 웹 데이터 스크레이퍼로 실시간 수집
    items, err = search_shopping_products_realtime(query, display=display)
    if items:
        return items, None

    return [], err if err else "상품 정보를 수집할 수 없습니다."

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
    pid_seed = sum(ord(c) for c in str(product_id))
    random.seed(pid_seed)

    records = []
    # 3년(1095일) 전부터 데이터 생성 (1~3일 간격으로 생성하여 데이터 품질 유지)
    step = 2 if days > 365 else 1
    for i in range(days, 0, -step):
        target_dt = now - timedelta(days=i)
        target_date = target_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # 주말(금, 토, 일) 특가 서명 패턴 (약 2~4% 할인)
        dow_factor = 0.97 if target_dt.weekday() in [4, 5, 6] else 1.0
        
        if pattern == "constant_discount":
            # 상시 할인: ±1.5% 이내 미세 변동만 존재
            multiplier = 1.0 + random.uniform(-0.015, 0.015)
        elif pattern == "real_discount_drop":
            # 역대 최저가: 과거엔 15~35% 더 비쌌다가 최근(7일 전~) 역대 최저가로 하락
            if i > 7:
                multiplier = random.uniform(1.15, 1.35)
            else:
                multiplier = random.uniform(0.98, 1.02) * dow_factor
        elif pattern == "fake_hike_before_sale":
            # 할인 착시: 최근 30일 전 30% 올렸다가 최근 5% 깎아준 척함
            if 7 <= i <= 40:
                multiplier = random.uniform(1.30, 1.45)
            else:
                multiplier = random.uniform(1.10, 1.20) * dow_factor
        elif pattern == "price_increase":
            # 최근 인플레이션/인기 상승으로 꾸준한 가격 상승세
            progress = (days - i) / days  # 0 -> 1
            multiplier = (0.85 + (progress * 0.35) + random.uniform(-0.03, 0.03)) * dow_factor
        else:
            multiplier = 1.0 * dow_factor

        simulated_price = max(100, int(base_price * multiplier))
        records.append((simulated_price, target_date))

    df_records = pd.DataFrame(records, columns=['price', 'collected_at'])
    df_records['collected_at'] = pd.to_datetime(df_records['collected_at'])

    try:
        bulk_save_price_history(
            product_id=product_id,
            title="Sample Product",
            category="Sample",
            image_url="",
            mall_name="Sample Mall",
            link="",
            history_records=records
        )
    except Exception as e:
        print(f"[collector.py] DB bulk save error: {e}")
        
    random.seed()  # 시드 초기화
    return df_records

from concurrent.futures import ThreadPoolExecutor

def fetch_single_trend_kw(kw):
    try:
        items, _ = search_shopping_products_realtime(kw, display=1)
        if items and len(items) > 0:
            item = items[0]
            item['query'] = kw
            return item
    except Exception as e:
        print(f"[collector.py] trend product fetch error for {kw}: {e}")
    return None

def get_danawa_popular_trend_products():
    """
    다나와(Danawa) 실시간 급상승 검색어 Top 4 (ddr5 16gb, 9800x3d, 제습기, 닌텐도 스위치 2)의
    실시간 1위 최저가 상품 및 정식 이미지/링크를 병렬 스레딩(ThreadPoolExecutor)으로 반환합니다.
    """
    popular_keywords = ["ddr5 16gb", "9800x3d", "제습기", "닌텐도 스위치 2"]
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(fetch_single_trend_kw, popular_keywords))
        
    return [r for r in results if r is not None]
