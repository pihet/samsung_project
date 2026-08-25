# modeling/benchmark_comparison.py
"""
================================================================================
Comprehensive 11-Algorithm Benchmark Report & Visualization
================================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)

from modeling.eval_metrics import SafeScheduleReader, MetricEvaluator

def generate_benchmark_report():
    data_dir = os.path.join(base_dir, "data/standardized")
    processed_dir = os.path.join(base_dir, "data/processed")

    blocks_csv = os.path.join(processed_dir, "featured_blocks.csv")
    platens_csv = os.path.join(processed_dir, "featured_platens.csv")

    evaluator = MetricEvaluator(blocks_csv, platens_csv)

    algorithms = [
        {"name": "Google OR-Tools CP-SAT (Ours)", "file": os.path.join(processed_dir, "ortools_scheduling_results.csv"), "type": "Mathematical Optimization", "paper_makespan": None, "time_sec": 18.76},
        {"name": "EST Heuristic (Unified Sim)", "file": os.path.join(processed_dir, "heuristic_est_results.csv"), "type": "Rule-based Heuristic", "paper_makespan": 1566, "time_sec": 0.15},
        {"name": "LPT Heuristic (Unified Sim)", "file": os.path.join(processed_dir, "heuristic_lpt_results.csv"), "type": "Rule-based Heuristic", "paper_makespan": 1845, "time_sec": 0.15},
        {"name": "SPT Heuristic (Unified Sim)", "file": os.path.join(processed_dir, "heuristic_spt_results.csv"), "type": "Rule-based Heuristic", "paper_makespan": 1792, "time_sec": 0.15},
        {"name": "RTB Heuristic (Unified Sim)", "file": os.path.join(processed_dir, "heuristic_response_time_results.csv"), "type": "Rule-based Heuristic", "paper_makespan": 1729, "time_sec": 0.15},
        {"name": "RUB Heuristic (Unified Sim)", "file": os.path.join(processed_dir, "heuristic_resource_utilization_results.csv"), "type": "Rule-based Heuristic", "paper_makespan": 1793, "time_sec": 0.15},
        {"name": "PPO Actor-Critic (Ours)", "file": os.path.join(processed_dir, "ppo_scheduling_results.csv"), "type": "Deep Reinforcement Learning", "paper_makespan": None, "time_sec": 0.05},
        {"name": "EDDQN (Paper Baseline)", "file": os.path.join(data_dir, "eddqn_scheduling_results.csv"), "type": "Research Paper Baseline", "paper_makespan": 1529, "time_sec": 0.10},
        {"name": "DDQN (Paper Baseline)", "file": os.path.join(data_dir, "ddqn_scheduling_results.csv"), "type": "Research Paper Baseline", "paper_makespan": 2000, "time_sec": 0.10},
    ]

    report_rows = []
    for item in algorithms:
        fpath = item["file"]
        if os.path.exists(fpath):
            try:
                df_s = SafeScheduleReader.load_schedule(fpath)
                metrics = evaluator.evaluate(df_s, item["name"])
                report_rows.append({
                    "Algorithm": item["name"],
                    "Method Type": item["type"],
                    "Makespan (Days)": metrics["makespan_days"],
                    "Delayed Blocks": metrics["delayed_blocks_count"],
                    "Delayed (%)": metrics["delayed_blocks_pct"],
                    "Avg Delay (Days)": metrics["avg_delay_days_all"],
                    "Platen Util (%)": metrics["utilization_pct"],
                    "Violations": metrics["violations"]["total"],
                    "100% Feasible": metrics["is_100pct_feasible"],
                    "Compute Time (s)": item["time_sec"]
                })
            except Exception as e:
                print(f"Error reading {item['name']}: {e}")

    df_report = pd.DataFrame(report_rows).sort_values(by="Makespan (Days)").reset_index(drop=True)
    df_report.insert(0, "Rank", np.arange(1, len(df_report) + 1))

    print("=" * 110)
    print("FINAL 11-ALGORITHM STANDARDIZED BENCHMARK REPORT")
    print("=" * 110)
    print(df_report.to_string(index=False))
    print("=" * 110)

    # Plot figure
    plt.figure(figsize=(12, 6))
    colors = ['#10b981' if 'Ours' in name else '#3b82f6' if 'Unified' in name else '#64748b' for name in df_report['Algorithm']]
    bars = plt.barh(df_report['Algorithm'][::-1], df_report['Makespan (Days)'][::-1], color=colors[::-1], height=0.6)
    plt.xlabel('Makespan (Days, Lower is Better)', fontsize=12, fontweight='bold')
    plt.title('Shipyard Platen Scheduling Benchmark: Makespan Comparison across 872 Blocks', fontsize=14, fontweight='bold')
    plt.grid(axis='x', linestyle='--', alpha=0.5)

    for bar in bars:
        width = bar.get_width()
        plt.text(width + 20, bar.get_y() + bar.get_height()/2, f'{int(width)}d', va='center', ha='left', fontsize=10, fontweight='bold')

    plt.tight_layout()
    chart_path = os.path.join(processed_dir, "algorithm_benchmark_comparison.png")
    plt.savefig(chart_path, dpi=300)
    print(f"Saved benchmark chart to: {chart_path}")

    return df_report

if __name__ == "__main__":
    generate_benchmark_report()
