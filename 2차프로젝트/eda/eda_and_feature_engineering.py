# eda/eda_and_feature_engineering.py
"""
================================================================================
 [EDA] 탐색적 데이터 분석, 도메인 파생 피처 생성 및 K-Means 군집화
================================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)

raw_data_dir = os.path.join(base_dir, "data/standardized")
processed_dir = os.path.join(base_dir, "data/processed")
os.makedirs(processed_dir, exist_ok=True)

print("=" * 80)
print(" [Step 1: EDA] 데이터 탐색 및 피처 엔지니어링 파이프라인 가동")
print("=" * 80)

# 1. 데이터셋 로드
df_blocks = pd.read_csv(os.path.join(raw_data_dir, "block_information.csv"))
df_platens = pd.read_csv(os.path.join(raw_data_dir, "platen_information.csv"))
df_initial = pd.read_csv(os.path.join(raw_data_dir, "initial_platen_status.csv"))

print(f" 로드 완료: 블록 {len(df_blocks)}건 | 정반 {len(df_platens)}건 | 초기점유 {len(df_initial)}건")

# 2. 정반 제원 파싱
def parse_dimension(dim_str):
    if not isinstance(dim_str, str) or '*' not in dim_str:
        return 20.0, 20.0
    parts = dim_str.split('*')
    try:
        return float(parts[0]), float(parts[1])
    except:
        return 20.0, 20.0

dim_parsed = df_platens['dimensions'].apply(parse_dimension)
df_platens['platen_length_m'] = [d[0] for d in dim_parsed]
df_platens['platen_width_m'] = [d[1] for d in dim_parsed]
df_platens['platen_area_m2'] = df_platens['platen_length_m'] * df_platens['platen_width_m']

# 3. 블록 파생 변수 생성
df_blocks['block_area_m2'] = df_blocks['length_m'] * df_blocks['width_m']
df_blocks['aspect_ratio'] = df_blocks['length_m'] / df_blocks['width_m'].replace(0, 1.0)
df_blocks['density_ton_per_m2'] = df_blocks['weight_ton'] / df_blocks['block_area_m2'].replace(0, 1.0)

df_blocks['est_dt'] = pd.to_datetime(df_blocks['earliest_start_date'])
df_blocks['due_dt'] = pd.to_datetime(df_blocks['due_date'])
df_blocks['total_window_days'] = (df_blocks['due_dt'] - df_blocks['est_dt']).dt.days
df_blocks['slack_days'] = df_blocks['total_window_days'] - df_blocks['lead_time_days']
df_blocks['urgency_ratio'] = (df_blocks['lead_time_days'] / df_blocks['total_window_days'].replace(0, 1.0)).clip(0.0, 1.0)

# 4. K-Means 4대 군집화
cluster_features = ['length_m', 'width_m', 'weight_ton', 'lead_time_days', 'slack_days', 'urgency_ratio']
X = df_blocks[cluster_features].fillna(0)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
df_blocks['cluster_id'] = kmeans.fit_predict(X_scaled)

cluster_labels = {
    0: "Type-A (Standard Medium)",
    1: "Type-B (Small Light)",
    2: "Type-C (Large Heavy)",
    3: "Type-D (Long-lead Urgent)"
}
df_blocks['cluster_name'] = df_blocks['cluster_id'].map(cluster_labels)

# 5. 저장 및 차트 생성
out_block_path = os.path.join(processed_dir, "featured_blocks.csv")
out_platen_path = os.path.join(processed_dir, "featured_platens.csv")

df_blocks.to_csv(out_block_path, index=False, encoding='utf-8')
df_platens.to_csv(out_platen_path, index=False, encoding='utf-8')

# 4분할 시각화 차트
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
sns.scatterplot(data=df_blocks, x='block_area_m2', y='weight_ton', hue='cluster_name', palette='tab10', ax=axes[0, 0], alpha=0.8)
axes[0, 0].set_title('1. Block Area (m²) vs Weight (Ton) by Cluster', fontweight='bold')

sns.histplot(df_blocks['lead_time_days'], bins=25, kde=True, color='teal', ax=axes[0, 1])
axes[0, 1].set_title('2. Process Lead Time (Days) Distribution', fontweight='bold')

sns.scatterplot(data=df_platens, x='platen_area_m2', y='crane_capacity_ton', color='crimson', s=90, ax=axes[1, 0])
axes[1, 0].set_title('3. Platen Area (m²) vs Crane Capacity (Ton)', fontweight='bold')

sns.histplot(df_blocks['slack_days'], bins=30, kde=True, color='indigo', ax=axes[1, 1])
axes[1, 1].axvline(0, color='red', linestyle='--', label='Critical Due Line')
axes[1, 1].set_title('4. Due Date Slack Days Buffer Distribution', fontweight='bold')
axes[1, 1].legend()

plt.tight_layout()
chart_path = os.path.join(processed_dir, "eda_feature_analysis.png")
plt.savefig(chart_path, dpi=200)
plt.close()

print(f" 결과 저장 완료: {out_block_path}")
print(f" 차트 저장 완료: {chart_path}")
