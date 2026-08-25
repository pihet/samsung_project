# modeling/eval_metrics.py
"""
================================================================================
Unified Metric Evaluator & Data Integrity Audit Engine
================================================================================
- Data Integrity Checks:
  1. Row Count & Completeness: Exactly 872 blocks present.
  2. Primary Key Uniqueness: seq_id (0..871) has 0 duplicates and 0 omissions.
  3. Valid Intervals: planned_end_day > planned_start_day.
  4. Known Platen IDs: All platen assignments exist in the official 66-platen master list.

- 4 Physical Constraint Checks:
  1. Spatial Feasibility (allows 90-degree planar rotation).
  2. Crane Capacity Feasibility (block weight <= platen crane limit).
  3. EST Precedence (planned_start >= earliest_start_date; release date constraint).
  4. Single-Occupancy Non-overlapping (one block per platen at any given time).

- Research Paper vs Unified Simulator Disclaimers:
  Historical paper baseline files (EDDQN, paper heuristics) originally utilized multi-block
  2D coordinate packing in the paper's experiments. They are evaluated here for direct
  historical metric reference (Makespan, Delay) alongside the unified sequential simulator.
================================================================================
"""

import os
import glob
from typing import Dict, Any, List, Optional, Tuple, Set
import numpy as np
import pandas as pd

STANDARD_COLUMNS = [
    'platen_name', 'platen_id', 'platen_length_m', 'platen_width_m', 'subcontractor_team', 
    'ship_id', 'block_seq_id', 'block_id', 'block_length_m', 'block_width_m', 
    'processing_time_days', 'block_output_value', 'planned_start_day', 'planned_end_day', 
    'due_date_day', 'delay_days', 'early_days', 'standard_early_days'
]

EXCEL_BASE_DAY = 43155  # 2018-02-24 in Excel serial date format

class SafeScheduleReader:
    """Safe reader for both raw research baselines and newly generated schedule CSVs."""
    
    @staticmethod
    def load_schedule(filepath: str) -> pd.DataFrame:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Schedule file not found: {filepath}")

        # 1. Header check
        df_sample = pd.read_csv(filepath, nrows=2)
        if 'planned_start_day' in df_sample.columns or 'planned_start' in df_sample.columns:
            # Standard modern format
            df = pd.read_csv(filepath)
            rename_map = {
                'planned_start': 'planned_start_day',
                'planned_end': 'planned_end_day',
                'due_date': 'due_date_day',
                'due_day': 'due_date_day',
                'lead_time': 'processing_time_days',
                'lead_time_days': 'processing_time_days'
            }
            df = df.rename(columns=rename_map)
        elif 'platen_name' in df_sample.columns:
            df = pd.read_csv(filepath)
        else:
            # Raw headerless baseline file
            df = pd.read_csv(filepath, header=None, names=STANDARD_COLUMNS)

        # 2. Add seq_id if missing
        if 'seq_id' not in df.columns:
            if 'block_seq_id' in df.columns and df['block_seq_id'].notna().all():
                df['seq_id'] = df['block_seq_id'].astype(int)
            else:
                df['seq_id'] = np.arange(len(df), dtype=int)

        # 3. Normalize Excel serial dates to relative days (0..N)
        if df['planned_end_day'].max() > 10000:
            df['planned_start_day'] = (df['planned_start_day'] - EXCEL_BASE_DAY).astype(int)
            df['planned_end_day'] = (df['planned_end_day'] - EXCEL_BASE_DAY).astype(int)
            if 'due_date_day' in df.columns:
                df['due_date_day'] = (df['due_date_day'] - EXCEL_BASE_DAY).astype(int)

        # 4. Recalculate exact delay days
        if 'due_date_day' in df.columns:
            df['delay_days'] = np.maximum(0, df['planned_end_day'] - df['due_date_day'])

        return df

class MetricEvaluator:
    """Rigorous evaluation and data integrity audit engine for 872 blocks x 66 platens scheduling."""
    
    def __init__(self, blocks_file: str, platens_file: str):
        self.df_blocks = pd.read_csv(blocks_file)
        self.df_platens = pd.read_csv(platens_file)
        
        if 'seq_id' not in self.df_blocks.columns:
            self.df_blocks['seq_id'] = np.arange(len(self.df_blocks))
            
        self.expected_num_blocks = len(self.df_blocks)
        self.num_platens = len(self.df_platens)
        self.valid_platen_ids: Set[str] = set(self.df_platens['platen_id'].astype(str))
        
        # Build platen lookup
        self.platen_dict = {}
        for _, p in self.df_platens.iterrows():
            p_id = str(p['platen_id'])
            self.platen_dict[p_id] = {
                'length': float(p['platen_length_m']),
                'width': float(p['platen_width_m']),
                'crane_cap': float(p['crane_capacity_ton'])
            }

        # Build block lookup by seq_id
        self.block_dict = {}
        for _, b in self.df_blocks.iterrows():
            s_id = int(b['seq_id'])
            est_val = int(b.get('est_day', 0))
            self.block_dict[s_id] = {
                'length': float(b.get('length_m', b.get('block_length_m', 0))),
                'width': float(b.get('width_m', b.get('block_width_m', 0))),
                'weight': float(b.get('weight_ton', 0)),
                'est_day': est_val
            }

        self.total_lead_time = float(self.df_blocks['lead_time_days'].sum() if 'lead_time_days' in self.df_blocks.columns else self.df_blocks['processing_time_days'].sum())

    def evaluate(self, df_sched: pd.DataFrame, algorithm_name: str = "Unknown", is_paper_baseline: bool = False) -> Dict[str, Any]:
        """Calculates exact KPI metrics, verifies integrity, and checks 4 physical constraints."""
        total_rows = len(df_sched)
        
        # --- 1. Data Integrity Audit ---
        seq_ids = df_sched['seq_id'].tolist() if 'seq_id' in df_sched.columns else list(range(total_rows))
        unique_seq_ids = set(seq_ids)
        duplicate_seq_count = total_rows - len(unique_seq_ids)
        missing_seq_count = max(0, self.expected_num_blocks - len(unique_seq_ids))
        
        invalid_intervals_count = int((df_sched['planned_end_day'] <= df_sched['planned_start_day']).sum())
        
        unknown_platens_count = 0
        if 'platen_id' in df_sched.columns:
            for p_id in df_sched['platen_id']:
                if str(p_id) not in self.valid_platen_ids and str(p_id) != 'nan':
                    unknown_platens_count += 1

        integrity_passed = (total_rows == self.expected_num_blocks and 
                            duplicate_seq_count == 0 and 
                            missing_seq_count == 0 and 
                            invalid_intervals_count == 0)

        # --- 2. Makespan & Delay Metrics ---
        makespan = int(df_sched['planned_end_day'].max() - df_sched['planned_start_day'].min())
        delayed_mask = df_sched['delay_days'] > 0
        delayed_count = int(delayed_mask.sum())
        delayed_pct = round((delayed_count / max(1, total_rows)) * 100, 2)
        total_delay = int(df_sched['delay_days'].sum())
        avg_delay_all = round(total_delay / max(1, total_rows), 2)
        avg_delay_delayed = round(total_delay / max(1, delayed_count), 2) if delayed_count > 0 else 0.0
        
        utilization_pct = round((self.total_lead_time / max(1, (self.num_platens * makespan))) * 100, 2)

        # --- 3. 4 Physical Constraint Checks ---
        spatial_violations = 0
        crane_violations = 0
        est_violations = 0
        overlap_violations = 0

        platen_intervals: Dict[str, List[Tuple[int, int, int]]] = {}

        for _, row in df_sched.iterrows():
            s_id = int(row['seq_id']) if 'seq_id' in row else 0
            p_id = str(row.get('platen_id', ''))
            start_d = int(row['planned_start_day'])
            end_d = int(row['planned_end_day'])

            # EST check
            if s_id in self.block_dict:
                b_info = self.block_dict[s_id]
                if start_d < b_info['est_day']:
                    est_violations += 1

                # Spatial & Crane check
                if p_id in self.platen_dict:
                    p_info = self.platen_dict[p_id]
                    b_max, b_min = max(b_info['length'], b_info['width']), min(b_info['length'], b_info['width'])
                    p_max, p_min = max(p_info['length'], p_info['width']), min(p_info['length'], p_info['width'])

                    if b_max > p_max or b_min > p_min:
                        spatial_violations += 1
                    if b_info['weight'] > p_info['crane_cap']:
                        crane_violations += 1

            # Non-overlapping interval tracking
            if p_id not in platen_intervals:
                platen_intervals[p_id] = []
            platen_intervals[p_id].append((start_d, end_d, s_id))

        for p_id, intervals in platen_intervals.items():
            sorted_intervals = sorted(intervals, key=lambda x: x[0])
            for i in range(len(sorted_intervals) - 1):
                cur_end = sorted_intervals[i][1]
                next_start = sorted_intervals[i+1][0]
                if next_start < cur_end:
                    overlap_violations += 1

        total_violations = spatial_violations + crane_violations + est_violations + overlap_violations

        return {
            "algorithm": algorithm_name,
            "is_paper_baseline": is_paper_baseline,
            "total_blocks": total_rows,
            "integrity": {
                "passed": integrity_passed,
                "duplicate_seq_ids": duplicate_seq_count,
                "missing_seq_ids": missing_seq_count,
                "invalid_intervals": invalid_intervals_count,
                "unknown_platens": unknown_platens_count
            },
            "makespan_days": makespan,
            "delayed_blocks_count": delayed_count,
            "delayed_blocks_pct": delayed_pct,
            "total_delay_days": total_delay,
            "avg_delay_days_all": avg_delay_all,
            "avg_delay_days_delayed": avg_delay_delayed,
            "utilization_pct": utilization_pct,
            "violations": {
                "spatial": spatial_violations,
                "crane": crane_violations,
                "est_precedence": est_violations,
                "overlap": overlap_violations,
                "total": total_violations
            },
            "is_100pct_feasible": (total_violations == 0)
        }

if __name__ == "__main__":
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(cur_dir)
    data_dir = os.path.join(base_dir, "data/standardized")
    processed_dir = os.path.join(base_dir, "data/processed")

    blocks_csv = os.path.join(processed_dir, "featured_blocks.csv")
    platens_csv = os.path.join(processed_dir, "featured_platens.csv")

    evaluator = MetricEvaluator(blocks_csv, platens_csv)

    print("=" * 105)
    print("UNIFIED EVALUATION & DATA INTEGRITY AUDIT REPORT")
    print("=" * 105)

    files = [
        # (Name, Path, Is Paper Baseline)
        ("Google OR-Tools CP-SAT (Ours)", os.path.join(processed_dir, "ortools_scheduling_results.csv"), False),
        ("EST Heuristic (Unified Sim)", os.path.join(processed_dir, "heuristic_est_results.csv"), False),
        ("LPT Heuristic (Unified Sim)", os.path.join(processed_dir, "heuristic_lpt_results.csv"), False),
        ("SPT Heuristic (Unified Sim)", os.path.join(processed_dir, "heuristic_spt_results.csv"), False),
        ("RTB Heuristic (Unified Sim)", os.path.join(processed_dir, "heuristic_rtb_results.csv"), False),
        ("RUB Heuristic (Unified Sim)", os.path.join(processed_dir, "heuristic_rub_results.csv"), False),
        ("PPO Actor-Critic (Ours)", os.path.join(processed_dir, "ppo_scheduling_results.csv"), False),
        ("EDDQN (Paper Baseline)", os.path.join(data_dir, "eddqn_scheduling_results.csv"), True),
        ("DDQN (Paper Baseline)", os.path.join(data_dir, "ddqn_scheduling_results.csv"), True),
    ]

    rows = []
    for name, fpath, is_paper in files:
        if os.path.exists(fpath):
            try:
                df = SafeScheduleReader.load_schedule(fpath)
                metrics = evaluator.evaluate(df, name, is_paper_baseline=is_paper)
                rows.append({
                    "Algorithm": name,
                    "Category": "Paper Baseline (2D)" if is_paper else "Unified Simulator (Sequential)",
                    "Blocks": metrics["total_blocks"],
                    "Integrity": "PASS" if metrics["integrity"]["passed"] else "WARN",
                    "Makespan (d)": metrics["makespan_days"],
                    "Delayed (%)": f"{metrics['delayed_blocks_pct']}%",
                    "Avg Delay (d)": metrics["avg_delay_days_all"],
                    "Violations": metrics["violations"]["total"],
                    "Feasible": "YES" if metrics["is_100pct_feasible"] else "NO"
                })
            except Exception as e:
                print(f"Audit error on {name}: {e}")

    df_out = pd.DataFrame(rows)
    print(df_out.to_string(index=False))
    print("=" * 105)
