# modeling/model_selection_matrix.py
"""
================================================================================
Artifact-Driven Multi-Criteria Decision Analysis (MCDA) & Model Selection Matrix
================================================================================
- Dynamically loads measured metrics from benchmark_metrics.json & schedule CSVs.
- Evaluates Candidates Across 6 Core Dimensions:
  1. Schedule Compactness (Makespan Days)
  2. Punctuality (Delayed Blocks Count & Avg Delay Days)
  3. Platen Efficiency (Platen Utilization %)
  4. Master Batch Generation Time (872-Block Full Schedule Seconds)
  5. Real-time Dispatch Latency (Per-Block Average Decision Milliseconds: T / 872)
  6. Training & Operational Overhead (Training Seconds / Zero-shot)
- Explicit Score Formula (1~10):
  Score = 10 * [0.35 * S_makespan + 0.25 * S_delay + 0.15 * S_util + 0.15 * S_speed + 0.10 * S_overhead]
================================================================================
"""

import os
import sys
import json
import numpy as np
import pandas as pd

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)

from modeling.eval_metrics import SafeScheduleReader, MetricEvaluator

def generate_mcda_matrix():
    print("=" * 115)
    print("MULTI-CRITERIA DECISION ANALYSIS (MCDA) - DYNAMIC ARTIFACT-DRIVEN MATRIX")
    print("=" * 115)

    processed_dir = os.path.join(base_dir, "data/processed")
    blocks_csv = os.path.join(processed_dir, "featured_blocks.csv")
    platens_csv = os.path.join(processed_dir, "featured_platens.csv")
    evaluator = MetricEvaluator(blocks_csv, platens_csv)

    # 1. Load recorded execution time metrics from JSON artifact
    metrics_json_path = os.path.join(processed_dir, "benchmark_metrics.json")
    metrics_store = {}
    if os.path.exists(metrics_json_path):
        try:
            with open(metrics_json_path, "r", encoding="utf-8") as f:
                metrics_store = json.load(f)
        except Exception:
            metrics_store = {}

    # Target candidate models with their generated schedule CSVs
    candidates = [
        {
            "name": "Google OR-Tools CP-SAT",
            "key": "ortools",
            "csv_file": os.path.join(processed_dir, "ortools_scheduling_results.csv"),
            "role": "Master Production Planning (Batch/Periodic)",
            "overhead_desc": "None (Exact Solver, 0s)",
            "overhead_sec": 0.0
        },
        {
            "name": "EST Heuristic Rule",
            "key": "heuristic_est",
            "csv_file": os.path.join(processed_dir, "heuristic_est_results.csv"),
            "role": "Ultra-fast Robust Fallback / Baseline",
            "overhead_desc": "None (Rule-based, 0s)",
            "overhead_sec": 0.0
        },
        {
            "name": "Action-Masked PPO RL (Ours)",
            "key": "ppo",
            "csv_file": os.path.join(processed_dir, "ppo_scheduling_results.csv"),
            "role": "Real-time AI Dispatcher & Dynamic Adjustment",
            "overhead_desc": "Training: ~26s (30 eps)",
            "overhead_sec": 26.0
        },
        {
            "name": "Action-Masked DQN (Ours)",
            "key": "dqn",
            "csv_file": os.path.join(processed_dir, "dqn_scheduling_results.csv"),
            "role": "Discrete Action Baseline Comparison",
            "overhead_desc": "Training: ~610s (30 eps)",
            "overhead_sec": 610.0
        }
    ]

    mcda_rows = []
    raw_eval_data = []

    for cand in candidates:
        fpath = cand["csv_file"]
        if not os.path.exists(fpath):
            continue

        df_sched = SafeScheduleReader.load_schedule(fpath)
        metrics = evaluator.evaluate(df_sched, cand["name"])

        # Fetch measured times from benchmark_metrics.json artifact
        key = cand["key"]
        if key in metrics_store and "compute_time_sec" in metrics_store[key]:
            batch_time_sec = float(metrics_store[key]["compute_time_sec"])
            batch_time_str = f"{batch_time_sec:.2f} s (Measured)"
            per_block_ms = (batch_time_sec / 872.0) * 1000.0
            per_block_str = f"{per_block_ms:.3f} ms/blk"
        else:
            batch_time_sec = 1.0
            batch_time_str = "N/A"
            per_block_ms = 1.0
            per_block_str = "N/A"

        train_time_sec = float(metrics_store.get(key, {}).get("training_time_sec", cand["overhead_sec"]))

        raw_eval_data.append({
            "name": cand["name"],
            "role": cand["role"],
            "makespan": metrics["makespan_days"],
            "delayed_blocks": metrics["delayed_blocks_count"],
            "delayed_pct": metrics["delayed_blocks_pct"],
            "avg_delay": metrics["avg_delay_days_all"],
            "utilization": metrics["utilization_pct"],
            "batch_time_sec": batch_time_sec,
            "batch_time_str": batch_time_str,
            "per_block_ms": per_block_ms,
            "per_block_str": per_block_str,
            "train_time_sec": train_time_sec,
            "overhead_desc": cand["overhead_desc"],
            "integrity": "PASS" if metrics["integrity"]["passed"] else "FAIL",
            "feasible": "YES" if metrics["is_100pct_feasible"] else "NO"
        })

    # Mathematical MCDA Scoring (TOPSIS / Weighted Sum Model)
    # Best reference targets
    min_makespan = min(r["makespan"] for r in raw_eval_data)
    min_delay = min(r["delayed_blocks"] for r in raw_eval_data)
    max_util = max(r["utilization"] for r in raw_eval_data)
    min_block_time = min(r["per_block_ms"] for r in raw_eval_data)

    weights = {
        "makespan": 0.35,
        "delay": 0.25,
        "utilization": 0.15,
        "latency": 0.15,
        "overhead": 0.10
    }

    for r in raw_eval_data:
        # Normalize (0.0 ~ 1.0)
        s_makespan = min_makespan / max(1, r["makespan"])
        s_delay = min_delay / max(1, r["delayed_blocks"])
        s_util = r["utilization"] / max(1e-3, max_util)
        s_speed = min_block_time / max(1e-3, r["per_block_ms"])
        s_overhead = 1.0 if r["train_time_sec"] == 0 else max(0.2, 1.0 - (r["train_time_sec"] / 1000.0))

        # Composite score out of 10
        total_score = 10.0 * (
            weights["makespan"] * s_makespan +
            weights["delay"] * s_delay +
            weights["utilization"] * s_util +
            weights["latency"] * s_speed +
            weights["overhead"] * s_overhead
        )

        mcda_rows.append({
            "Candidate": r["name"],
            "Makespan (Days)": r["makespan"],
            "Delayed Blocks": f"{r['delayed_blocks']} ({r['delayed_pct']}%)",
            "Avg Delay (Days)": r["avg_delay"],
            "Platen Util (%)": f"{r['utilization']}%",
            "Total 872-Blk Time": r["batch_time_str"],
            "Per-Block Latency": r["per_block_str"],
            "Training Overhead": r["overhead_desc"],
            "Best Fit Role": r["role"],
            "MCDA Score (1-10)": round(total_score, 2)
        })

    df_mcda = pd.DataFrame(mcda_rows).sort_values(by="MCDA Score (1-10)", ascending=False).reset_index(drop=True)
    print(df_mcda.to_string(index=False))
    print("=" * 115)

    # Save artifacts
    out_csv = os.path.join(processed_dir, "mcda_model_selection_matrix.csv")
    df_mcda.to_csv(out_csv, index=False)

    out_json = os.path.join(processed_dir, "mcda_model_selection_matrix.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "weights": weights,
            "formula": "Score = 10 * [0.35*(min_m/m) + 0.25*(min_d/d) + 0.15*(u/max_u) + 0.15*(min_t/t) + 0.10*overhead_score]",
            "results": mcda_rows
        }, f, indent=2)

    return df_mcda

if __name__ == "__main__":
    generate_mcda_matrix()
