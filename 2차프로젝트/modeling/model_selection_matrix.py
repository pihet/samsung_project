# modeling/model_selection_matrix.py
"""
================================================================================
Artifact-Driven Multi-Criteria Decision Analysis (MCDA) Matrix Generator
================================================================================
"""

import os
import sys
import json
import pandas as pd
import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)

from modeling.eval_metrics import SafeScheduleReader, MetricEvaluator

def get_artifact_path(subfolder: str, filename: str) -> str:
    c1 = os.path.join(base_dir, f"data/processed/{subfolder}/{filename}")
    c2 = os.path.join(base_dir, f"data/processed/{filename}")
    return c1 if os.path.exists(c1) else c2

def generate_mcda_matrix():
    print("=" * 115)
    print("MCDA EVALUATION MATRIX (DIRECT ARTIFACT & BENCHMARK METRICS INTEGRATION)")
    print("=" * 115)

    blocks_csv = get_artifact_path("features", "featured_blocks.csv")
    platens_csv = get_artifact_path("features", "featured_platens.csv")
    evaluator = MetricEvaluator(blocks_csv, platens_csv)

    metrics_json_path = get_artifact_path("reports", "benchmark_metrics.json")
    metrics_store = {}
    if os.path.exists(metrics_json_path):
        with open(metrics_json_path, "r", encoding="utf-8") as f:
            metrics_store = json.load(f)

    candidates = [
        {
            "name": "Google OR-Tools CP-SAT",
            "key": "ortools",
            "sched_csv": get_artifact_path("schedules", "ortools_scheduling_results.csv"),
            "role": "Master Production Optimizer",
            "deployment": "Batch (Weekly/Monthly)",
            "train_overhead_score": 10.0,
            "train_overhead_str": "0s (Direct Solve)"
        },
        {
            "name": "EST Heuristic Rule",
            "key": "heuristic_est",
            "sched_csv": get_artifact_path("schedules", "heuristic_est_results.csv"),
            "role": "Operational Safety Fallback",
            "deployment": "Real-time & Zero-cost Fallback",
            "train_overhead_score": 10.0,
            "train_overhead_str": "0s (Direct Rule)"
        },
        {
            "name": "Action-Masked PPO RL (Ours)",
            "key": "ppo",
            "sched_csv": get_artifact_path("schedules", "ppo_scheduling_results.csv"),
            "role": "Real-time AI Dispatcher",
            "deployment": "Real-time Event Engine",
            "train_overhead_score": 9.0,
            "train_overhead_str": "24.6s (RL Train)"
        },
        {
            "name": "Action-Masked DQN (Ours)",
            "key": "dqn",
            "sched_csv": get_artifact_path("schedules", "dqn_scheduling_results.csv"),
            "role": "Discrete Value Baseline",
            "deployment": "Offline Reference",
            "train_overhead_score": 3.0,
            "train_overhead_str": "610.4s (DQN Train)"
        }
    ]

    records = []
    for cand in candidates:
        sched_file = cand["sched_csv"]
        if not os.path.exists(sched_file):
            continue
        df_sched = SafeScheduleReader.load_schedule(sched_file)
        eval_res = evaluator.evaluate(df_sched, cand["name"])

        key = cand["key"]
        if key in metrics_store and "compute_time_sec" in metrics_store[key]:
            compute_sec = float(metrics_store[key]["compute_time_sec"])
        else:
            compute_sec = 1.0

        latency_ms_per_block = (compute_sec / 872.0) * 1000.0

        records.append({
            "Candidate Model": cand["name"],
            "Target Deployment Role": cand["role"],
            "Makespan (Days)": eval_res["makespan_days"],
            "Delayed Blocks": eval_res["delayed_blocks_count"],
            "Delayed Rate (%)": eval_res["delayed_blocks_pct"],
            "Avg Delay (Days)": eval_res["avg_delay_days_all"],
            "Platen Util (%)": eval_res["utilization_pct"],
            "100% Feasible": eval_res["is_100pct_feasible"],
            "Total 872-Block Time (s)": compute_sec,
            "Decision Latency (ms/block)": latency_ms_per_block,
            "Training Overhead": cand["train_overhead_str"],
            "_overhead_score": cand["train_overhead_score"]
        })

    df_mcda = pd.DataFrame(records)

    min_makespan = df_mcda["Makespan (Days)"].min()
    min_delay = df_mcda["Delayed Blocks"].min()
    max_util = df_mcda["Platen Util (%)"].max()
    min_latency = df_mcda["Decision Latency (ms/block)"].min()

    scores = []
    for _, r in df_mcda.iterrows():
        s_makespan = (min_makespan / r["Makespan (Days)"]) * 10.0
        s_delay = (min_delay / r["Delayed Blocks"]) * 10.0
        s_util = (r["Platen Util (%)"] / max_util) * 10.0
        s_latency = (min_latency / r["Decision Latency (ms/block)"]) * 10.0
        s_overhead = r["_overhead_score"]

        total_score = (
            0.35 * s_makespan +
            0.25 * s_delay +
            0.15 * s_util +
            0.15 * s_latency +
            0.10 * s_overhead
        )
        scores.append(round(total_score, 2))

    df_mcda["MCDA Score (1-10)"] = scores
    df_mcda = df_mcda.sort_values(by="MCDA Score (1-10)", ascending=False).reset_index(drop=True)

    df_display = df_mcda.drop(columns=["_overhead_score"])
    print(df_display.to_string(index=False))
    print("=" * 115)

    experiments_dir = os.path.join(base_dir, "data/processed/experiments")
    os.makedirs(experiments_dir, exist_ok=True)

    out_csv = os.path.join(experiments_dir, "mcda_model_selection_matrix.csv")
    out_json = os.path.join(experiments_dir, "mcda_model_selection_matrix.json")
    df_display.to_csv(out_csv, index=False)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(df_display.to_dict(orient="records"), f, indent=2)

    print(f"Saved MCDA artifacts to:\n - {out_csv}\n - {out_json}")
    return df_display

if __name__ == "__main__":
    generate_mcda_matrix()
