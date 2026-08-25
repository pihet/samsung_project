# simulation/simulator.py
"""
================================================================================
Shipyard Platen Discrete Event Simulator Engine
================================================================================
- Modeled Constraints (Explicit Definitions):
  1. Spatial Feasibility (with 90-deg planar rotation):
     max(block_length, block_width) <= max(platen_length, platen_width) and
     min(block_length, block_width) <= min(platen_length, platen_width)
  2. Crane Capacity Feasibility:
     block_weight_ton <= platen_crane_capacity_ton
  3. EST Precedence (Arrival Date):
     planned_start_day >= earliest_start_day (EST).
     (Note: This models earliest available release date; inter-block DAG dependencies
      are not modeled due to absence of dependency graph in source data).
  4. Platen Non-overlapping (Single-Occupancy Interval):
     Each platen processes one block at a time sequentially [planned_start, planned_end).
     (Note: Multi-block 2D coordinate sub-packing within a platen is not modeled).
  5. Initial Platen Status (2017-11-16 vs 2018-02-24):
     Initial platen occupancy from initial_platen_status.csv ended on 2017-11-16 (Day 43055),
     which is 100 days prior to the first block arrival on 2018-02-24 (Day 43155).
     Thus all 66 platens start fully available (day 0) at simulation launch.

- Hard Constraint & Infeasibility Handling:
  - If a block has NO feasible platens across the entire shipyard:
    The block is explicitly recorded as INFEASIBLE_REJECTED with is_feasible=False.
  - If a block has feasible platens but an invalid action is chosen:
    Agent receives a heavy penalty (-500.0) and simulator falls back to a valid platen.
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
        reward_version: str = "V2",
        order_by: str = "est_urgency"  # 'est_urgency' or 'raw'
    ):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(cur_dir)
        default_processed_dir = os.path.join(base_dir, "data/processed")
        default_standardized_dir = os.path.join(base_dir, "data/standardized")

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
            else:
                self.base_date = pd.to_datetime("2018-02-24")

        # Ensure lead_time_days
        if 'lead_time_days' not in self.df_blocks.columns:
            if 'processing_time_days' in self.df_blocks.columns:
                self.df_blocks['lead_time_days'] = self.df_blocks['processing_time_days']

    def reset(self) -> np.ndarray:
        self.current_block_idx = 0
        self.total_reward = 0.0
        self.step_count = 0
        self.platen_schedules: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(self.num_platens)}
        
        # Initial availability calculation from initial_platen_status.csv
        self.platen_available_days = np.zeros(self.num_platens, dtype=int)
        if self.df_initial_status is not None and 'expected_end_day_serial' in self.df_initial_status.columns:
            # Base date 2018-02-24 is Excel serial 43155
            base_serial = 43155
            for _, row in self.df_initial_status.iterrows():
                p_name = str(row.get('platen_name', ''))
                end_serial = int(row['expected_end_day_serial'])
                # Find matching platen
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
        """Verifies physical spatial fit (with 90-deg rotation) and crane capacity."""
        if block_idx >= self.num_blocks or platen_idx >= self.num_platens or platen_idx < 0:
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
        """Returns boolean mask of valid platens. If block is impossible, returns all False."""
        if block_idx is None:
            block_idx = self.current_block_idx
        if block_idx >= self.num_blocks:
            return np.ones(self.num_platens, dtype=bool)

        mask = np.zeros(self.num_platens, dtype=bool)
        for p in range(self.num_platens):
            feas, _ = self.check_feasibility(block_idx, p)
            if feas:
                mask[p] = True
        return mask

    def find_safe_fallback_platen(self, block_idx: int) -> Optional[int]:
        """Finds earliest available feasible platen, or None if physically impossible across all platens."""
        mask = self.get_action_mask(block_idx)
        valid_platens = np.where(mask)[0]
        if len(valid_platens) == 0:
            return None

        b = self.df_blocks.iloc[block_idx]
        est_d = int(b.get('est_day', 0))

        best_p = valid_platens[0]
        best_start = max(est_d, int(self.platen_available_days[best_p]))
        for p in valid_platens:
            s_cand = max(est_d, int(self.platen_available_days[p]))
            if s_cand < best_start:
                best_start = s_cand
                best_p = p
        return int(best_p)

    def step(self, action_platen_idx: int) -> Dict[str, Any]:
        if self.current_block_idx >= self.num_blocks:
            raise IndexError("All blocks already scheduled. Please reset simulator.")

        b = self.df_blocks.iloc[self.current_block_idx]
        is_requested_feasible, reason = self.check_feasibility(self.current_block_idx, action_platen_idx)

        # Check overall block feasibility across all platens
        mask = self.get_action_mask(self.current_block_idx)
        valid_platens = np.where(mask)[0]

        if len(valid_platens) == 0:
            # Case 1: Block cannot be placed on any platen in the shipyard
            reward = -1000.0
            self.total_reward += reward
            record = {
                "seq_id": int(b['seq_id']),
                "block_id": b['block_id'],
                "ship_id": b['ship_id'],
                "platen_idx": -1,
                "platen_id": "NONE",
                "platen_name": "INFEASIBLE_REJECTED",
                "planned_start_day": -1,
                "planned_end_day": -1,
                "due_day": int(b.get('due_day', 0)),
                "delay_days": 9999,
                "lead_time_days": int(b.get('lead_time_days', 0)),
                "is_feasible": False,
                "requested_feasible": False,
                "status": "INFEASIBLE_REJECTED",
                "reward": round(reward, 2)
            }
            self.allocation_history.append(record)
            self.current_block_idx += 1
            self.step_count += 1
            return record

        if not is_requested_feasible:
            # Case 2: Requested platen is invalid, but other feasible platens exist -> Safe fallback with penalty
            actual_platen_idx = self.find_safe_fallback_platen(self.current_block_idx)
            penalty = -500.0
        else:
            # Case 3: Valid platen requested
            actual_platen_idx = int(action_platen_idx)
            penalty = 0.0

        p = self.df_platens.iloc[actual_platen_idx]

        est_day = int(b.get('est_day', 0))
        due_day = int(b.get('due_day', 0))
        lead_time = int(b.get('lead_time_days', b.get('processing_time_days', 10)))

        # Sequential platen scheduling (no-overlap)
        current_platen_free = int(self.platen_available_days[actual_platen_idx])
        planned_start = max(est_day, current_platen_free)
        planned_end = planned_start + lead_time
        delay_days = max(0, planned_end - due_day)
        early_days = max(0, due_day - planned_end)

        # Update platen state
        self.platen_available_days[actual_platen_idx] = planned_end

        # Calculate reward
        reward = self._calculate_reward(is_requested_feasible, delay_days, early_days, b, p) + penalty
        self.total_reward += reward

        record = {
            "seq_id": int(b['seq_id']),
            "block_id": b['block_id'],
            "ship_id": b['ship_id'],
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

    def _calculate_reward(self, is_feasible: bool, delay_days: int, early_days: int, b: pd.Series, p: pd.Series) -> float:
        if not is_feasible:
            return -100.0

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
        
        # Connect EDA cluster_id (0..3)
        b_cluster = float(b.get('cluster_id', b.get('block_cluster', 0))) / 4.0

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
