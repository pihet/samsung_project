# modeling/train_best_model.py
"""
================================================================================
Train & Finalize Best V4 Hyperparameter Model across 3 Seeds (42, 100, 2024)
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

from utils.paths import get_feature_path, MODELS_DIR, SCHEDULES_DIR, REPORTS_DIR, EXPERIMENTS_DIR
from modeling.train_ppo import PPOTrainer, set_global_seeds, update_metrics_json
from modeling.eval_metrics import MetricEvaluator

SEEDS = [42, 100, 2024]
BEST_LR = 1e-3
BEST_ENTROPY = 0.05
BEST_REWARD = "V2"
BEST_TAU = 0.5

def train_best_model_suite():
    print("=" * 105)
    print("TRAINING FINAL BEST V4 MODEL (LR=1e-3, Ent=0.05, Rew=V2, Tau=0.5) ACROSS 3 SEEDS")
    print("=" * 105)

    blocks_csv = get_feature_path("featured_blocks.csv")
    platens_csv = get_feature_path("featured_platens.csv")
    evaluator = MetricEvaluator(blocks_csv, platens_csv)

    seed_records = []
    best_makespan = 999999
    best_df = None
    best_state_dict = None

    for seed in SEEDS:
        set_global_seeds(seed)
        trainer = PPOTrainer(
            lr=BEST_LR,
            entropy_coef=BEST_ENTROPY,
            feature_version="V2",
            reward_version=BEST_REWARD,
            seed=seed
        )

        t0 = time.perf_counter()
        for ep in range(1, 31):
            traj = trainer.collect_trajectory()
            trainer.train_step(traj)
        train_sec = time.perf_counter() - t0

        eval_res, eval_sec = trainer.evaluate_and_save(save_name=f"ppo_best_seed{seed}", training_time_sec=train_sec)

        seed_records.append({
            "Seed": seed,
            "Makespan (Days)": eval_res["makespan_days"],
            "Delayed Blocks": eval_res["delayed_blocks_count"],
            "Delayed (%)": eval_res["delayed_blocks_pct"],
            "Avg Delay (Days)": eval_res["avg_delay_days_all"],
            "Platen Util (%)": eval_res["utilization_pct"],
            "Train Time (s)": round(train_sec, 2),
            "Inference Time (s)": round(eval_sec, 4)
        })

        if eval_res["makespan_days"] < best_makespan:
            best_makespan = eval_res["makespan_days"]
            best_df = pd.DataFrame(trainer.env.simulator.allocation_history)
            best_state_dict = trainer.ac_net.state_dict()
            best_eval_res = eval_res
            best_eval_time = eval_sec
            best_train_time = train_sec

    df_seeds = pd.DataFrame(seed_records)
    print("\n" + "=" * 105)
    print("FINAL BEST V4 MODEL - 3-SEED RESULTS")
    print("=" * 105)
    print(df_seeds.to_string(index=False))

    # Save Best Model Artifacts in models/
    best_model_path = os.path.join(MODELS_DIR, "best_rl_model.pth")
    torch.save(best_state_dict, best_model_path)
    
    # Save as primary ppo schedule in schedules/
    best_sched_path = os.path.join(SCHEDULES_DIR, "ppo_scheduling_results.csv")
    best_df.to_csv(best_sched_path, index=False)

    update_metrics_json("ppo", {
        "algorithm": "PPO Actor-Critic (Ours)",
        "feature_version": "V2",
        "reward_version": BEST_REWARD,
        "compute_time_sec": round(best_eval_time, 4),
        "training_time_sec": round(best_train_time, 2),
        "makespan_days": best_eval_res["makespan_days"],
        "delayed_blocks": best_eval_res["delayed_blocks_count"],
        "timestamp": time.time()
    })

    print(f"\nSaved Best Model ({best_makespan} Days) to: {best_model_path}")
    print(f"Updated primary schedule CSV: {best_sched_path}")
    print("=" * 105)

if __name__ == "__main__":
    train_best_model_suite()
