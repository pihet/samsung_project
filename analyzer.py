import pandas as pd
import numpy as np

def analyze_price_trend(df_history, days=None):
    """
    상품 가격 이력(DataFrame)을 입력받아 지정 기간(days) 동안의 할인 유형 및 구매 추천 지수를 분석하는 엔진
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
            'recommendation': '가격 데이터 수집이 진행 중입니다. 며칠간 수집 후 다시 확인해 보세요.'
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

    # 가격 범위 내 위치 (0 = 최저가, 100 = 최고가)
    price_range = max_price - min_price
    if price_range > 0:
        position_percentile = ((current_price - min_price) / price_range) * 100
    else:
        position_percentile = 50.0

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

    return {
        'current_price': current_price,
        'avg_price': int(avg_price),
        'min_price': min_price,
        'max_price': max_price,
        'discount_score': min(100, max(0, discount_score)),
        'pattern': pattern,
        'badge': badge,
        'badge_color': badge_color,
        'recommendation': recommendation
    }
