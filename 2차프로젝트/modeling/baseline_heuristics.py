# modeling/baseline_heuristics.py
"""
================================================================================
Standard Rule-Based Baseline Heuristics (EST, SPT, LPT, RUB, RTB)
================================================================================
"""

import os
import sys
from typing import Dict, Any, List
import numpy as np
import pandas as pd

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "simulation"))

from simulation.simulator import ShipyardPlatenSimulator
from modeling.eval_metrics import MetricEvaluator

def run_heuristic(rule_name: str, blocks_csv: str, platens_csv: str) -> Dict[str, Any]:
    df_b = pd.read_csv(blocks_csv)
    df_p = pd.read_csv(platens_csv)

    # 1. Calibrate calendar
    if 'est_day' not in df_b.columns:
        df_b['est_dt'] = pd.to_datetime(df_b['earliest_start_date'])
        df_b['due_dt'] = pd.to_datetime(df_b['due_date'])
        base_dt = df_b['est_dt'].min()
        df_b['est_day'] = (df_b['est_dt'] - base_dt).dt.days
        df_b['due_day'] = (df_b['due_dt'] - base_dt).dt.days

    if 'lead_time_days' not in df_b.columns and 'processing_time_days' in df_b.columns:
        df_b['lead_time_days'] = df_b['processing_time_days']

    if 'urgency_ratio' not in df_b.columns:
        df_b['urgency_ratio'] = df_b['lead_time_days'] / np.maximum(1, df_b['due_day'] - df_b['est_day'])

    # 2. Sort blocks based on rule
    if rule_name == "EST":
        df_sorted = df_b.sort_values(by=['est_day', 'urgency_ratio'], ascending=[True, False]).reset_index(drop=True)
    elif rule_name == "SPT":
        df_sorted = df_b.sort_values(by=['lead_time_days', 'est_day'], ascending=[True, True]).reset_index(drop=True)
    elif rule_name == "LPT":
        df_sorted = df_b.sort_values(by=['lead_time_days', 'est_day'], ascending=[False, True]).reset_index(drop=True)
    elif rule_name == "RTB":
        df_sorted = df_b.sort_values(by=['urgency_ratio', 'est_day'], ascending=[False, True]).reset_index(drop=True)
    elif rule_name == "RUB":
        df_sorted = df_b.sort_values(by=['block_area_m2', 'est_day'], ascending=[False, True]).reset_index(drop=True)
    else:
        df_sorted = df_b.copy()

    # 3. Simulator with sorted blocks
    sim = ShipyardPlatenSimulator(df_sorted, df_p, order_by="raw")

    for b_idx in range(sim.num_blocks):
        b = sim.df_blocks.iloc[b_idx]
        mask = sim.get_action_mask(b_idx)
        valid_platens = np.where(mask)[0]

        est_d = int(b['est_day'])
        b_area = float(b['block_area_m2'])

        best_p = valid_platens[0]

        if rule_name in ["EST", "SPT", "LPT", "RTB"]:
            best_start = max(est_d, int(sim.platen_available_days[best_p]))
            for p in valid_platens:
                s_cand = max(est_d, int(sim.platen_available_days[p]))
                if s_cand < best_start:
                    best_start = s_cand
                    best_p = p
        elif rule_name == "RUB":
            best_start = max(est_d, int(sim.platen_available_days[best_p]))
            best_waste = float(sim.df_platens.iloc[best_p]['platen_area_m2']) - b_area

            for p in valid_platens:
                s_cand = max(est_d, int(sim.platen_available_days[p]))
                p_area = float(sim.df_platens.iloc[p]['platen_area_m2'])
                waste = p_area - b_area
                if s_cand <= best_start + 2 and waste < best_waste:
                    best_start = s_cand
                    best_waste = waste
                    best_p = p

        sim.step(best_p)

    metrics = sim.get_summary_metrics()
    df_out = pd.DataFrame(sim.allocation_history)
    out_file = os.path.join(base_dir, f"data/processed/heuristic_{rule_name.lower()}_results.csv")
    df_out.to_csv(out_file, index=False)

    return {
        "rule": rule_name,
        "makespan": metrics["makespan"],
        "delayed_blocks": metrics["delayed_blocks"],
        "avg_delay": metrics["avg_delay_days"],
        "utilization_pct": metrics["utilization_pct"],
        "file": out_file
    }

def evaluate_all_heuristics():
    processed_dir = os.path.join(base_dir, "data/processed")
    blocks_csv = os.path.join(processed_dir, "featured_blocks.csv")
    platens_csv = os.path.join(processed_dir, "featured_platens.csv")

    evaluator = MetricEvaluator(blocks_csv, platens_csv)
    print("=" * 80)
    print("Executing 5 Unified Heuristic Baselines on Standard Simulator")
    print("=" * 80)

    rules = ["EST", "SPT", "LPT", "RUB", "RTB"]
    results = []
    for r in rules:
        res = run_heuristic(r, blocks_csv, platens_csv)
        df_sched = pd.read_csv(res["file"])
        eval_res = evaluator.evaluate(df_sched, f"{r} (Unified Simulator)")
        results.append({
            "Heuristic Rule": r,
            "Makespan (Days)": eval_res["makespan_days"],
            "Delayed Blocks": f"{eval_res['delayed_blocks_count']} ({eval_res['delayed_blocks_pct']}%)",
            "Avg Delay (Days)": eval_res["avg_delay_days_all"],
            "Platen Util (%)": eval_res["utilization_pct"],
            "Violations": eval_res["violations"]["total"],
            "Feasible": "YES" if eval_res["is_100pct_feasible"] else "NO"
        })

    df_report = pd.DataFrame(results)
    print(df_report.to_string(index=False))
    print("=" * 80)

if __name__ == "__main__":
    evaluate_all_heuristics()
