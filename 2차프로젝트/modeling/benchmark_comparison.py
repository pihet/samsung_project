# modeling/benchmark_comparison.py
"""
================================================================================
Comprehensive Benchmark Comparison & Performance Visualization
================================================================================
- Dynamically loads measured execution times from benchmark_metrics.json artifact.
- Distinct Categories:
  1. Unified Sequential Simulator (1-Block Non-overlapping, 100% Feasible)
  2. Historical Research Paper Baselines (Figure 10 & 3,000-episode logs reference)
================================================================================
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)

from modeling.eval_metrics import SafeScheduleReader, MetricEvaluator

METRICS_JSON = os.path.join(base_dir, "data/processed/benchmark_metrics.json")

def generate_benchmark_report():
    data_dir = os.path.join(base_dir, "data/standardized")
    processed_dir = os.path.join(base_dir, "data/processed")

    blocks_csv = os.path.join(processed_dir, "featured_blocks.csv")
    platens_csv = os.path.join(processed_dir, "featured_platens.csv")

    evaluator = MetricEvaluator(blocks_csv, platens_csv)

    # Load recorded execution times from artifact
    metrics_store = {}
    if os.path.exists(METRICS_JSON):
        try:
            with open(METRICS_JSON, "r", encoding="utf-8") as f:
                metrics_store = json.load(f)
        except Exception:
            metrics_store = {}

    # Target algorithms registry
    algorithm_registry = [
        # Unified Simulator Algorithms
        {
            "name": "Google OR-Tools CP-SAT (Ours)",
            "key": "ortools",
            "file": os.path.join(processed_dir, "ortools_scheduling_results.csv"),
            "category": "Unified Simulator",
            "type": "Mathematical Optimization",
        },
        {
            "name": "EST Heuristic (Unified Sim)",
            "key": "heuristic_est",
            "file": os.path.join(processed_dir, "heuristic_est_results.csv"),
            "category": "Unified Simulator",
            "type": "Rule-based Heuristic",
        },
        {
            "name": "LPT Heuristic (Unified Sim)",
            "key": "heuristic_lpt",
            "file": os.path.join(processed_dir, "heuristic_lpt_results.csv"),
            "category": "Unified Simulator",
            "type": "Rule-based Heuristic",
        },
        {
            "name": "SPT Heuristic (Unified Sim)",
            "key": "heuristic_spt",
            "file": os.path.join(processed_dir, "heuristic_spt_results.csv"),
            "category": "Unified Simulator",
            "type": "Rule-based Heuristic",
        },
        {
            "name": "PPO Actor-Critic (Ours)",
            "key": "ppo",
            "file": os.path.join(processed_dir, "ppo_scheduling_results.csv"),
            "category": "Unified Simulator",
            "type": "Deep Reinforcement Learning",
        },
        {
            "name": "RTB Heuristic (Unified Sim)",
            "key": "heuristic_rtb",
            "file": os.path.join(processed_dir, "heuristic_rtb_results.csv"),
            "category": "Unified Simulator",
            "type": "Rule-based Heuristic",
        },
        {
            "name": "RUB Heuristic (Unified Sim)",
            "key": "heuristic_rub",
            "file": os.path.join(processed_dir, "heuristic_rub_results.csv"),
            "category": "Unified Simulator",
            "type": "Rule-based Heuristic",
        },
        # Research Paper Historical Reference Baselines
        {
            "name": "EDDQN (Paper Baseline)",
            "key": "paper_eddqn",
            "file": os.path.join(data_dir, "eddqn_scheduling_results.csv"),
            "category": "Paper Baseline (2D)",
            "type": "Research Paper Baseline",
        },
        {
            "name": "DDQN (Paper Baseline)",
            "key": "paper_ddqn",
            "file": os.path.join(data_dir, "ddqn_scheduling_results.csv"),
            "category": "Paper Baseline (2D)",
            "type": "Research Paper Baseline",
        }
    ]

    valid_results = []
    missing_count = 0

    for item in algorithm_registry:
        fpath = item["file"]
        if not os.path.exists(fpath):
            print(f"[Warning] Result file not found for '{item['name']}': {fpath}. Skipping.")
            missing_count += 1
            continue

        try:
            df_sched = SafeScheduleReader.load_schedule(fpath)
            is_paper = (item["category"] == "Paper Baseline (2D)")
            metrics = evaluator.evaluate(df_sched, item["name"], is_paper_baseline=is_paper)
            
            # Resolve measured execution time from artifact
            key = item.get("key", "")
            if is_paper:
                compute_time_str = "Historical Ref (3000 eps)"
            elif key in metrics_store and "compute_time_sec" in metrics_store[key]:
                sec = float(metrics_store[key]["compute_time_sec"])
                compute_time_str = f"{sec:.2f}s (Measured)"
            else:
                compute_time_str = "N/A (Run to measure)"

            valid_results.append({
                "Algorithm": item["name"],
                "Category": item["category"],
                "Methodology": item["type"],
                "Makespan (Days)": metrics["makespan_days"],
                "Delayed Blocks": f"{metrics['delayed_blocks_count']} ({metrics['delayed_blocks_pct']}%)",
                "Avg Delay (Days)": metrics["avg_delay_days_all"],
                "Platen Util (%)": f"{metrics['utilization_pct']}%",
                "Violations": metrics["violations"]["total"] if not is_paper else "-",
                "100% Feasible": metrics["feasible_display"],
                "Integrity": "PASS" if metrics["integrity"]["passed"] else "FAIL",
                "Compute Time": compute_time_str
            })
        except Exception as e:
            print(f"[Error] Failed to evaluate '{item['name']}': {e}")
            missing_count += 1

    df_report = pd.DataFrame(valid_results)
    total_evaluated = len(df_report)

    # 1. Print Unified Simulator Leaderboard
    df_unified = df_report[df_report["Category"] == "Unified Simulator"].sort_values(by="Makespan (Days)").reset_index(drop=True)
    df_unified.insert(0, "Rank", np.arange(1, len(df_unified) + 1))

    print("\n" + "=" * 115)
    print(f"BENCHMARK REPORT: {len(df_unified)} ALGORITHMS ON UNIFIED SEQUENTIAL SIMULATOR (100% FEASIBLE)")
    print("=" * 115)
    print(df_unified.to_string(index=False))

    # 2. Print Research Paper Reference Baselines
    df_paper = df_report[df_report["Category"] == "Paper Baseline (2D)"].sort_values(by="Makespan (Days)").reset_index(drop=True)
    print("\n" + "=" * 115)
    print(f"HISTORICAL RESEARCH PAPER BASELINES ({len(df_paper)} ALGORITHMS - FIGURE 10 REFERENCE)")
    print("=" * 115)
    print(df_paper.to_string(index=False))
    print("=" * 115)

    # 3. Generate Publication-Grade Comparison Chart
    try:
        plt.figure(figsize=(12, 6))
        df_plot = df_report.sort_values(by="Makespan (Days)", ascending=False).reset_index(drop=True)
        
        colors = []
        for cat in df_plot["Category"]:
            if cat == "Unified Simulator":
                colors.append("#10b981") # Emerald Green
            else:
                colors.append("#64748b") # Slate Gray
                
        bars = plt.barh(df_plot["Algorithm"], df_plot["Makespan (Days)"], color=colors, height=0.6)
        plt.xlabel("Makespan (Days, Lower is Better)", fontsize=11, fontweight="bold")
        plt.title(f"Shipyard Platen Scheduling Benchmark ({total_evaluated} Evaluated Algorithms)", fontsize=13, fontweight="bold")
        plt.grid(axis="x", linestyle="--", alpha=0.5)

        for bar in bars:
            width = bar.get_width()
            plt.text(width + 25, bar.get_y() + bar.get_height()/2, f"{int(width)}d", va="center", ha="left", fontsize=10, fontweight="bold")

        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor="#10b981", label="Unified Simulator (Ours / Heuristics)"),
            Patch(facecolor="#64748b", label="Paper Baseline (Figure 10 2D Ref)")
        ]
        plt.legend(handles=legend_elements, loc="lower right", frameon=True)

        plt.tight_layout()
        chart_path = os.path.join(processed_dir, "algorithm_benchmark_comparison.png")
        plt.savefig(chart_path, dpi=300)
        print(f"\nSaved updated benchmark chart to: {chart_path}")
    except Exception as e:
        print(f"\n[Notice] Chart plotting skipped: {e}")

    return df_report

if __name__ == "__main__":
    generate_benchmark_report()
