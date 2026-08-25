# modeling/benchmark_comparison.py
"""
================================================================================
 [Benchmark] 알고리즘별 종합 성능 비교 및 평가 리포트 생성
================================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
processed_dir = os.path.join(base_dir, "data/processed")

benchmark_data = [
    {"Algorithm": "Google OR-Tools CP-SAT (Ours)", "Makespan_Days": 1216, "Delayed_Blocks": 252, "Compute_Time_Sec": 18.09, "Type": "Mathematical Optimization"},
    {"Algorithm": "EST Heuristic (Ours)", "Makespan_Days": 1249, "Delayed_Blocks": 259, "Compute_Time_Sec": 0.12, "Type": "Rule-based Heuristic"},
    {"Algorithm": "PPO Actor-Critic (Ours)", "Makespan_Days": 1398, "Delayed_Blocks": 586, "Compute_Time_Sec": 0.05, "Type": "Deep Reinforcement Learning"},
    {"Algorithm": "EDDQN (Paper Benchmark)", "Makespan_Days": 1529, "Delayed_Blocks": 310, "Compute_Time_Sec": 0.10, "Type": "Research Paper Baseline"},
    {"Algorithm": "EST (Paper Benchmark)", "Makespan_Days": 1566, "Delayed_Blocks": 345, "Compute_Time_Sec": 0.15, "Type": "Research Paper Baseline"},
    {"Algorithm": "RTB Heuristic (Paper)", "Makespan_Days": 1729, "Delayed_Blocks": 420, "Compute_Time_Sec": 0.15, "Type": "Research Paper Baseline"},
    {"Algorithm": "SPT Heuristic (Paper)", "Makespan_Days": 1792, "Delayed_Blocks": 435, "Compute_Time_Sec": 0.15, "Type": "Research Paper Baseline"},
    {"Algorithm": "RUB Heuristic (Paper)", "Makespan_Days": 1793, "Delayed_Blocks": 440, "Compute_Time_Sec": 0.15, "Type": "Research Paper Baseline"},
    {"Algorithm": "LPT Heuristic (Paper)", "Makespan_Days": 1845, "Delayed_Blocks": 460, "Compute_Time_Sec": 0.15, "Type": "Research Paper Baseline"},
    {"Algorithm": "DDQN (Paper Benchmark)", "Makespan_Days": 2000, "Delayed_Blocks": 510, "Compute_Time_Sec": 0.10, "Type": "Research Paper Baseline"},
    {"Algorithm": "Random Policy (Baseline)", "Makespan_Days": 7003, "Delayed_Blocks": 513, "Compute_Time_Sec": 0.05, "Type": "Random Baseline"}
]

df_bm = pd.DataFrame(benchmark_data)
df_bm_sorted = df_bm.sort_values(by="Makespan_Days", ascending=True).reset_index(drop=True)

print("=" * 85)
print(" [종합 알고리즘 벤치마크 비교 성적표 (Makespan 오름차순)]")
print("=" * 85)
print(df_bm_sorted[['Algorithm', 'Type', 'Makespan_Days', 'Delayed_Blocks', 'Compute_Time_Sec']].to_string(index=False))
print("=" * 85)

# 시각화 비교 바차트 생성
plt.figure(figsize=(12, 6))
colors = ['#1f77b4' if 'Ours' in a else '#7f7f7f' for a in df_bm_sorted['Algorithm']]
colors[0] = '#2ca02c' # 1위 녹색

bars = plt.barh(df_bm_sorted['Algorithm'][::-1], df_bm_sorted['Makespan_Days'][::-1], color=colors[::-1], height=0.65)
plt.xlabel('Total Makespan (Days - Lower is Better)', fontsize=12, fontweight='bold')
plt.title('Shipyard Platen Scheduling Algorithm Benchmark Comparison (872 Blocks x 66 Platens)', fontsize=13, fontweight='bold')
plt.grid(axis='x', linestyle='--', alpha=0.5)

for bar in bars:
    width = bar.get_width()
    plt.text(width + 80, bar.get_y() + bar.get_height()/2, f'{int(width):,} Days',
             va='center', ha='left', fontsize=10, fontweight='bold', color='black')

plt.xlim(0, 8000)
plt.tight_layout()

chart_out = os.path.join(processed_dir, "algorithm_benchmark_comparison.png")
plt.savefig(chart_out, dpi=200)
plt.close()

print(f" 최종 비교 차트 저장 완료: {chart_out}")
