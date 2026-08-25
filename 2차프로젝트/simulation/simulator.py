# simulation/simulator.py
"""
================================================================================
Shipyard Platen Discrete Event Simulator Engine
================================================================================
- Core Capabilities:
  1. 4-Physical Constraints Evaluation: Spatial (with 90-degree rotation), Crane Capacity, Precedence (EST), Non-overlapping platen schedule.
  2. Flexible Data Ingestion: Supports direct DataFrames, file paths, or directory paths.
  3. Action Masking: Generates exact boolean mask for feasible platens.
  4. 208-Dimensional State Representation: Normalized Block (10-dim) + 66 Platens (3-dim each).
  5. Multi-Version Reward Engine (V1/V2/V3) for Reinforcement Learning training.
================================================================================
"""

import os
import sys
from typing import Dict, List, Tuple, Any, Union, Optional
import numpy as np
import pandas as pd

class ShipyardPlatenSimulator:
    def __init__(
        self, 
        blocks_source: Union[str, pd.DataFrame] = None, 
        platens_source: Union[str, pd.DataFrame] = None,
        reward_version: str = "V2",
        order_by: str = "est_urgency"  # 'est_urgency' or 'raw'
    ):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(cur_dir)
        default_processed_dir = os.path.join(base_dir, "data/processed")

        # 1. Load Blocks
        if blocks_source is None:
            blocks_source = os.path.join(default_processed_dir, "featured_blocks.csv")

        if isinstance(blocks_source, pd.DataFrame):
            self.df_blocks = blocks_source.copy()
        elif os.path.isdir(blocks_source):
            self.df_blocks = pd.read_csv(os.path.join(blocks_source, "featured_blocks.csv"))
        else:
            self.df_blocks = pd.read_csv(blocks_source)

        # 2. Load Platens
        if platens_source is None:
            platens_source = os.path.join(default_processed_dir, "featured_platens.csv")

        if isinstance(platens_source, pd.DataFrame):
            self.df_platens = platens_source.copy()
        elif os.path.isdir(platens_source):
            self.df_platens = pd.read_csv(os.path.join(platens_source, "featured_platens.csv"))
        else:
            self.df_platens = pd.read_csv(platens_source)

        self.reward_version = reward_version
        self.order_by = order_by

        # Ensure seq_id exists
        if 'seq_id' not in self.df_blocks.columns:
            self.df_blocks['seq_id'] = np.arange(len(self.df_blocks))
        if 'seq_id' not in self.df_platens.columns:
            self.df_platens['seq_id'] = np.arange(len(self.df_platens))

        # Calendar calibration
        self._calibrate_calendar()

        # Sorting strategy
        if self.order_by == "est_urgency" and 'est_day' in self.df_blocks.columns and 'urgency_ratio' in self.df_blocks.columns:
            self.df_blocks = self.df_blocks.sort_values(by=['est_day', 'urgency_ratio'], ascending=[True, False]).reset_index(drop=True)

        self.num_blocks = len(self.df_blocks)
        self.num_platens = len(self.df_platens)

        self.reset()

    def _calibrate_calendar(self):
        if 'est_day' not in self.df_blocks.columns or 'due_day' not in self.df_blocks.columns:
            if 'earliest_start_date' in self.df_blocks.columns and 'due_date' in self.df_blocks.columns:
                self.df_blocks['est_dt'] = pd.to_datetime(self.df_blocks['earliest_start_date'])
                self.df_blocks['due_dt'] = pd.to_datetime(self.df_blocks['due_date'])
                self.base_date = self.df_blocks['est_dt'].min()
                self.df_blocks['est_day'] = (self.df_blocks['est_dt'] - self.base_date).dt.days
                self.df_blocks['due_day'] = (self.df_blocks['due_dt'] - self.base_date).dt.days

        # Ensure lead_time_days
        if 'lead_time_days' not in self.df_blocks.columns:
            if 'processing_time_days' in self.df_blocks.columns:
                self.df_blocks['lead_time_days'] = self.df_blocks['processing_time_days']

    def reset(self) -> np.ndarray:
        self.current_block_idx = 0
        self.total_reward = 0.0
        self.step_count = 0
        self.platen_schedules: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(self.num_platens)}
        self.platen_available_days = np.zeros(self.num_platens, dtype=int)
        self.allocation_history: List[Dict[str, Any]] = []
        return self._get_state()

    @property
    def platen_available_day(self):
        return self.platen_available_days

    def check_feasibility(self, block_idx: int, platen_idx: int) -> Tuple[bool, str]:
        """Verifies physical spatial fit (with 90-deg rotation) and crane capacity."""
        if block_idx >= self.num_blocks or platen_idx >= self.num_platens:
            return False, "INDEX_OUT_OF_BOUNDS"

        b = self.df_blocks.iloc[block_idx]
        p = self.df_platens.iloc[platen_idx]

        b_len = float(b.get('length_m', b.get('block_length_m', 0)))
        b_wid = float(b.get('width_m', b.get('block_width_m', 0)))
        b_wt  = float(b.get('weight_ton', 0))

        p_len = float(p['platen_length_m'])
        p_wid = float(p['platen_width_m'])
        p_cap = float(p['crane_capacity_ton'])

        b_max, b_min = max(b_len, b_wid), min(b_len, b_wid)
        p_max, p_min = max(p_len, p_wid), min(p_len, p_wid)

        if b_max > p_max or b_min > p_min:
            return False, "SPATIAL_EXCEEDED"

        if b_wt > p_cap:
            return False, "CRANE_CAPACITY_EXCEEDED"

        return True, "FEASIBLE"

    def get_action_mask(self, block_idx: Optional[int] = None) -> np.ndarray:
        """Returns boolean mask of valid platens for the current block."""
        if block_idx is None:
            block_idx = self.current_block_idx
        if block_idx >= self.num_blocks:
            return np.ones(self.num_platens, dtype=bool)

        mask = np.zeros(self.num_platens, dtype=bool)
        for p in range(self.num_platens):
            feas, _ = self.check_feasibility(block_idx, p)
            if feas:
                mask[p] = True
        if not np.any(mask):
            # Fallback to largest capacity platen
            mask[-1] = True
        return mask

    def step(self, action_platen_idx: int) -> Dict[str, Any]:
        if self.current_block_idx >= self.num_blocks:
            raise IndexError("All blocks already scheduled. Please reset simulator.")

        b = self.df_blocks.iloc[self.current_block_idx]
        p = self.df_platens.iloc[action_platen_idx]

        is_feasible, reason = self.check_feasibility(self.current_block_idx, action_platen_idx)

        est_day = int(b.get('est_day', 0))
        due_day = int(b.get('due_day', 0))
        lead_time = int(b.get('lead_time_days', b.get('processing_time_days', 10)))

        # Sequential platen scheduling (no-overlap)
        current_platen_free = int(self.platen_available_days[action_platen_idx])
        planned_start = max(est_day, current_platen_free)
        planned_end = planned_start + lead_time
        delay_days = max(0, planned_end - due_day)
        early_days = max(0, due_day - planned_end)

        # Update platen state
        self.platen_available_days[action_platen_idx] = planned_end

        # Calculate reward
        reward = self._calculate_reward(is_feasible, delay_days, early_days, b, p)
        self.total_reward += reward

        record = {
            "seq_id": int(b['seq_id']),
            "block_id": b['block_id'],
            "ship_id": b['ship_id'],
            "platen_idx": int(action_platen_idx),
            "platen_id": p['platen_id'],
            "platen_name": p['platen_name'],
            "planned_start_day": planned_start,
            "planned_end_day": planned_end,
            "due_day": due_day,
            "delay_days": delay_days,
            "lead_time_days": lead_time,
            "is_feasible": is_feasible,
            "reward": round(reward, 2)
        }

        self.allocation_history.append(record)
        self.platen_schedules[action_platen_idx].append(record)
        self.current_block_idx += 1
        self.step_count += 1

        return record

    def _calculate_reward(self, is_feasible: bool, delay_days: int, early_days: int, b: pd.Series, p: pd.Series) -> float:
        if not is_feasible:
            return -500.0

        b_len = float(b.get('length_m', b.get('block_length_m', 0)))
        b_wid = float(b.get('width_m', b.get('block_width_m', 0)))
        b_area = b_len * b_wid
        p_area = float(p['platen_area_m2'])
        area_utilization = min(1.0, b_area / max(1.0, p_area))

        if self.reward_version == "V1":
            return -float(delay_days) + 0.1 * early_days
        elif self.reward_version == "V2":
            r = 10.0
            r -= float(delay_days) * 2.0
            r += min(5.0, early_days * 0.2)
            r += area_utilization * 5.0
            return r
        else: # V3: Workload balance
            avg_avail = np.mean(self.platen_available_days)
            std_avail = np.std(self.platen_available_days)
            r = 10.0 - float(delay_days) * 3.0 + area_utilization * 5.0 - (std_avail * 0.05)
            return r

    def _get_state(self) -> np.ndarray:
        if self.current_block_idx >= self.num_blocks:
            return np.zeros(10 + self.num_platens * 3, dtype=np.float32)

        b = self.df_blocks.iloc[self.current_block_idx]

        b_len = float(b.get('length_m', b.get('block_length_m', 0)))
        b_wid = float(b.get('width_m', b.get('block_width_m', 0)))
        b_wt  = float(b.get('weight_ton', 0))
        b_lead = float(b.get('lead_time_days', b.get('processing_time_days', 10)))
        b_est = float(b.get('est_day', 0))
        b_due = float(b.get('due_day', 0))
        b_slack = float(b.get('slack_days', (b_due - b_est) - b_lead))
        b_urgency = float(b.get('urgency_ratio', min(1.0, b_lead / max(1.0, b_due - b_est))))
        b_type = 1.0 if str(b.get('block_type', '')).upper() == 'FLAT' else 0.0
        b_cluster = float(b.get('block_cluster', 0)) / 4.0

        block_feature = [
            b_len / 35.0,
            b_wid / 25.0,
            b_wt / 250.0,
            b_lead / 80.0,
            b_est / 1500.0,
            b_due / 1500.0,
            b_slack / 200.0,
            b_urgency,
            b_type,
            b_cluster
        ]

        platen_features = []
        for p_idx in range(self.num_platens):
            p = self.df_platens.iloc[p_idx]
            avail_day = float(self.platen_available_days[p_idx])
            p_area = float(p['platen_area_m2'])
            p_cap = float(p['crane_capacity_ton'])
            platen_features.extend([
                avail_day / 1500.0,
                p_area / 800.0,
                p_cap / 350.0
            ])

        state_vector = np.array(block_feature + platen_features, dtype=np.float32)
        return state_vector

    def get_summary_metrics(self) -> Dict[str, Any]:
        if not self.allocation_history:
            return {"status": "EMPTY"}
        df_hist = pd.DataFrame(self.allocation_history)
        makespan = int(df_hist['planned_end_day'].max() - df_hist['planned_start_day'].min())
        delayed_blocks = int((df_hist['delay_days'] > 0).sum())
        total_delay = int(df_hist['delay_days'].sum())
        avg_delay = round(total_delay / max(1, len(df_hist)), 2)
        total_lead = float(df_hist['lead_time_days'].sum())
        utilization = round((total_lead / max(1, (self.num_platens * makespan))) * 100, 2)

        return {
            "total_blocks": len(df_hist),
            "makespan": makespan,
            "delayed_blocks": delayed_blocks,
            "total_delay_days": total_delay,
            "avg_delay_days": avg_delay,
            "utilization_pct": utilization,
            "total_reward": round(self.total_reward, 2)
        }
