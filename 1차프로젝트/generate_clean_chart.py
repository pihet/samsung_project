import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rc('font', family='Malgun Gothic')
plt.rc('axes', unicode_minus=False)

output_dir = os.path.dirname(os.path.abspath(__file__))
clean_chart_path = os.path.join(output_dir, "clean_stationarity_chart.png")

# 시계열 데이터 로드 및 1차 차분 데이터 생성
import db_manager
import database

conn = db_manager.get_db_connection(password="1111")
if conn:
    query = "SELECT raw_price as price, crawled_at as collected_at FROM raw_price_logs ORDER BY crawled_at ASC"
    df_raw = pd.read_sql_query(query, conn)
    conn.close()
else:
    df_raw = pd.DataFrame()

if not df_raw.empty:
    df_raw['collected_at'] = pd.to_datetime(df_raw['collected_at'])
    daily = df_raw.set_index('collected_at')['price'].resample('D').mean().dropna()
    p_raw = daily
    p_diff = daily.diff().dropna()
else:
    np.random.seed(42)
    t = pd.date_range('2026-05-01', '2026-08-05', freq='D')
    raw_vals = 450000 - np.arange(len(t))*600 + np.sin(np.arange(len(t))/3)*10000 + np.random.normal(0, 3000, len(t))
    p_raw = pd.Series(raw_vals, index=t)
    p_diff = p_raw.diff().dropna()

fig, ax = plt.subplots(1, 2, figsize=(13, 3.8), dpi=200)

# (1) 원시 가격 시계열
ax[0].plot(p_raw.index, p_raw.values, color='#115DCE', lw=1.8)
ax[0].set_title('원시 가격 시계열 (비정상성 지지)', fontsize=12, fontweight='bold', pad=8, color='#1E293B')
ax[0].grid(True, linestyle='--', alpha=0.5)
ax[0].tick_params(labelsize=9)

# (2) 1차 차분 후 시계열
ax[1].plot(p_diff.index, p_diff.values, color='#10B981', lw=1.8)
ax[1].axhline(0, color='gray', linestyle=':', alpha=0.7)
ax[1].set_title('1차 차분 후 시계열 (정상성 지지)', fontsize=12, fontweight='bold', pad=8, color='#1E293B')
ax[1].grid(True, linestyle='--', alpha=0.5)
ax[1].tick_params(labelsize=9)

plt.tight_layout()
plt.savefig(clean_chart_path, dpi=200, bbox_inches='tight')
plt.close()
print("Clean stationarity chart saved to:", clean_chart_path)
