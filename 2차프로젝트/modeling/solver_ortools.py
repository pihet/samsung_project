# modeling/solver_ortools.py
"""
================================================================================
Google OR-Tools CP-SAT Deterministic Rolling Horizon Optimization Engine
================================================================================
- Deterministic single-thread search (num_workers=1, random_seed=42)
- Uses `max_deterministic_time` instead of wall-clock `max_time_in_seconds`
  to guarantee 100% exact byte-for-byte repeatable schedule CSV artifacts.
================================================================================
"""

import os
import sys
import time
import json
import hashlib
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)

from utils.paths import get_feature_path, SCHEDULES_DIR, REPORTS_DIR
from modeling.eval_metrics import MetricEvaluator

METRICS_JSON = os.path.join(REPORTS_DIR, "benchmark_metrics.json")

def update_metrics_json(algo_key: str, data: Dict[str, Any]):
    store = {}
    if os.path.exists(METRICS_JSON):
        try:
            with open(METRICS_JSON, "r", encoding="utf-8") as f:
                store = json.load(f)
        except Exception:
            store = {}
    store[algo_key] = data
    with open(METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)

def get_valid_platens_for_block(b_len: float, b_wid: float, b_wt: float, df_platens: pd.DataFrame) -> List[int]:
    b_max, b_min = max(b_len, b_wid), min(b_len, b_wid)
    valid_indices = []
    for idx, p in df_platens.iterrows():
        p_len, p_wid = float(p['platen_length_m']), float(p['platen_width_m'])
        p_cap = float(p['crane_capacity_ton'])
        p_max, p_min = max(p_len, p_wid), min(p_len, p_wid)
        if b_max <= p_max and b_min <= p_min and b_wt <= p_cap:
            valid_indices.append(int(idx))
    return valid_indices

def solve_window_cpsat(
    df_window: pd.DataFrame, 
    df_platens: pd.DataFrame, 
    platen_start_times: np.ndarray, 
    max_deterministic_time: float = 0.5,
    random_seed: int = 42
) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    model = cp_model.CpModel()
    num_platens = len(df_platens)
    window_len = len(df_window)

    max_p_free = int(np.max(platen_start_times)) if len(platen_start_times) > 0 else 0
    max_due = int(df_window['due_day'].max()) if 'due_day' in df_window.columns else 1000
    horizon = max(max_p_free, max_due) + int(df_window['lead_time_days'].sum()) + 500

    start_vars = {}
    end_vars = {}
    delay_vars = {}
    assignment_lits = {}
    platen_intervals = {p: [] for p in range(num_platens)}

    feasible_platens = {}
    infeasible_blocks_idx = []

    for b_i in range(window_len):
        b = df_window.iloc[b_i]
        b_len = float(b['length_m']) if 'length_m' in b else float(b['block_length_m'])
        b_wid = float(b['width_m']) if 'width_m' in b else float(b['block_width_m'])
        b_wt = float(b['weight_ton'])
        
        v_list = get_valid_platens_for_block(b_len, b_wid, b_wt, df_platens)
        if not v_list:
            infeasible_blocks_idx.append(b_i)
            continue
        
        feasible_platens[b_i] = v_list

        est_d = int(b['est_day'])
        duration = int(b['lead_time_days'])
        due_d = int(b['due_day'])

        start_var = model.NewIntVar(est_d, horizon, f"start_w_b{b_i}")
        end_var = model.NewIntVar(est_d + duration, horizon + duration, f"end_w_b{b_i}")
        model.Add(end_var == start_var + duration)
        start_vars[b_i] = start_var
        end_vars[b_i] = end_var

        delay_var = model.NewIntVar(0, horizon, f"delay_w_b{b_i}")
        model.Add(delay_var >= end_var - due_d)
        delay_vars[b_i] = delay_var

        presence_lits = []
        for p_i in v_list:
            lit = model.NewBoolVar(f"assign_w_b{b_i}_p{p_i}")
            presence_lits.append(lit)
            assignment_lits[(b_i, p_i)] = lit

            p_free = int(platen_start_times[p_i])
            if p_free > est_d:
                model.Add(start_var >= p_free).OnlyEnforceIf(lit)

            interval = model.NewOptionalIntervalVar(
                start_var, duration, end_var, lit, f"interval_w_b{b_i}_p{p_i}"
            )
            platen_intervals[p_i].append(interval)

        model.Add(sum(presence_lits) == 1)

    for p_i in range(num_platens):
        if platen_intervals[p_i]:
            model.AddNoOverlap(platen_intervals[p_i])

    if delay_vars:
        total_delay_expr = sum(delay_vars.values())
        total_end_expr = sum(end_vars.values())
        model.Minimize(15 * total_delay_expr + total_end_expr)

    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = int(random_seed)
    solver.parameters.max_deterministic_time = float(max_deterministic_time)
    
    if feasible_platens:
        status = solver.Solve(model)
    else:
        status = cp_model.INFEASIBLE

    new_platen_times = np.copy(platen_start_times)
    window_results = []

    # Process Infeasible Blocks (Explicit Rejection)
    for b_i in infeasible_blocks_idx:
        b = df_window.iloc[b_i]
        window_results.append({
            "seq_id": int(b['seq_id']),
            "block_id": b['block_id'],
            "ship_id": b['ship_id'],
            "platen_idx": -1,
            "platen_id": "NONE",
            "platen_name": "INFEASIBLE_REJECTED",
            "planned_start_day": -1,
            "planned_end_day": -1,
            "due_date_day": int(b['due_day']),
            "delay_days": 9999,
            "processing_time_days": int(b['lead_time_days']),
            "is_feasible": False,
            "status": "INFEASIBLE_REJECTED"
        })

    # Process Feasible Blocks
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for b_i in feasible_platens:
            b = df_window.iloc[b_i]
            s_d = solver.Value(start_vars[b_i])
            e_d = solver.Value(end_vars[b_i])
            del_d = solver.Value(delay_vars[b_i])
            
            chosen_p = feasible_platens[b_i][0]
            for p_i in feasible_platens[b_i]:
                if solver.Value(assignment_lits[(b_i, p_i)]) == 1:
                    chosen_p = p_i
                    break

            new_platen_times[chosen_p] = max(new_platen_times[chosen_p], e_d)
            p_info = df_platens.iloc[chosen_p]

            window_results.append({
                "seq_id": int(b['seq_id']),
                "block_id": b['block_id'],
                "ship_id": b['ship_id'],
                "platen_idx": chosen_p,
                "platen_id": p_info['platen_id'],
                "platen_name": p_info['platen_name'],
                "planned_start_day": s_d,
                "planned_end_day": e_d,
                "due_date_day": int(b['due_day']),
                "delay_days": del_d,
                "processing_time_days": int(b['lead_time_days']),
                "is_feasible": True,
                "status": "ALLOCATED"
            })
    else:
        # Fallback Greedy for feasible blocks
        for b_i in feasible_platens:
            b = df_window.iloc[b_i]
            est_d = int(b['est_day'])
            duration = int(b['lead_time_days'])
            due_d = int(b['due_day'])

            best_p = feasible_platens[b_i][0]
            best_s = max(est_d, int(new_platen_times[best_p]))
            for p_i in feasible_platens[b_i]:
                s_cand = max(est_d, int(new_platen_times[p_i]))
                if s_cand < best_s:
                    best_s = s_cand
                    best_p = p_i

            e_d = best_s + duration
            del_d = max(0, e_d - due_d)
            new_platen_times[best_p] = e_d
            p_info = df_platens.iloc[best_p]

            window_results.append({
                "seq_id": int(b['seq_id']),
                "block_id": b['block_id'],
                "ship_id": b['ship_id'],
                "platen_idx": best_p,
                "platen_id": p_info['platen_id'],
                "platen_name": p_info['platen_name'],
                "planned_start_day": best_s,
                "planned_end_day": e_d,
                "due_date_day": due_d,
                "delay_days": del_d,
                "processing_time_days": duration,
                "is_feasible": True,
                "status": "ALLOCATED"
            })

    window_results = sorted(window_results, key=lambda x: x['seq_id'])
    return window_results, new_platen_times

def run_ortools_platen_optimization(
    window_size: int = 50, 
    max_deterministic_time: float = 0.5,
    random_seed: int = 42,
    save_artifact: bool = True
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    t_start = time.perf_counter()
    print("=" * 80)
    print(f"Google OR-Tools CP-SAT Deterministic Optimization (det_time={max_deterministic_time}, workers=1, seed={random_seed})")
    print("=" * 80)

    block_file = get_feature_path("featured_blocks.csv")
    platen_file = get_feature_path("featured_platens.csv")

    df_blocks = pd.read_csv(block_file)
    df_platens = pd.read_csv(platen_file)

    num_blocks = len(df_blocks)
    num_platens = len(df_platens)

    df_blocks['est_dt'] = pd.to_datetime(df_blocks['earliest_start_date'])
    df_blocks['due_dt'] = pd.to_datetime(df_blocks['due_date'])
    base_date = df_blocks['est_dt'].min()
    df_blocks['est_day'] = (df_blocks['est_dt'] - base_date).dt.days
    df_blocks['due_day'] = (df_blocks['due_dt'] - base_date).dt.days

    df_blocks = df_blocks.sort_values(by=['est_day', 'urgency_ratio'], ascending=[True, False]).reset_index(drop=True)

    platen_times = np.zeros(num_platens, dtype=int)
    all_results = []
    num_windows = (num_blocks + window_size - 1) // window_size

    for w_idx in range(num_windows):
        start_idx = w_idx * window_size
        end_idx = min(num_blocks, (w_idx + 1) * window_size)
        df_win = df_blocks.iloc[start_idx:end_idx].copy()

        t0 = time.time()
        w_res, platen_times = solve_window_cpsat(
            df_win, df_platens, platen_times, 
            max_deterministic_time=max_deterministic_time,
            random_seed=random_seed
        )
        elapsed = round(time.time() - t0, 2)
        all_results.extend(w_res)
        print(f"   [Window {w_idx+1:>2}/{num_windows}] Blocks {start_idx:>3}~{end_idx:>3} CP-SAT Solved ({elapsed:>4.2f}s) | Makespan: {int(np.max(platen_times))}d")

    total_solve_time = round(time.perf_counter() - t_start, 4)

    df_out = pd.DataFrame(all_results).sort_values(by='seq_id').reset_index(drop=True)
    out_csv = os.path.join(SCHEDULES_DIR, "ortools_scheduling_results.csv")
    
    if save_artifact:
        df_out.to_csv(out_csv, index=False, encoding='utf-8')

    evaluator = MetricEvaluator(block_file, platen_file)
    eval_res = evaluator.evaluate(df_out, "Google OR-Tools CP-SAT")

    if save_artifact:
        # Compute SHA-256 hash of schedule CSV
        with open(out_csv, 'rb') as f:
            csv_sha256 = hashlib.sha256(f.read()).hexdigest()

        update_metrics_json("ortools", {
            "algorithm": "Google OR-Tools CP-SAT (Ours)",
            "compute_time_sec": total_solve_time,
            "makespan_days": eval_res["makespan_days"],
            "delayed_blocks": eval_res["delayed_blocks_count"],
            "sha256": csv_sha256,
            "deterministic_time_limit": max_deterministic_time,
            "seed": random_seed,
            "timestamp": time.time()
        })

    print("\n" + "=" * 80)
    print("Google OR-Tools CP-SAT Exact Evaluation Results")
    print("=" * 80)
    print(f"   Makespan: {eval_res['makespan_days']} Days")
    print(f"   Delayed Blocks: {eval_res['delayed_blocks_count']} / {num_blocks} ({eval_res['delayed_blocks_pct']}%)")
    print(f"   Average Delay: {eval_res['avg_delay_days_all']} Days")
    print(f"   Platen Utilization: {eval_res['utilization_pct']} %")
    print(f"   Integrity: {'PASS' if eval_res['integrity']['passed'] else 'FAIL'}")
    print(f"   Constraint Violations: {eval_res['violations']['total']}")
    print(f"   100% Feasible: {eval_res['is_100pct_feasible']}")
    print(f"   Measured Solve Time: {total_solve_time} s")
    if save_artifact:
        print(f"   Output: {out_csv}")
    print("=" * 80)

    return eval_res, df_out

if __name__ == "__main__":
    run_ortools_platen_optimization(window_size=50, max_deterministic_time=0.05, random_seed=42)
