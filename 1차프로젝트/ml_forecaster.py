import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import Ridge
from statsmodels.tsa.api import Holt
import warnings

warnings.filterwarnings('ignore')

WEEKDAY_KOR = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']

def predict_future_prices(df_history, forecast_days=14):
    """
    과거 가격 이력 DataFrame을 받아 향후 forecast_days(기본 14일) 미래 가격 및 추세를 예측하는 시계열 ML 엔진
    """
    if df_history is None or df_history.empty or len(df_history) < 3:
        return None

    df = df_history.copy()
    df['collected_at'] = pd.to_datetime(df['collected_at'])
    df = df.sort_values('collected_at')

    # 1. 일별 리샘플링 및 결측치 보간 (Daily Resampling)
    daily = df.set_index('collected_at')['price'].resample('D').mean()
    daily = daily.ffill().bfill()
    
    if len(daily) < 3:
        return None

    last_date = daily.index[-1]
    forecast_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
    
    current_price = float(daily.iloc[-1])
    
    # ----------------------------------------------------
    # Model 1: Holt's Linear Exponential Smoothing (Trend)
    # ----------------------------------------------------
    try:
        model_holt = Holt(daily.values, initialization_method="estimated", damped_trend=True)
        fit_holt = model_holt.fit(damping_factor=0.9)
        pred_holt = fit_holt.forecast(forecast_days)
    except Exception:
        # Fallback to simple trend line if Holt fails
        x = np.arange(len(daily))
        z = np.polyfit(x, daily.values, 1)
        p = np.poly1d(z)
        pred_holt = p(np.arange(len(daily), len(daily) + forecast_days))

    # ----------------------------------------------------
    # Model 2: Ridge Regression with Lag & Day-of-Week Features
    # ----------------------------------------------------
    try:
        df_feats = pd.DataFrame({'price': daily.values}, index=daily.index)
        df_feats['dayofweek'] = df_feats.index.dayofweek
        df_feats['time_idx'] = np.arange(len(df_feats))
        
        # Lag features
        df_feats['lag_1'] = df_feats['price'].shift(1)
        df_feats['lag_7'] = df_feats['price'].shift(7).bfill()
        df_feats['rolling_mean_7'] = df_feats['price'].rolling(7, min_periods=1).mean()
        
        train_df = df_feats.dropna()
        if len(train_df) >= 3:
            X_cols = ['dayofweek', 'time_idx', 'lag_1', 'lag_7', 'rolling_mean_7']
            X_train = train_df[X_cols]
            y_train = train_df['price']

            model_ridge = Ridge(alpha=1.0)
            model_ridge.fit(X_train, y_train)

            # Iterative Multi-step Forecasting
            pred_ridge = []
            curr_series = list(daily.values)
            start_idx = len(daily)

            for i, f_date in enumerate(forecast_dates):
                f_dow = f_date.dayofweek
                f_idx = start_idx + i
                lag_1_val = curr_series[-1]
                lag_7_val = curr_series[-7] if len(curr_series) >= 7 else curr_series[0]
                roll_7_val = np.mean(curr_series[-7:]) if len(curr_series) >= 7 else np.mean(curr_series)

                X_next = pd.DataFrame([[f_dow, f_idx, lag_1_val, lag_7_val, roll_7_val]], columns=X_cols)
                next_p = float(model_ridge.predict(X_next)[0])
                pred_ridge.append(next_p)
                curr_series.append(next_p)
            pred_ridge = np.array(pred_ridge)
        else:
            pred_ridge = pred_holt
    except Exception:
        pred_ridge = pred_holt

    # ----------------------------------------------------
    # 앙상블 (Ensemble): Holt 50% + Ridge 50%
    # ----------------------------------------------------
    pred_base = 0.5 * pred_holt + 0.5 * pred_ridge

    # ----------------------------------------------------
    # 요일별 계절성(Day-of-Week Seasonality) 주간 파동 반영
    # ----------------------------------------------------
    df_dow = pd.DataFrame({'price': daily.values, 'dow': daily.index.dayofweek})
    overall_mean = float(np.mean(daily.values))
    dow_means = df_dow.groupby('dow')['price'].mean()
    
    # 요일별 상대 비율 계산 (예: 금/토/일은 상대적으로 할인 비중 반영)
    dow_ratios = {}
    for d in range(7):
        if d in dow_means and overall_mean > 0:
            dow_ratios[d] = float(dow_means[d] / overall_mean)
        else:
            dow_ratios[d] = 1.0

    # 14일 미래 일자별 요일 계절성 적용
    seasonality_factors = np.array([dow_ratios[f_date.dayofweek] for f_date in forecast_dates])
    pred_final = pred_base * seasonality_factors

    # 음수 방지 및 최소 가격 제한 (기존 가격의 30% 이하로 떨어지지 않도록 안정화)
    min_price_floor = max(100.0, current_price * 0.3)
    pred_final = np.maximum(pred_final, min_price_floor)

    # 잔차 기반 신뢰 구간 (Prediction Interval)
    residuals = daily.values[-min(len(daily), 30):] - (pred_holt[:min(len(daily), 30)] if len(pred_holt) >= min(len(daily), 30) else daily.values[-min(len(daily), 30):])
    residual_std = float(np.std(residuals)) if len(residuals) > 1 else current_price * 0.03
    
    lower_bound = pred_final - (1.645 * residual_std * np.sqrt(1 + np.arange(forecast_days) * 0.05))
    upper_bound = pred_final + (1.645 * residual_std * np.sqrt(1 + np.arange(forecast_days) * 0.05))

    # Forecast DataFrame 생성
    forecast_df = pd.DataFrame({
        'collected_at': forecast_dates,
        'price': pred_final.astype(int),
        'lower_bound': lower_bound.astype(int),
        'upper_bound': upper_bound.astype(int),
        'is_forecast': True
    })

    # ----------------------------------------------------
    # 패턴 & 최적 구매 요일 분석
    # ----------------------------------------------------
    # 요일별 과거 평균 가격
    df_dow = pd.DataFrame({'price': daily.values, 'dow': daily.index.dayofweek})
    weekday_avg = df_dow.groupby('dow')['price'].mean().to_dict()
    best_dow_idx = min(weekday_avg, key=weekday_avg.get) if weekday_avg else 0
    best_weekday_name = WEEKDAY_KOR[best_dow_idx]

    # 14일 예측 기간 중 최저가 날짜 및 가격
    min_pred_idx = np.argmin(pred_final)
    best_buy_date = forecast_dates[min_pred_idx]
    best_buy_day_str = f"{best_buy_date.strftime('%m/%d')} ({WEEKDAY_KOR[best_buy_date.dayofweek]})"
    predicted_min_price = int(pred_final[min_pred_idx])

    # 추세 판단 (마지막 예측가 vs 현재가)
    price_diff_pct = ((pred_final[-1] - current_price) / current_price) * 100
    if price_diff_pct <= -2.5:
        trend_direction = "하락"
        trend_summary = f"향후 14일간 약 {abs(price_diff_pct):.1f}% 추가 하락 추세가 예상됩니다."
    elif price_diff_pct >= 2.5:
        trend_direction = "상승"
        trend_summary = f"향후 14일간 약 {price_diff_pct:.1f}% 가격 상승 추세가 예상됩니다."
    else:
        trend_direction = "보합"
        trend_summary = "향후 14일간 현재 가격대에서 큰 변동 없이 보합세를 유지할 것으로 보입니다."

    return {
        'forecast_df': forecast_df,
        'current_price': int(current_price),
        'predicted_min_price': predicted_min_price,
        'predicted_avg_price': int(np.mean(pred_final)),
        'trend_direction': trend_direction,
        'trend_change_pct': round(price_diff_pct, 1),
        'trend_summary': trend_summary,
        'best_buy_day_str': best_buy_day_str,
        'best_weekday_name': best_weekday_name,
        'weekday_avg': weekday_avg
    }

if __name__ == "__main__":
    dates = pd.date_range(end=datetime.now(), periods=60)
    prices = np.sin(np.linspace(0, 10, 60)) * 5000 + 50000
    test_df = pd.DataFrame({'collected_at': dates, 'price': prices})
    result = predict_future_prices(test_df, forecast_days=14)
    print("Test successful!")
    print("Trend Direction:", result['trend_direction'])
    print("Forecast min price:", result['predicted_min_price'])
    print("Best buy day:", result['best_buy_day_str'])
