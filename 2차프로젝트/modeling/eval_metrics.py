# modeling/eval_metrics.py
"""
================================================================================
Comprehensive Unified Evaluation Suite for Shipyard Platen Scheduling
================================================================================
"""

import os
import sys
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)

from utils.paths import get_feature_path, get_schedule_path, STANDARDIZED_DIR

class SafeScheduleReader:
    STD_18_COLS = [
        'platen_name', 'platen_id', 'platen_length_m', 'platen_width_m', 'subcontractor_team',
        'ship_id', 'block_seq_id', 'block_id', 'block_length_m', 'block_width_m',
        'processing_time_days', 'block_output_value', 'planned_start_day', 'planned_end_day',
        'due_date_day', 'delay_days', 'early_days', 'standard_early_days'
    ]

    @staticmethod
    def load_schedule(filepath: str) -> pd.DataFrame:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Schedule file not found: {filepath}")

        df = pd.read_csv(filepath)
        cols_lower = [str(c).lower() for c in df.columns]

        has_start = any(k in cols_lower for k in ['start', 'planned_start', 'planned_start_day'])
        has_end = any(k in cols_lower for k in ['end', 'planned_end', 'planned_end_day'])

        # If it's the 18-column paper baseline format missing proper header
        if not (has_start and has_end) and df.shape[1] == 18:
            df.columns = SafeScheduleReader.STD_18_COLS
            return df

        if has_start and has_end:
            return df

        # Fallback headerless read
        if df.shape[1] >= 6:
            guesses = [
                "block_id", "platen_id", "planned_start_day", "planned_end_day", 
                "due_date_day", "delay_days", "processing_time_days", "lead_time_days", "is_feasible"
            ]
            df.columns = guesses[:df.shape[1]]
            return df

        return df


class MetricEvaluator:
    def __init__(self, blocks_path: Optional[str] = None, platens_path: Optional[str] = None):
        if blocks_path is None:
            blocks_path = get_feature_path("featured_blocks.csv")

        if platens_path is None:
            platens_path = get_feature_path("featured_platens.csv")

        self.df_blocks = pd.read_csv(blocks_path)
        self.df_platens = pd.read_csv(platens_path)

        if 'seq_id' not in self.df_blocks.columns:
            self.df_blocks['seq_id'] = np.arange(len(self.df_blocks))
        if 'seq_id' not in self.df_platens.columns:
            self.df_platens['seq_id'] = np.arange(len(self.df_platens))

        self.df_blocks_by_seq = self.df_blocks.set_index('seq_id')
        self.total_blocks_dataset = len(self.df_blocks)
        self.total_platens_dataset = len(self.df_platens)

        self._calibrate_calendar()

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

    def standardize_schedule(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        df = df_raw.copy()
        col_map = {
            'planned_start': 'planned_start_day',
            'start_day': 'planned_start_day',
            'start': 'planned_start_day',
            'planned_end': 'planned_end_day',
            'end_day': 'planned_end_day',
            'end': 'planned_end_day',
            'due_date': 'due_date_day',
            'due_day': 'due_date_day',
            'lead_time': 'processing_time_days',
            'lead_time_days': 'processing_time_days',
            'process_time': 'processing_time_days',
            'platen': 'platen_idx',
            'platen_id_assigned': 'platen_id'
        }
        df = df.rename(columns=col_map)

        if 'planned_start_day' not in df.columns:
            df['planned_start_day'] = 0
        if 'planned_end_day' not in df.columns:
            df['planned_end_day'] = 0

        if 'due_date_day' not in df.columns:
            if 'block_id' in df.columns and 'block_id' in self.df_blocks.columns:
                due_map = self.df_blocks.set_index('block_id')['due_day'].to_dict()
                df['due_date_day'] = df['block_id'].map(due_map).fillna(1000).astype(int)
            else:
                df['due_date_day'] = 1000

        if 'delay_days' not in df.columns:
            df['delay_days'] = np.maximum(0, df['planned_end_day'] - df['due_date_day'])

        if 'is_feasible' not in df.columns:
            if 'status' in df.columns:
                df['is_feasible'] = (df['status'] != 'INFEASIBLE_REJECTED')
            else:
                p_col = 'platen_idx' if 'platen_idx' in df.columns else 'platen_id'
                df['is_feasible'] = df[p_col].notnull() & (df['planned_start_day'] >= 0)

        return df

    def verify_integrity(self, df_sched: pd.DataFrame) -> Dict[str, Any]:
        total_rows = len(df_sched)
        passed = (total_rows == self.total_blocks_dataset)

        if 'seq_id' in df_sched.columns:
            unique_blocks = df_sched['seq_id'].nunique()
        elif 'block_id' in df_sched.columns and 'ship_id' in df_sched.columns:
            unique_blocks = df_sched.groupby(['ship_id', 'block_id']).ngroups
        else:
            unique_blocks = df_sched['block_id'].nunique() if 'block_id' in df_sched.columns else total_rows
        duplicates = total_rows - unique_blocks

        return {
            "passed": bool(passed and duplicates == 0),
            "expected_blocks": self.total_blocks_dataset,
            "actual_blocks": total_rows,
            "duplicate_blocks": duplicates,
            "message": "Integrity 100% Verified" if (passed and duplicates == 0) else f"Discrepancy: {total_rows} rows, {duplicates} duplicates vs {self.total_blocks_dataset} expected"
        }

    def evaluate(self, df_schedule: pd.DataFrame, algorithm_name: str = "Unknown", is_paper_baseline: bool = False) -> Dict[str, Any]:
        df = self.standardize_schedule(df_schedule)
        integrity = self.verify_integrity(df)

        df_valid = df[df['is_feasible']]
        total_valid = len(df_valid)
        total_infeasible = len(df) - total_valid

        # Physical Constraint Check
        violations = {"spatial": 0, "crane": 0, "overlap": 0, "total": 0}
        
        if not is_paper_baseline:
            for _, row in df_valid.iterrows():
                p_idx = int(row.get('platen_idx', -1))
                if 0 <= p_idx < self.total_platens_dataset:
                    p = self.df_platens.iloc[p_idx]
                    
                    if 'seq_id' in row and int(row['seq_id']) in self.df_blocks_by_seq.index:
                        b = self.df_blocks_by_seq.loc[int(row['seq_id'])]
                    else:
                        b_idx = int(row.get('seq_id', 0))
                        b = self.df_blocks.iloc[b_idx]

                    b_len = float(b['length_m']) if 'length_m' in b else float(b['block_length_m'])
                    b_wid = float(b['width_m']) if 'width_m' in b else float(b['block_width_m'])
                    b_max, b_min = max(b_len, b_wid), min(b_len, b_wid)

                    p_max = max(float(p['platen_length_m']), float(p['platen_width_m']))
                    p_min = min(float(p['platen_length_m']), float(p['platen_width_m']))

                    if b_max > p_max or b_min > p_min:
                        violations["spatial"] += 1

                    if float(b['weight_ton']) > float(p['crane_capacity_ton']):
                        violations["crane"] += 1

            violations["total"] = violations["spatial"] + violations["crane"]

        is_100pct_feasible = (violations["total"] == 0 and total_infeasible == 0)

        # Timeline and Delays
        if total_valid > 0:
            min_start = int(df_valid['planned_start_day'].min())
            max_end = int(df_valid['planned_end_day'].max())
            makespan = max(0, max_end - min_start)
        else:
            makespan = 0

        # Delay count and rate
        delayed_blocks_cnt = int((df_valid['delay_days'] > 0).sum())
        delayed_rate_pct = round((delayed_blocks_cnt / max(1, self.total_blocks_dataset)) * 100, 1)

        total_delay_days = int(df_valid['delay_days'].sum())
        avg_delay_all = round(total_delay_days / max(1, self.total_blocks_dataset), 1)
        avg_delay_delayed = round(total_delay_days / max(1, delayed_blocks_cnt), 1) if delayed_blocks_cnt > 0 else 0.0

        # Platen Utilization
        total_lead_time = float(df_valid['processing_time_days'].sum()) if 'processing_time_days' in df_valid else float(self.df_blocks['lead_time_days'].sum())
        denominator = float(self.total_platens_dataset * max(1, makespan))
        utilization_pct = round((total_lead_time / denominator) * 100, 1) if makespan > 0 else 0.0

        if is_paper_baseline:
            feasible_display = "Paper (2D Packing)"
        else:
            feasible_display = "YES (100%)" if is_100pct_feasible else f"NO ({violations['total']} Violations)"

        return {
            "algorithm": algorithm_name,
            "makespan_days": makespan,
            "delayed_blocks_count": delayed_blocks_cnt,
            "delayed_blocks_pct": delayed_rate_pct,
            "total_delay_days": total_delay_days,
            "avg_delay_days_all": avg_delay_all,
            "avg_delay_days_delayed": avg_delay_delayed,
            "utilization_pct": utilization_pct,
            "is_100pct_feasible": is_100pct_feasible,
            "feasible_display": feasible_display,
            "violations": violations,
            "integrity": integrity
        }


def run_evaluation_suite():
    evaluator = MetricEvaluator()

    def find_csv(filename: str) -> str:
        return get_schedule_path(filename)

    test_targets = [
        ("Google OR-Tools CP-SAT (Ours)", find_csv("ortools_scheduling_results.csv"), "Unified Simulator (Sequential)", False),
        ("EST Heuristic (Unified Sim)", find_csv("heuristic_est_results.csv"), "Unified Simulator (Sequential)", False),
        ("LPT Heuristic (Unified Sim)", find_csv("heuristic_lpt_results.csv"), "Unified Simulator (Sequential)", False),
        ("SPT Heuristic (Unified Sim)", find_csv("heuristic_spt_results.csv"), "Unified Simulator (Sequential)", False),
        ("PPO Actor-Critic (Ours)", find_csv("ppo_scheduling_results.csv"), "Unified Simulator (Sequential)", False),
        ("RTB Heuristic (Unified Sim)", find_csv("heuristic_rtb_results.csv"), "Unified Simulator (Sequential)", False),
        ("RUB Heuristic (Unified Sim)", find_csv("heuristic_rub_results.csv"), "Unified Simulator (Sequential)", False),
        ("EDDQN (Paper Baseline)", find_csv("eddqn_scheduling_results.csv"), "Paper Baseline (2D)", True),
        ("DDQN (Paper Baseline)", find_csv("ddqn_scheduling_results.csv"), "Paper Baseline (2D)", True),
        ("Action-Masked DQN (Ours)", find_csv("dqn_scheduling_results.csv"), "Unified Simulator (Sequential)", False)
    ]

    print("=" * 115)
    print("STRICT MULTI-ALGORITHM BENCHMARK & METRIC EVALUATION (ALL 872 BLOCKS)")
    print("=" * 115)

    results = []
    for name, path, sim_type, is_paper in test_targets:
        if not os.path.exists(path):
            continue
        df_sched = SafeScheduleReader.load_schedule(path)
        metrics = evaluator.evaluate(df_sched, name, is_paper_baseline=is_paper)

        results.append({
            "Algorithm": name,
            "Sim Type": sim_type,
            "Makespan (Days)": metrics["makespan_days"],
            "Delayed Blocks": f"{metrics['delayed_blocks_count']} ({metrics['delayed_blocks_pct']}%)",
            "Avg Delay (Days)": metrics["avg_delay_days_all"],
            "Platen Util (%)": f"{metrics['utilization_pct']}%",
            "Integrity (872/872)": "PASS" if metrics["integrity"]["passed"] else "FAIL",
            "Violations": metrics["violations"]["total"] if not is_paper else "-",
            "Feasible": metrics["feasible_display"]
        })

    df_out = pd.DataFrame(results)
    print(df_out.to_string(index=False))
    print("=" * 115)

if __name__ == "__main__":
    run_evaluation_suite()
