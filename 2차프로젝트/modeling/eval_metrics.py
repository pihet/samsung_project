# modeling/eval_metrics.py
"""
================================================================================
Unified Metric Evaluator & Safe Baseline CSV Reader
================================================================================
- Features:
  1. Safe CSV reader: Handles missing headers in raw EDDQN/Heuristic files without modifying raw data.
  2. Date Normalization: Handles Excel serial dates (base = 43,155) vs relative simulation days.
  3. Unique Key Tracking: Preserves `seq_id` (0..871) as the immutable primary key.
  4. 4-Constraint Verification: Spatial (with 90-deg rotation), Crane Capacity, EST Precedence, Non-overlapping.
  5. Standard Metrics: Makespan, Delayed Block Count/Pct, Total/Avg Delay, Platen Utilization, Violations.
================================================================================
"""

import os
import glob
from typing import Dict, Any, List, Optional, Tuple
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
    def load_schedule(filepath: str, df_blocks: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Schedule file not found: {filepath}")

        # 1. Header check
        df_sample = pd.read_csv(filepath, nrows=2)
        if 'planned_start_day' in df_sample.columns or 'planned_start' in df_sample.columns:
            # Standard modern format
            df = pd.read_csv(filepath)
            # Normalize column names if needed
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
    """Rigorous evaluation engine for 872 blocks x 66 platens scheduling."""
    
    def __init__(self, blocks_file: str, platens_file: str):
        self.df_blocks = pd.read_csv(blocks_file)
        self.df_platens = pd.read_csv(platens_file)
        
        # Ensure seq_id is in df_blocks
        if 'seq_id' not in self.df_blocks.columns:
            self.df_blocks['seq_id'] = np.arange(len(self.df_blocks))
            
        self.num_blocks = len(self.df_blocks)
        self.num_platens = len(self.df_platens)
        self.total_lead_time = float(self.df_blocks['lead_time_days'].sum() if 'lead_time_days' in self.df_blocks.columns else self.df_blocks['processing_time_days'].sum())

    def evaluate(self, df_sched: pd.DataFrame, algorithm_name: str = "Unknown") -> Dict[str, Any]:
        """Calculates exact KPI metrics and verifies 4 physical constraints."""
        total_rows = len(df_sched)
        makespan = int(df_sched['planned_end_day'].max() - df_sched['planned_start_day'].min())
        
        delayed_mask = df_sched['delay_days'] > 0
        delayed_count = int(delayed_mask.sum())
        delayed_pct = round((delayed_count / max(1, total_rows)) * 100, 2)
        total_delay = int(df_sched['delay_days'].sum())
        avg_delay_all = round(total_delay / max(1, total_rows), 2)
        avg_delay_delayed = round(total_delay / max(1, delayed_count), 2) if delayed_count > 0 else 0.0
        
        utilization_pct = round((self.total_lead_time / max(1, (self.num_platens * makespan))) * 100, 2)

        # Constraint Verifications
        spatial_violations = 0
        crane_violations = 0
        est_violations = 0
        overlap_violations = 0

        # Build platen lookup
        platen_dict = {}
        for _, p in self.df_platens.iterrows():
            p_id = str(p['platen_id'])
            platen_dict[p_id] = {
                'length': float(p['platen_length_m']),
                'width': float(p['platen_width_m']),
                'crane_cap': float(p['crane_capacity_ton'])
            }

        # Build block lookup by seq_id
        block_dict = {}
        for _, b in self.df_blocks.iterrows():
            s_id = int(b['seq_id'])
            est_val = int(b.get('est_day', 0))
            block_dict[s_id] = {
                'length': float(b.get('length_m', b.get('block_length_m', 0))),
                'width': float(b.get('width_m', b.get('block_width_m', 0))),
                'weight': float(b.get('weight_ton', 0)),
                'est_day': est_val
            }

        # Interval overlap tracking per platen
        platen_intervals: Dict[str, List[Tuple[int, int, int]]] = {}

        for _, row in df_sched.iterrows():
            s_id = int(row['seq_id'])
            p_id = str(row.get('platen_id', ''))
            start_d = int(row['planned_start_day'])
            end_d = int(row['planned_end_day'])

            # 1. EST Precedence check
            if s_id in block_dict:
                b_info = block_dict[s_id]
                if start_d < b_info['est_day']:
                    est_violations += 1

                # 2. Spatial & Crane check
                if p_id in platen_dict:
                    p_info = platen_dict[p_id]
                    b_max, b_min = max(b_info['length'], b_info['width']), min(b_info['length'], b_info['width'])
                    p_max, p_min = max(p_info['length'], p_info['width']), min(p_info['length'], p_info['width'])

                    if b_max > p_max or b_min > p_min:
                        spatial_violations += 1
                    if b_info['weight'] > p_info['crane_cap']:
                        crane_violations += 1

            # 3. Non-overlapping check
            if p_id not in platen_intervals:
                platen_intervals[p_id] = []
            platen_intervals[p_id].append((start_d, end_d, s_id))

        # Check intervals for overlaps
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
            "total_blocks": total_rows,
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
    if not os.path.exists(blocks_csv):
        blocks_csv = os.path.join(data_dir, "block_information.csv")
    platens_csv = os.path.join(processed_dir, "featured_platens.csv")
    if not os.path.exists(platens_csv):
        platens_csv = os.path.join(data_dir, "platen_information.csv")

    evaluator = MetricEvaluator(blocks_csv, platens_csv)

    print("=" * 90)
    print("Unified Metric Evaluation Report across All Baseline and Generated Files")
    print("=" * 90)

    # 1. Evaluate Research Baseline Files
    baseline_files = {
        "EDDQN (Paper Baseline)": os.path.join(data_dir, "eddqn_scheduling_results.csv"),
        "DDQN (Paper Baseline)": os.path.join(data_dir, "ddqn_scheduling_results.csv"),
        "EST Heuristic (Paper)": os.path.join(data_dir, "heuristic_est_results.csv"),
        "LPT Heuristic (Paper)": os.path.join(data_dir, "heuristic_lpt_results.csv"),
        "SPT Heuristic (Paper)": os.path.join(data_dir, "heuristic_spt_results.csv"),
        "RUB Heuristic (Paper)": os.path.join(data_dir, "heuristic_resource_utilization_results.csv"),
        "RTB Heuristic (Paper)": os.path.join(data_dir, "heuristic_response_time_results.csv"),
    }

    # 2. Evaluate Newly Generated Files
    generated_files = {
        "Google OR-Tools CP-SAT (Ours)": os.path.join(processed_dir, "ortools_scheduling_results.csv"),
        "Action-Masked DQN (Ours)": os.path.join(processed_dir, "dqn_scheduling_results.csv"),
        "PPO Actor-Critic (Ours)": os.path.join(processed_dir, "ppo_scheduling_results.csv")
    }

    results = []
    all_files = {**baseline_files, **generated_files}

    for name, fpath in all_files.items():
        if os.path.exists(fpath):
            try:
                df = SafeScheduleReader.load_schedule(fpath)
                metrics = evaluator.evaluate(df, name)
                results.append({
                    "Algorithm": name,
                    "Makespan (Days)": metrics["makespan_days"],
                    "Delayed Blocks": f"{metrics['delayed_blocks_count']} ({metrics['delayed_blocks_pct']}%)",
                    "Avg Delay (Days)": metrics["avg_delay_days_all"],
                    "Platen Util (%)": metrics["utilization_pct"],
                    "Violations": metrics["violations"]["total"],
                    "Feasible": "YES" if metrics["is_100pct_feasible"] else "NO"
                })
            except Exception as e:
                print(f"Error evaluating {name}: {e}")

    df_report = pd.DataFrame(results)
    print(df_report.to_string(index=False))
    print("=" * 90)
