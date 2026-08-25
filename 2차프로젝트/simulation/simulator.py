# simulation/simulator.py
"""
================================================================================
Shipyard Platen Discrete Event Simulator Engine (High-Performance Vectorized)
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
        initial_status_source: Union[str, pd.DataFrame] = None,
        feature_version: str = "V2",  # 'V1' or 'V2'
        reward_version: str = "V2",   # 'V1', 'V2', 'V3'
        order_by: str = "est_urgency" # 'est_urgency' or 'raw'
    ):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(cur_dir)
        features_dir = os.path.join(base_dir, "data/processed/features")
        processed_dir = os.path.join(base_dir, "data/processed")
        default_standardized_dir = os.path.join(base_dir, "data/standardized")

        # 1. Load Blocks (Supports features/ folder with fallback)
        if blocks_source is None:
            cand1 = os.path.join(features_dir, "featured_blocks.csv")
            cand2 = os.path.join(processed_dir, "featured_blocks.csv")
            blocks_source = cand1 if os.path.exists(cand1) else cand2

        if isinstance(blocks_source, pd.DataFrame):
            self.df_blocks = blocks_source.copy()
        elif os.path.isdir(blocks_source):
            self.df_blocks = pd.read_csv(os.path.join(blocks_source, "featured_blocks.csv"))
        else:
            self.df_blocks = pd.read_csv(blocks_source)

        # 2. Load Platens (Supports features/ folder with fallback)
        if platens_source is None:
            cand1 = os.path.join(features_dir, "featured_platens.csv")
            cand2 = os.path.join(processed_dir, "featured_platens.csv")
            platens_source = cand1 if os.path.exists(cand1) else cand2

        if isinstance(platens_source, pd.DataFrame):
            self.df_platens = platens_source.copy()
        elif os.path.isdir(platens_source):
            self.df_platens = pd.read_csv(os.path.join(platens_source, "featured_platens.csv"))
        else:
            self.df_platens = pd.read_csv(platens_source)

        # 3. Load Initial Platen Status (Optional)
        self.df_initial_status = None
        if initial_status_source is not None:
            if isinstance(initial_status_source, pd.DataFrame):
                self.df_initial_status = initial_status_source.copy()
            elif os.path.exists(initial_status_source):
                self.df_initial_status = pd.read_csv(initial_status_source)
        else:
            std_init = os.path.join(default_standardized_dir, "initial_platen_status.csv")
            if os.path.exists(std_init):
                self.df_initial_status = pd.read_csv(std_init)

        self.feature_version = feature_version
        self.reward_version = reward_version
        self.order_by = order_by

        if 'seq_id' not in self.df_blocks.columns:
            self.df_blocks['seq_id'] = np.arange(len(self.df_blocks))
        if 'seq_id' not in self.df_platens.columns:
            self.df_platens['seq_id'] = np.arange(len(self.df_platens))

        self._calibrate_calendar()

        if self.order_by == "est_urgency" and 'est_day' in self.df_blocks.columns and 'urgency_ratio' in self.df_blocks.columns:
            self.df_blocks = self.df_blocks.sort_values(by=['est_day', 'urgency_ratio'], ascending=[True, False]).reset_index(drop=True)

        self.num_blocks = len(self.df_blocks)
        self.num_platens = len(self.df_platens)

        self._pre_extract_numpy_arrays()
        self.reset()

    def _calibrate_calendar(self):
        if 'est_day' not in self.df_blocks.columns or 'due_day' not in self.df_blocks.columns:
            if 'earliest_start_date' in self.df_blocks.columns and 'due_date' in self.df_blocks.columns:
                self.df_blocks['est_dt'] = pd.to_datetime(self.df_blocks['earliest_start_date'])
                self.df_blocks['due_dt'] = pd.to_datetime(self.df_blocks['due_date'])
                self.base_date = self.df_blocks['est_dt'].min()
                self.df_blocks['est_day'] = (self.df_blocks['est_dt'] - self.base_date).dt.days
                self.df_blocks['due_day'] = (self.df_blocks['due_dt'] - self.base_date).dt.days
            else:
                self.base_date = pd.to_datetime("2018-02-24")

        if 'lead_time_days' not in self.df_blocks.columns and 'processing_time_days' in self.df_blocks.columns:
            self.df_blocks['lead_time_days'] = self.df_blocks['processing_time_days']

    def _pre_extract_numpy_arrays(self):
        b_len = self.df_blocks['length_m'].to_numpy(dtype=np.float32) if 'length_m' in self.df_blocks.columns else self.df_blocks['block_length_m'].to_numpy(dtype=np.float32)
        b_wid = self.df_blocks['width_m'].to_numpy(dtype=np.float32) if 'width_m' in self.df_blocks.columns else self.df_blocks['block_width_m'].to_numpy(dtype=np.float32)
        self.b_max = np.maximum(b_len, b_wid)
        self.b_min = np.minimum(b_len, b_wid)
        self.b_area = b_len * b_wid
        self.b_wt = self.df_blocks['weight_ton'].to_numpy(dtype=np.float32)
        self.b_lead = self.df_blocks['lead_time_days'].to_numpy(dtype=np.int32)
        self.b_est = self.df_blocks['est_day'].to_numpy(dtype=np.int32)
        self.b_due = self.df_blocks['due_day'].to_numpy(dtype=np.int32)
        self.b_seq = self.df_blocks['seq_id'].to_numpy(dtype=np.int32)
        self.b_type = (self.df_blocks['block_type'].astype(str).str.upper() == 'FLAT').to_numpy(dtype=np.float32) if 'block_type' in self.df_blocks.columns else np.ones(self.num_blocks, dtype=np.float32)

        if 'slack_days' in self.df_blocks.columns:
            self.b_slack = (self.df_blocks['slack_days'].to_numpy(dtype=np.float32)) / 200.0
        else:
            self.b_slack = ((self.b_due - self.b_est) - self.b_lead).astype(np.float32) / 200.0

        if 'urgency_ratio' in self.df_blocks.columns:
            self.b_urgency = self.df_blocks['urgency_ratio'].to_numpy(dtype=np.float32)
        else:
            self.b_urgency = (self.b_lead / np.maximum(1.0, (self.b_due - self.b_est).astype(np.float32)))

        cluster_col = 'cluster_id' if 'cluster_id' in self.df_blocks.columns else 'block_cluster'
        self.b_cluster = (self.df_blocks[cluster_col].to_numpy(dtype=np.float32) / 4.0) if cluster_col in self.df_blocks.columns else np.zeros(self.num_blocks, dtype=np.float32)

        p_len = self.df_platens['platen_length_m'].to_numpy(dtype=np.float32)
        p_wid = self.df_platens['platen_width_m'].to_numpy(dtype=np.float32)
        self.p_max = np.maximum(p_len, p_wid)
        self.p_min = np.minimum(p_len, p_wid)
        self.p_cap = self.df_platens['crane_capacity_ton'].to_numpy(dtype=np.float32)
        self.p_area = self.df_platens['platen_area_m2'].to_numpy(dtype=np.float32)

        self.feasibility_matrix = (
            (self.b_max[:, None] <= self.p_max[None, :]) &
            (self.b_min[:, None] <= self.p_min[None, :]) &
            (self.b_wt[:, None] <= self.p_cap[None, :])
        )

    def reset(self) -> np.ndarray:
        self.current_block_idx = 0
        self.total_reward = 0.0
        self.step_count = 0
        self.platen_schedules: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(self.num_platens)}
        
        self.platen_available_days = np.zeros(self.num_platens, dtype=np.int32)
        if self.df_initial_status is not None and 'expected_end_day_serial' in self.df_initial_status.columns:
            base_serial = 43155
            for _, row in self.df_initial_status.iterrows():
                p_name = str(row.get('platen_name', ''))
                end_serial = int(row['expected_end_day_serial'])
                p_matches = self.df_platens[self.df_platens['platen_name'] == p_name]
                if len(p_matches) > 0:
                    p_idx = int(p_matches.index[0])
                    init_avail = max(0, end_serial - base_serial)
                    self.platen_available_days[p_idx] = max(self.platen_available_days[p_idx], init_avail)

        self.allocation_history: List[Dict[str, Any]] = []
        return self._get_state()

    @property
    def platen_available_day(self):
        return self.platen_available_days

    def check_feasibility(self, block_idx: int, platen_idx: int) -> Tuple[bool, str]:
        if block_idx >= self.num_blocks or platen_idx >= self.num_platens or platen_idx < 0:
            return False, "INDEX_OUT_OF_BOUNDS"
        is_feas = bool(self.feasibility_matrix[block_idx, platen_idx])
        return is_feas, "FEASIBLE" if is_feas else "CONSTRAINT_VIOLATION"

    def get_action_mask(self, block_idx: Optional[int] = None) -> np.ndarray:
        if block_idx is None:
            block_idx = self.current_block_idx
        if block_idx >= self.num_blocks:
            return np.ones(self.num_platens, dtype=bool)
        return self.feasibility_matrix[block_idx]

    def find_safe_fallback_platen(self, block_idx: int) -> Optional[int]:
        valid_platens = np.where(self.feasibility_matrix[block_idx])[0]
        if len(valid_platens) == 0:
            return None

        est_d = self.b_est[block_idx]
        avail_subset = self.platen_available_days[valid_platens]
        starts = np.maximum(est_d, avail_subset)
        best_local_idx = np.argmin(starts)
        return int(valid_platens[best_local_idx])

    def step(self, action_platen_idx: int) -> Dict[str, Any]:
        if self.current_block_idx >= self.num_blocks:
            raise IndexError("All blocks already scheduled. Please reset simulator.")

        idx = self.current_block_idx
        valid_platens = np.where(self.feasibility_matrix[idx])[0]

        if len(valid_platens) == 0:
            reward = -1000.0
            self.total_reward += reward
            record = {
                "seq_id": int(self.b_seq[idx]),
                "block_id": self.df_blocks.iloc[idx]['block_id'],
                "ship_id": self.df_blocks.iloc[idx]['ship_id'],
                "platen_idx": -1,
                "platen_id": "NONE",
                "platen_name": "INFEASIBLE_REJECTED",
                "planned_start_day": -1,
                "planned_end_day": -1,
                "due_day": int(self.b_due[idx]),
                "delay_days": 9999,
                "lead_time_days": int(self.b_lead[idx]),
                "is_feasible": False,
                "requested_feasible": False,
                "status": "INFEASIBLE_REJECTED",
                "reward": round(reward, 2)
            }
            self.allocation_history.append(record)
            self.current_block_idx += 1
            self.step_count += 1
            return record

        is_requested_feasible = bool(self.feasibility_matrix[idx, action_platen_idx]) if (0 <= action_platen_idx < self.num_platens) else False

        if not is_requested_feasible:
            actual_platen_idx = self.find_safe_fallback_platen(idx)
            penalty = -500.0
        else:
            actual_platen_idx = int(action_platen_idx)
            penalty = 0.0

        est_day = int(self.b_est[idx])
        due_day = int(self.b_due[idx])
        lead_time = int(self.b_lead[idx])

        current_platen_free = int(self.platen_available_days[actual_platen_idx])
        planned_start = max(est_day, current_platen_free)
        planned_end = planned_start + lead_time
        delay_days = max(0, planned_end - due_day)
        early_days = max(0, due_day - planned_end)

        self.platen_available_days[actual_platen_idx] = planned_end

        reward = self._calculate_reward_fast(is_requested_feasible, delay_days, early_days, idx, actual_platen_idx) + penalty
        self.total_reward += reward

        p = self.df_platens.iloc[actual_platen_idx]
        record = {
            "seq_id": int(self.b_seq[idx]),
            "block_id": self.df_blocks.iloc[idx]['block_id'],
            "ship_id": self.df_blocks.iloc[idx]['ship_id'],
            "platen_idx": int(actual_platen_idx),
            "platen_id": p['platen_id'],
            "platen_name": p['platen_name'],
            "planned_start_day": planned_start,
            "planned_end_day": planned_end,
            "due_day": due_day,
            "delay_days": delay_days,
            "lead_time_days": lead_time,
            "is_feasible": True,
            "requested_feasible": is_requested_feasible,
            "status": "ALLOCATED",
            "reward": round(reward, 2)
        }

        self.allocation_history.append(record)
        self.platen_schedules[actual_platen_idx].append(record)
        self.current_block_idx += 1
        self.step_count += 1

        return record

    def _calculate_reward_fast(self, is_feasible: bool, delay_days: int, early_days: int, b_idx: int, p_idx: int) -> float:
        if not is_feasible:
            return -100.0

        b_area = float(self.b_area[b_idx])
        p_area = float(self.p_area[p_idx])
        area_utilization = min(1.0, b_area / max(1.0, p_area))

        if self.reward_version == "V1":
            return -1.0 * float(delay_days)
        elif self.reward_version == "V2":
            r = 10.0 - float(delay_days) * 2.0 + min(5.0, early_days * 0.2) + area_utilization * 5.0
            return r
        else:
            std_avail = float(np.std(self.platen_available_days))
            r = 10.0 - 0.05 * (float(delay_days) ** 2) + 5.0 * area_utilization - 0.05 * std_avail + min(5.0, 0.2 * float(early_days))
            return r

    def _get_state(self) -> np.ndarray:
        if self.current_block_idx >= self.num_blocks:
            return np.zeros(10 + self.num_platens * 3, dtype=np.float32)

        idx = self.current_block_idx

        if self.feature_version == "V1":
            b_slack = 0.0
            b_urgency = 0.0
            b_cluster = 0.0
        else:
            b_slack = float(self.b_slack[idx])
            b_urgency = float(self.b_urgency[idx])
            b_cluster = float(self.b_cluster[idx])

        block_feature = [
            float(self.b_max[idx]) / 35.0,
            float(self.b_min[idx]) / 25.0,
            float(self.b_wt[idx]) / 250.0,
            float(self.b_lead[idx]) / 80.0,
            float(self.b_est[idx]) / 1500.0,
            float(self.b_due[idx]) / 1500.0,
            b_slack,
            b_urgency,
            float(self.b_type[idx]),
            b_cluster
        ]

        p_feat_avail = (self.platen_available_days / 1500.0).astype(np.float32)
        p_feat_area = (self.p_area / 800.0).astype(np.float32)
        p_feat_cap = (self.p_cap / 350.0).astype(np.float32)

        platen_matrix = np.column_stack([p_feat_avail, p_feat_area, p_feat_cap]).flatten()
        state_vector = np.concatenate([np.array(block_feature, dtype=np.float32), platen_matrix])
        return state_vector

    def get_summary_metrics(self) -> Dict[str, Any]:
        if not self.allocation_history:
            return {"status": "EMPTY"}
        df_hist = pd.DataFrame(self.allocation_history)
        df_valid = df_hist[df_hist['is_feasible']]
        
        if len(df_valid) == 0:
            return {"status": "ALL_INFEASIBLE", "total_blocks": len(df_hist), "makespan": 0}

        makespan = int(df_valid['planned_end_day'].max() - df_valid['planned_start_day'].min())
        delayed_blocks = int((df_valid['delay_days'] > 0).sum())
        total_delay = int(df_valid['delay_days'].sum())
        avg_delay = round(total_delay / max(1, len(df_valid)), 2)
        total_lead = float(df_valid['lead_time_days'].sum())
        utilization = round((total_lead / max(1, (self.num_platens * makespan))) * 100, 2)

        return {
            "total_blocks": len(df_hist),
            "feasible_blocks": len(df_valid),
            "infeasible_blocks": len(df_hist) - len(df_valid),
            "makespan": makespan,
            "delayed_blocks": delayed_blocks,
            "total_delay_days": total_delay,
            "avg_delay_days": avg_delay,
            "utilization_pct": utilization,
            "total_reward": round(self.total_reward, 2)
        }
