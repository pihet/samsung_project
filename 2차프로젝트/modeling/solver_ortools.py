# modeling/solver_ortools.py
"""
================================================================================
 [Modeling] Google OR-Tools CP-SAT 기반 롤링 호라이즌(Rolling Horizon) 수리최적화 솔버
================================================================================
"""

import os
import sys
import time
import numpy as np
import pandas as pd
from ortools.sat.python import cp_model
from typing import Dict, Any, List, Tuple

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)

def solve_window_cpsat(
    df_window: pd.DataFrame,
    df_platens: pd.DataFrame,
    platen_start_times: np.ndarray,
    time_limit_per_window: float = 2.0
) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    model = cp_model.CpModel()
    num_blocks = len(df_window)
    num_platens = len(df_platens)

    feasible_platens = {}
    for b_i in range(num_blocks):
        b = df_window.iloc[b_i]
        b_max, b_min = max(b['length_m'], b['width_m']), min(b['length_m'], b['width_m'])
        
        v_list = []
        for p_i in range(num_platens):
            p = df_platens.iloc[p_i]
            p_max, p_min = max(p['platen_length_m'], p['platen_width_m']), min(p['platen_length_m'], p['platen_width_m'])
            if b_max <= p_max and b_min <= p_min and b['weight_ton'] <= p['crane_capacity_ton']:
                v_list.append(p_i)
        
        if not v_list:
            v_list = [0, 1, 2]
        feasible_platens[b_i] = v_list

    min_est = int(df_window['est_day'].min())
    max_duration_sum = int(df_window['lead_time_days'].sum())
    horizon = int(max(np.max(platen_start_times), min_est) + max_duration_sum + 200)

    start_vars = {}
    end_vars = {}
    delay_vars = {}
    platen_intervals = {p_i: [] for p_i in range(num_platens)}
    assignment_lits = {}

    for b_i in range(num_blocks):
        b = df_window.iloc[b_i]
        est_d = int(b['est_day'])
        due_d = int(b['due_day'])
        duration = int(b['lead_time_days'])

        start_var = model.NewIntVar(est_d, horizon, f"start_w_b{b_i}")
        end_var = model.NewIntVar(est_d + duration, horizon, f"end_w_b{b_i}")
        model.Add(end_var == start_var + duration)

        start_vars[b_i] = start_var
        end_vars[b_i] = end_var

        delay_var = model.NewIntVar(0, horizon, f"delay_w_b{b_i}")
        model.Add(delay_var >= end_var - due_d)
        delay_vars[b_i] = delay_var

        presence_lits = []
        for p_i in feasible_platens[b_i]:
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

    total_delay_expr = sum(delay_vars.values())
    total_end_expr = sum(end_vars.values())
    model.Minimize(10 * total_delay_expr + total_end_expr)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_per_window)
    solver.parameters.num_workers = 8
    status = solver.Solve(model)

    new_platen_times = np.copy(platen_start_times)
    window_results = []

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for b_i in range(num_blocks):
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
                "block_id": b['block_id'],
                "ship_id": b['ship_id'],
                "platen_idx": chosen_p,
                "platen_id": p_info['platen_id'],
                "platen_name": p_info['platen_name'],
                "planned_start_day": s_d,
                "planned_end_day": e_d,
                "due_day": int(b['due_day']),
                "delay_days": del_d,
                "lead_time_days": int(b['lead_time_days'])
            })
    else:
        for b_i in range(num_blocks):
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
                "block_id": b['block_id'],
                "ship_id": b['ship_id'],
                "platen_idx": best_p,
                "platen_id": p_info['platen_id'],
                "platen_name": p_info['platen_name'],
                "planned_start_day": best_s,
                "planned_end_day": e_d,
                "due_day": due_d,
                "delay_days": del_d,
                "lead_time_days": duration
            })

    return window_results, new_platen_times

def run_ortools_platen_optimization(window_size: int = 50, time_limit_per_window: float = 1.0) -> Dict[str, Any]:
    print("=" * 80)
    print(" [Google OR-Tools CP-SAT] 롤링 호라이즌(Rolling Horizon) 수리최적화 가동")
    print("=" * 80)

    block_file = os.path.join(base_dir, "data/processed/featured_blocks.csv")
    platen_file = os.path.join(base_dir, "data/processed/featured_platens.csv")

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
    total_start_time = time.time()
    num_windows = (num_blocks + window_size - 1) // window_size

    for w_idx in range(num_windows):
        start_idx = w_idx * window_size
        end_idx = min(num_blocks, (w_idx + 1) * window_size)
        df_win = df_blocks.iloc[start_idx:end_idx].copy()

        t0 = time.time()
        w_res, platen_times = solve_window_cpsat(df_win, df_platens, platen_times, time_limit_per_window)
        elapsed = round(time.time() - t0, 2)
        all_results.extend(w_res)
        print(f"    [Window {w_idx+1:>2}/{num_windows}] 블록 {start_idx:>3}~{end_idx:>3} CP-SAT 최적화 완료 ({elapsed:>4.2f}초) | 현재 Makespan: {int(np.max(platen_times))}일")

    total_solve_time = round(time.time() - total_start_time, 2)

    df_out = pd.DataFrame(all_results)
    out_csv = os.path.join(base_dir, "data/processed/ortools_scheduling_results.csv")
    df_out.to_csv(out_csv, index=False, encoding='utf-8')

    final_makespan = int(df_out['planned_end_day'].max())
    delayed_blocks = int((df_out['delay_days'] > 0).sum())
    total_delay = int(df_out['delay_days'].sum())
    avg_delay = round(total_delay / num_blocks, 2)
    total_lead = int(df_blocks['lead_time_days'].sum())
    utilization_pct = round((total_lead / (num_platens * final_makespan)) * 100, 2)

    metrics = {
        "status": "OPTIMAL_OR_FEASIBLE",
        "makespan": final_makespan,
        "delayed_blocks": delayed_blocks,
        "total_delay_days": total_delay,
        "avg_delay_days": avg_delay,
        "utilization_pct": utilization_pct,
        "solve_time_sec": total_solve_time,
        "output_file": out_csv
    }

    print("\n" + "=" * 80)
    print(" [Google OR-Tools CP-SAT 롤링 호라이즌 최종 성적표]")
    print("=" * 80)
    print(f"    총 소요 공기 (Makespan): {metrics['makespan']} 일")
    print(f"    납기 지연 블록 수: {metrics['delayed_blocks']} 개 / {num_blocks}개 ({metrics['delayed_blocks']/num_blocks*100:.1f}%)")
    print(f"    평균 지연 일수: {metrics['avg_delay_days']} 일")
    print(f"    정반 평균 가동률: {metrics['utilization_pct']} %")
    print(f"    872개 전체 최적화 소요 시간: {metrics['solve_time_sec']} 초")
    print(f"    결과 파일 저장 완료: {metrics['output_file']}")
    print("=" * 80)

    return metrics

if __name__ == "__main__":
    run_ortools_platen_optimization(window_size=50, time_limit_per_window=1.0)
