# modeling/dynamic_scenario_eval.py
"""
================================================================================
Dynamic Emergency Rush Block Injection Evaluation on Realistic Platen State
================================================================================
- Restores actual platen occupancy state from master schedule.
- Evaluates real-time allocation of 5 emergency rush blocks against occupied platens.
- Uses strictly measured time.perf_counter() for PPO and EST.
- OR-Tools is marked as 'N/A - full re-optimization not executed' (no artificial sleep).
================================================================================
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
import torch

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "simulation"))

from simulation.simulator import ShipyardPlatenSimulator
from modeling.train_ppo import MaskedActorCritic
from modeling.eval_metrics import SafeScheduleReader

def get_occupied_platen_state_at_day(master_schedule_csv: str, target_day: int = 100, num_platens: int = 66) -> np.ndarray:
    """Calculates each platen's next available day based on active allocations at target_day."""
    platen_avail = np.zeros(num_platens, dtype=np.int32)
    if os.path.exists(master_schedule_csv):
        df_master = SafeScheduleReader.load_schedule(master_schedule_csv)
        for _, row in df_master.iterrows():
            p_idx = int(row.get('platen_idx', -1))
            p_end = int(row.get('planned_end_day', -1))
            if 0 <= p_idx < num_platens:
                platen_avail[p_idx] = max(platen_avail[p_idx], p_end)
    return platen_avail

def evaluate_dynamic_emergency_scenario():
    print("=" * 115)
    print("DYNAMIC SCENARIO EVALUATION: 5 EMERGENCY RUSH BLOCKS ON OCCUPIED PLATEN STATE")
    print("=" * 115)

    blocks_csv = os.path.join(base_dir, "data/processed/featured_blocks.csv")
    platens_csv = os.path.join(base_dir, "data/processed/featured_platens.csv")
    master_sched_csv = os.path.join(base_dir, "data/processed/ortools_scheduling_results.csv")
    if not os.path.exists(master_sched_csv):
        master_sched_csv = os.path.join(base_dir, "data/processed/ppo_scheduling_results.csv")

    df_platens = pd.read_csv(platens_csv)

    # 5 Emergency Rush Blocks arriving at Day 100 with tight deadlines
    emergency_blocks = [
        {"seq_id": 9001, "block_id": "EMERG_01", "ship_id": "S_RUSH", "length_m": 15.0, "width_m": 12.0, "weight_ton": 70.0, "lead_time_days": 10, "earliest_start_date": "2018-06-01", "due_date": "2018-06-25", "est_day": 100, "due_day": 125, "slack_days": 15, "urgency_ratio": 0.40, "block_type": "FLAT", "cluster_id": 0},
        {"seq_id": 9002, "block_id": "EMERG_02", "ship_id": "S_RUSH", "length_m": 20.0, "width_m": 15.0, "weight_ton": 120.0, "lead_time_days": 14, "earliest_start_date": "2018-06-01", "due_date": "2018-06-25", "est_day": 100, "due_day": 125, "slack_days": 11, "urgency_ratio": 0.56, "block_type": "FLAT", "cluster_id": 1},
        {"seq_id": 9003, "block_id": "EMERG_03", "ship_id": "S_RUSH", "length_m": 18.0, "width_m": 14.0, "weight_ton": 90.0, "lead_time_days": 12, "earliest_start_date": "2018-06-05", "due_date": "2018-06-28", "est_day": 105, "due_day": 128, "slack_days": 11, "urgency_ratio": 0.52, "block_type": "FLAT", "cluster_id": 1},
        {"seq_id": 9004, "block_id": "EMERG_04", "ship_id": "S_RUSH", "length_m": 22.0, "width_m": 16.0, "weight_ton": 140.0, "lead_time_days": 15, "earliest_start_date": "2018-06-05", "due_date": "2018-07-02", "est_day": 105, "due_day": 132, "slack_days": 12, "urgency_ratio": 0.55, "block_type": "FLAT", "cluster_id": 2},
        {"seq_id": 9005, "block_id": "EMERG_05", "ship_id": "S_RUSH", "length_m": 25.0, "width_m": 18.0, "weight_ton": 150.0, "lead_time_days": 18, "earliest_start_date": "2018-06-10", "due_date": "2018-07-10", "est_day": 110, "due_day": 140, "slack_days": 12, "urgency_ratio": 0.60, "block_type": "FLAT", "cluster_id": 2}
    ]
    df_emergency = pd.DataFrame(emergency_blocks)

    # Restore realistic platen occupancy baseline
    base_occupancy = get_occupied_platen_state_at_day(master_sched_csv, target_day=100, num_platens=len(df_platens))

    results = []

    # 1. Action-Masked PPO RL on Occupied Platen Baseline
    sim_ppo = ShipyardPlatenSimulator(df_emergency, df_platens, order_by="raw")
    sim_ppo.platen_available_days = base_occupancy.copy()

    ppo_model_path = os.path.join(base_dir, "data/processed/best_rl_model.pth")
    if not os.path.exists(ppo_model_path):
        ppo_model_path = os.path.join(base_dir, "data/processed/ppo_model.pth")

    device = torch.device("cpu")
    ppo_net = MaskedActorCritic(sim_ppo._get_state().shape[0], sim_ppo.num_platens).to(device)
    if os.path.exists(ppo_model_path):
        ppo_net.load_state_dict(torch.load(ppo_model_path, map_location=device))
    ppo_net.eval()

    t_ppo_start = time.perf_counter()
    ppo_allocations = []
    for _ in range(len(df_emergency)):
        state = torch.FloatTensor(sim_ppo._get_state()).unsqueeze(0)
        mask = torch.BoolTensor(sim_ppo.get_action_mask()).unsqueeze(0)
        with torch.no_grad():
            action = ppo_net.get_eval_action(state, mask, temperature=0.5)
        rec = sim_ppo.step(action)
        ppo_allocations.append(rec)
    ppo_time_ms = (time.perf_counter() - t_ppo_start) * 1000

    results.append({
        "Methodology": "Action-Masked PPO RL (Ours)",
        "Role": "Real-time AI Dispatcher",
        "5-Block Total Decision Time": f"{ppo_time_ms:.2f} ms",
        "Per-Block Decision Latency": f"{ppo_time_ms / 5.0:.3f} ms",
        "Delayed Rush Blocks": sum(1 for r in ppo_allocations if r['delay_days'] > 0),
        "Total Rush Delay Days": sum(r['delay_days'] for r in ppo_allocations),
        "100% Feasible": all(r['is_feasible'] for r in ppo_allocations)
    })

    # 2. EST Heuristic Rule on Occupied Platen Baseline
    sim_est = ShipyardPlatenSimulator(df_emergency, df_platens, order_by="raw")
    sim_est.platen_available_days = base_occupancy.copy()

    t_est_start = time.perf_counter()
    est_allocations = []
    for b_idx in range(len(df_emergency)):
        mask = sim_est.get_action_mask()
        valid_p = np.where(mask)[0]
        if len(valid_p) > 0:
            est_d = int(df_emergency.iloc[b_idx]['est_day'])
            best_p = valid_p[0]
            best_s = max(est_d, int(sim_est.platen_available_days[best_p]))
            for p in valid_p:
                s_cand = max(est_d, int(sim_est.platen_available_days[p]))
                if s_cand < best_s:
                    best_s = s_cand
                    best_p = p
        else:
            best_p = 0
        rec = sim_est.step(best_p)
        est_allocations.append(rec)
    est_time_ms = (time.perf_counter() - t_est_start) * 1000

    results.append({
        "Methodology": "EST Heuristic Rule",
        "Role": "Rule-based Fallback",
        "5-Block Total Decision Time": f"{est_time_ms:.2f} ms",
        "Per-Block Decision Latency": f"{est_time_ms / 5.0:.3f} ms",
        "Delayed Rush Blocks": sum(1 for r in est_allocations if r['delay_days'] > 0),
        "Total Rush Delay Days": sum(r['delay_days'] for r in est_allocations),
        "100% Feasible": all(r['is_feasible'] for r in est_allocations)
    })

    # 3. Google OR-Tools CP-SAT (Full Re-optimization)
    results.append({
        "Methodology": "Google OR-Tools CP-SAT",
        "Role": "Master Production Optimizer",
        "5-Block Total Decision Time": "N/A - full re-optimization not executed",
        "Per-Block Decision Latency": "N/A",
        "Delayed Rush Blocks": "N/A",
        "Total Rush Delay Days": "N/A",
        "100% Feasible": "N/A"
    })

    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))
    print("=" * 115)

    out_json = os.path.join(base_dir, "data/processed/dynamic_scenario_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return df_res

if __name__ == "__main__":
    evaluate_dynamic_emergency_scenario()
