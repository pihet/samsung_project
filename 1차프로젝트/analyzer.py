import pandas as pd
import numpy as np
from ml_forecaster import predict_future_prices

def analyze_price_trend(df_history, days=None, upcoming_events=None):
    """
    상품 가격 이력(DataFrame)을 입력받아 지정 기간(days) 동안의 할인 유형,
    머신러닝 시계열 예측(14일) 및 세일 캘린더 연동 최신 구매 추천 지수를 분석하는 종합 엔진
    """
    if df_history is None or df_history.empty:
        return {
            'current_price': 0,
            'avg_price': 0,
            'min_price': 0,
            'max_price': 0,
            'discount_score': 0,
            'pattern': '데이터 부족',
            'badge': '데이터 수집 필요',
            'badge_color': 'gray',
            'recommendation': '가격 데이터 수집이 진행 중입니다. 며칠간 수집 후 다시 확인해 보세요.',
            'ml_forecast': None
        }

    df = df_history.copy()
    if 'collected_at' in df.columns and days is not None:
        cutoff_date = pd.to_datetime(df['collected_at'].max()) - pd.Timedelta(days=days)
        df = df[df['collected_at'] >= cutoff_date]

    if df.empty:
        df = df_history

    prices = df['price'].values
    current_price = prices[-1]
    avg_price = float(np.mean(prices))
    min_price = int(np.min(prices))
    max_price = int(np.max(prices))
    
    # 변동성 계산 (표준편차 / 평균가)
    std_dev = float(np.std(prices))
    volatility = (std_dev / avg_price) if avg_price > 0 else 0

    # 할인율 (평균가 대비 현재가 절감 비율)
    discount_vs_avg = ((avg_price - current_price) / avg_price * 100) if avg_price > 0 else 0

    # 머신러닝 14일 미래 시계열 예측 실행 (세일 이벤트 할인율 직접 연동)
    ml_forecast = predict_future_prices(df_history, forecast_days=14, upcoming_events=upcoming_events)

    # 1. 상시 할인 패턴 (가격 변동성 2% 이하)
    if volatility <= 0.02:
        pattern = "상시 할인 (Fake Discount)"
        badge = "상시 할인 중 (구매 보류 권장)"
        badge_color = "red"
        discount_score = int(30 + max(-15, min(15, discount_vs_avg)))
        recommendation = "이 상품은 거의 항상 동일한 가격대를 유지하고 있습니다. '할인' 표기에 현혹되지 마시고 급하지 않다면 관망하세요."

    # 2. 진짜 폭락 최저가 패턴 (현재가가 역대/기간 최저가이며, 평균보다 5% 이상 저렴)
    elif current_price <= min_price * 1.01 and discount_vs_avg >= 5.0:
        pattern = "진짜 최저가 달성"
        badge = "지금이 진짜 최저가!"
        badge_color = "green"
        discount_score = int(85 + min(15, discount_vs_avg * 1.2))
        recommendation = "최근 가격 추이 중 가장 저렴한 최저가 구간입니다! 구매하기 아주 좋은 타이밍입니다."

    # 3. 평균가 대비 저렴한 구간
    elif current_price < avg_price:
        pattern = "평소보다 약간 저렴"
        badge = "평소보다 살짝 저렴 (보통)"
        badge_color = "orange"
        discount_score = int(60 + min(20, discount_vs_avg * 1.5))
        recommendation = "평소 판매가보다 소폭 저렴한 수준입니다. 필요하다면 부담 없이 구매하셔도 무방합니다."

    # 4. 평균가보다 오히려 비싼 고가 구간
    else:
        pattern = "평소 가격보다 고가"
        badge = "가격 상승 구간 (비추천)"
        badge_color = "red"
        hike_percent = ((current_price - avg_price) / avg_price * 100)
        discount_score = max(5, int(45 - hike_percent * 2.0))
        recommendation = "평소 평균 판매가보다 높은 시기입니다. 가격이 다시 안정될 때까지 구매를 미루는 것을 추천합니다."

    # ----------------------------------------------------
    # 머신러닝 시계열 예측 결합 조정 (Future Trend Weighting)
    # ----------------------------------------------------
    if ml_forecast:
        trend = ml_forecast['trend_direction']
        pct = ml_forecast['trend_change_pct']
        
        # 14일 후 더 가격이 하락할 것으로 예상되면 점수를 살짝 낮춰 구매 대기 유도
        if trend == "하락":
            discount_score = max(5, discount_score - 8)
            recommendation += f"<br/>[예측]: 향후 14일간 약 {abs(pct)}% 추가 가격 하락이 예상되어 보류를 추천합니다."
        elif trend == "상승":
            discount_score = min(100, discount_score + 5)
            recommendation += f"<br/>[예측]: 향후 14일간 약 {pct}% 가격 상승이 예상되므로 필요한 경우 빠른 조기 구매를 권장합니다."

    # ----------------------------------------------------
    # 쇼핑몰 세일 캘린더 연동 알림 (중복 세일 이벤트 다중 수집)
    # ----------------------------------------------------
    sale_alerts = []
    if upcoming_events:
        for ev in upcoming_events:
            d_left = ev.get('days_left', 99)
            if d_left is not None and 0 <= d_left <= 14:
                sale_alerts.append({
                    'event_name': ev.get('event_name', '대형 할인'),
                    'mall_name': ev.get('mall_name', '쇼핑몰'),
                    'days_left': d_left,
                    'discount_rate_avg': ev.get('discount_rate_avg', 15),
                    'recommend_action': ev.get('recommend_action', 'WAIT')
                })

    return {
        'current_price': current_price,
        'avg_price': int(avg_price),
        'min_price': min_price,
        'max_price': max_price,
        'discount_score': min(100, max(0, discount_score)),
        'pattern': pattern,
        'badge': badge,
        'badge_color': badge_color,
        'recommendation': recommendation,
        'ml_forecast': ml_forecast,
        'sale_alerts': sale_alerts
    }

def calculate_effective_price(lprice, card_discount_rate=0.05, pay_point_rate=0.01):
    """카드 청구할인 및 페이 적립금을 가미한 체감 실구매가 계산"""
    if not lprice or lprice <= 0:
        return 0, 0, 0, 0
    card_discount = int(lprice * card_discount_rate)
    pay_point = int(lprice * pay_point_rate)
    total_savings = card_discount + pay_point
    effective_price = lprice - total_savings
    return effective_price, total_savings, card_discount, pay_point

def find_cheaper_spec_alternatives(current_item, all_items):
    """현재 상품과 유사 스펙이지만 가격이 10%~40% 저렴한 대체 가성비 상품 추천"""
    if not current_item or not all_items:
        return []
    
    cur_p = current_item.get('lprice', 0)
    cur_tags = set(current_item.get('spec_tags', []))
    cur_id = str(current_item.get('product_id'))
    
    alternatives = []
    for item in all_items:
        if str(item.get('product_id')) == cur_id:
            continue
        
        item_p = item.get('lprice', 0)
        # 가격이 10% 이상 저렴한 상품 탐지
        if 0 < item_p < cur_p * 0.90 and item_p >= cur_p * 0.50:
            item_tags = set(item.get('spec_tags', []))
            common_tags = cur_tags.intersection(item_tags)
            
            savings = cur_p - item_p
            savings_pct = int((savings / cur_p) * 100)
            
            alternatives.append({
                'item': item,
                'savings': savings,
                'savings_pct': savings_pct,
                'common_specs': list(common_tags)
            })
            
    # 절약 금액 기준 내림차순 정렬 후 상위 2개 반환
    alternatives.sort(key=lambda x: x['savings'], reverse=True)
    return alternatives[:2]

def clean_product_name(title):
    """제조사/회사명(코카콜라음료, 삼성전자, LG전자, 롯데칠성음료 등)을 제거하고 순수 상품명만 반환"""
    if not title:
        return ""
    import re
    pattern = r'^(?:삼성전자|LG전자|코카콜라음료|코카콜라|롯데칠성음료|롯데칠성|동원F&B|동원|농심|오뚜기|애플|Apple|한성컴퓨터|한성|MSI|ASUS|에이서|Acer|레노버|Lenovo|HP|DELL|삼양식품|삼양|팔도|해태제과|해태|오리온|매일유업|매일|서울우유|남양유업|남양|빙그레|동서식품|동서|대상|청정원|CJ제일제당|CJ|하이트진로|오비맥주|[가-힣A-Za-z0-9]+(?:전자|음료|제과|식품|제약|컴퓨터|코리아|산업|유업))\s+'
    cleaned = re.sub(pattern, '', title.strip(), flags=re.IGNORECASE).strip()
    return cleaned if cleaned else title
