# simulation/simulator.py
"""
================================================================================
 [Simulation] 스마트 조선소 정반 배치 시뮬레이터 코어 엔진 (Shipyard Platen Simulator)
================================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

class ShipyardPlatenSimulator:
    def __init__(self, data_dir: str = None, reward_version: str = "V2"):
        if data_dir is None:
            # 2차프로젝트 루트 디렉토리 기준 data/processed 탐색
            cur_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(cur_dir)
            data_dir = os.path.join(base_dir, "data/processed")
        
        self.data_dir = data_dir
        self.reward_version = reward_version

        # 1. 데이터 로드
        self.df_blocks = pd.read_csv(os.path.join(data_dir, "featured_blocks.csv"))
        self.df_platens = pd.read_csv(os.path.join(data_dir, "featured_platens.csv"))
        
        # 캘린더 정규화 (Day 0 기준)
        self._calibrate_calendar()

        self.num_blocks = len(self.df_blocks)
        self.num_platens = len(self.df_platens)

        self.reset()

    def _calibrate_calendar(self):
        self.df_blocks['est_dt'] = pd.to_datetime(self.df_blocks['earliest_start_date'])
        self.df_blocks['due_dt'] = pd.to_datetime(self.df_blocks['due_date'])
        self.base_date = self.df_blocks['est_dt'].min()
        self.df_blocks['est_day'] = (self.df_blocks['est_dt'] - self.base_date).dt.days
        self.df_blocks['due_day'] = (self.df_blocks['due_dt'] - self.base_date).dt.days

    def reset(self):
        self.current_block_idx = 0
        self.total_reward = 0.0
        self.step_count = 0
        self.platen_schedules: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(self.num_platens)}
        self.platen_available_day = np.zeros(self.num_platens, dtype=int)
        self.allocation_history = []
        return self.get_observation()

    def check_feasibility(self, block_idx: int, platen_idx: int) -> Tuple[bool, str]:
        block = self.df_blocks.iloc[block_idx]
        platen = self.df_platens.iloc[platen_idx]

        b_len, b_wid = block['length_m'], block['width_m']
        p_len, p_wid = platen['platen_length_m'], platen['platen_width_m']

        b_max, b_min = max(b_len, b_wid), min(b_len, b_wid)
        p_max, p_min = max(p_len, p_wid), min(p_len, p_wid)

        if b_max > p_max or b_min > p_min:
            return False, f"Spatial Violation"

        if block['weight_ton'] > platen['crane_capacity_ton']:
            return False, f"Crane Violation"

        return True, "Feasible"

    def find_earliest_start_day(self, block_idx: int, platen_idx: int) -> int:
        block = self.df_blocks.iloc[block_idx]
        est_day = int(block['est_day'])
        platen_free_day = int(self.platen_available_day[platen_idx])
        return max(est_day, platen_free_day)

    def step(self, action_platen_idx: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        if self.current_block_idx >= self.num_blocks:
            return self.get_observation(), 0.0, True, {"msg": "Episode finished"}

        block = self.df_blocks.iloc[self.current_block_idx]
        platen = self.df_platens.iloc[action_platen_idx]

        is_feasible, reason = self.check_feasibility(self.current_block_idx, action_platen_idx)

        reward = 0.0
        info = {
            "block_id": block['block_id'],
            "platen_id": platen['platen_id'],
            "is_feasible": is_feasible,
            "reason": reason
        }

        if not is_feasible:
            reward = -20.0
            fallback_p = self._find_fallback_platen(self.current_block_idx)
            planned_start_day = self.find_earliest_start_day(self.current_block_idx, fallback_p)
            chosen_p = fallback_p
        else:
            planned_start_day = self.find_earliest_start_day(self.current_block_idx, action_platen_idx)
            chosen_p = action_platen_idx

        lead_time = int(block['lead_time_days'])
        planned_end_day = planned_start_day + lead_time
        due_day = int(block['due_day'])
        delay_days = max(0, planned_end_day - due_day)
        early_days = max(0, due_day - planned_end_day)

        self.platen_schedules[chosen_p].append({
            "block_id": str(block['block_id']),
            "ship_id": str(block['ship_id']),
            "start_day": planned_start_day,
            "end_day": planned_end_day,
            "delay_days": delay_days
        })
        self.platen_available_day[chosen_p] = planned_end_day

        self.allocation_history.append({
            "block_idx": self.current_block_idx,
            "block_id": block['block_id'],
            "ship_id": block['ship_id'],
            "platen_idx": chosen_p,
            "platen_id": self.df_platens.iloc[chosen_p]['platen_id'],
            "platen_name": self.df_platens.iloc[chosen_p]['platen_name'],
            "planned_start_day": planned_start_day,
            "planned_end_day": planned_end_day,
            "due_day": due_day,
            "delay_days": delay_days,
            "lead_time_days": lead_time
        })

        if is_feasible:
            reward = self._calculate_reward(self.current_block_idx, chosen_p, delay_days, early_days)

        self.total_reward += reward
        self.current_block_idx += 1
        self.step_count += 1

        done = (self.current_block_idx >= self.num_blocks)
        next_state = self.get_observation()

        if done:
            info["metrics"] = self.get_summary_metrics()

        return next_state, reward, done, info

    def _find_fallback_platen(self, block_idx: int) -> int:
        for p_idx in range(self.num_platens):
            feas, _ = self.check_feasibility(block_idx, p_idx)
            if feas:
                return p_idx
        return 0

    def _calculate_reward(self, block_idx: int, platen_idx: int, delay_days: int, early_days: int) -> float:
        block = self.df_blocks.iloc[block_idx]
        platen = self.df_platens.iloc[platen_idx]

        if self.reward_version == "V1":
            return 1.0

        b_area = block['block_area_m2']
        p_area = platen['platen_area_m2']
        area_util = min(1.0, b_area / max(p_area, 1e-5))

        r_feas = 2.0
        r_delay = - (delay_days * 0.5)
        r_early = min(2.0, early_days * 0.05)
        r_util = area_util * 1.5

        if self.reward_version == "V2":
            return r_feas + r_delay + r_early + r_util

        workload_std = np.std(self.platen_available_day)
        r_balance = - (workload_std * 0.01)
        return r_feas + r_delay + r_early + r_util + r_balance

    def get_observation(self) -> np.ndarray:
        if self.current_block_idx >= self.num_blocks:
            return np.zeros(10 + self.num_platens * 3, dtype=np.float32)

        block = self.df_blocks.iloc[self.current_block_idx]
        b_feats = [
            block['length_m'] / 35.0,
            block['width_m'] / 25.0,
            block['weight_ton'] / 250.0,
            block['lead_time_days'] / 80.0,
            block['est_day'] / 1500.0,
            block['due_day'] / 1500.0,
            block['slack_days'] / 200.0,
            block['urgency_ratio'],
            1.0 if block['block_type'] == 'FLAT' else 0.0,
            float(block['cluster_id']) / 3.0
        ]

        p_feats = []
        max_avail = max(1, np.max(self.platen_available_day))
        for p_idx in range(self.num_platens):
            platen = self.df_platens.iloc[p_idx]
            p_feats.extend([
                self.platen_available_day[p_idx] / max(max_avail, 1500.0),
                platen['platen_area_m2'] / 800.0,
                platen['crane_capacity_ton'] / 350.0
            ])

        return np.array(b_feats + p_feats, dtype=np.float32)

    def get_summary_metrics(self) -> Dict[str, Any]:
        if not self.allocation_history:
            return {}

        df_res = pd.DataFrame(self.allocation_history)
        makespan = int(df_res['planned_end_day'].max())
        total_delay = int(df_res['delay_days'].sum())
        delayed_blocks = int((df_res['delay_days'] > 0).sum())
        avg_delay = float(df_res['delay_days'].mean())
        total_occupied = df_res['lead_time_days'].sum()
        utilization = round((total_occupied / (self.num_platens * makespan)) * 100, 2)
        workload_std = round(float(np.std(self.platen_available_day)), 2)

        return {
            "makespan": makespan,
            "delayed_blocks": delayed_blocks,
            "total_delay_days": total_delay,
            "avg_delay_days": round(avg_delay, 2),
            "utilization_pct": utilization,
            "workload_std": workload_std,
            "total_reward": round(self.total_reward, 2)
        }

if __name__ == "__main__":
    sim = ShipyardPlatenSimulator()
    print(f" Simulation Core Engine OK: Blocks={sim.num_blocks}, Platens={sim.num_platens}")
