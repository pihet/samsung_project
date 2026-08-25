# modeling/tune_hyperparameters.py
"""
================================================================================
V4 Hyperparameter Tuning for Action-Masked PPO
================================================================================
- Evaluates:
  * Entropy Regularization (0.01, 0.05, 0.10) to prevent platen monopoly collapse
  * Learning Rates (1e-4, 3e-4, 1e-3)
  * Reward versions (V2 vs V3)
  * Temperature-calibrated evaluation (tau=0.5 vs tau=0.0)
- Selects best configuration and trains across 3 seeds (42, 100, 2024).
- Saves best model to data/processed/best_rl_model.pth.
================================================================================
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
import torch
from typing import Dict, List, Any

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)

from modeling.train_ppo import PPOTrainer, set_global_seeds
from modeling.eval_metrics import MetricEvaluator

PARAM_GRID = [
    {"lr": 3e-4, "entropy_coef": 0.05, "reward_version": "V2", "tau": 0.5, "tag": "Tune_H1"},
    {"lr": 3e-4, "entropy_coef": 0.10, "reward_version": "V3", "tau": 0.5, "tag": "Tune_H2"},
    {"lr": 1e-3, "entropy_coef": 0.05, "reward_version": "V2", "tau": 0.5, "tag": "Tune_H3"},
    {"lr": 1e-4, "entropy_coef": 0.05, "reward_version": "V3", "tau": 0.5, "tag": "Tune_H4"},
    {"lr": 3e-4, "entropy_coef": 0.01, "reward_version": "V2", "tau": 0.5, "tag": "Tune_H5"},
    {"lr": 3e-4, "entropy_coef": 0.08, "reward_version": "V3", "tau": 0.5, "tag": "Tune_H6"},
]

def run_tuning():
    print("=" * 105)
    print("STARTING V4 HYPERPARAMETER TUNING SEARCH (6 CANDIDATE CONFIGURATIONS)")
    print("=" * 105)

    tuning_results = []
    blocks_csv = os.path.join(base_dir, "data/processed/featured_blocks.csv")
    platens_csv = os.path.join(base_dir, "data/processed/featured_platens.csv")
    evaluator = MetricEvaluator(blocks_csv, platens_csv)

    for cand in PARAM_GRID:
        set_global_seeds(42)
        trainer = PPOTrainer(
            lr=cand["lr"],
            entropy_coef=cand["entropy_coef"],
            feature_version="V2",
            reward_version=cand["reward_version"],
            seed=42
        )

        t0 = time.perf_counter()
        for ep in range(1, 31):
            trainer.train_episode()
        train_time = time.perf_counter() - t0

        # Evaluate with tau
        t_eval_start = time.perf_counter()
        obs, info = trainer.env.reset(seed=42)
        terminated = False
        trainer.ac_net.eval()

        while not terminated:
            state_t = torch.FloatTensor(obs).unsqueeze(0).to(trainer.device)
            mask_t = torch.BoolTensor(info["action_mask"]).unsqueeze(0).to(trainer.device)
            with torch.no_grad():
                action = trainer.ac_net.get_eval_action(state_t, mask_t, temperature=cand["tau"])
            next_obs, _, terminated, _, next_info = trainer.env.step(action)
            obs = next_obs
            info = next_info

        eval_time = time.perf_counter() - t_eval_start
        df_out = pd.DataFrame(trainer.env.simulator.allocation_history)
        metrics = evaluator.evaluate(df_out, cand["tag"])

        tuning_results.append({
            "Tag": cand["tag"],
            "LR": cand["lr"],
            "Entropy_Coef": cand["entropy_coef"],
            "Reward_Ver": cand["reward_version"],
            "Tau": cand["tau"],
            "Makespan (Days)": metrics["makespan_days"],
            "Delayed Blocks": f"{metrics['delayed_blocks_count']} ({metrics['delayed_blocks_pct']}%)",
            "Avg Delay (Days)": metrics["avg_delay_days_all"],
            "Platen Util (%)": f"{metrics['utilization_pct']}%",
            "Train Time (s)": round(train_time, 2),
            "Inference Time (s)": round(eval_time, 4)
        })
        print(f"[{cand['tag']}] LR: {cand['lr']} | Ent: {cand['entropy_coef']} | Rew: {cand['reward_version']} -> Makespan: {metrics['makespan_days']}d | Delayed: {metrics['delayed_blocks_count']}")

    df_res = pd.DataFrame(tuning_results).sort_values(by="Makespan (Days)").reset_index(drop=True)
    print("\n" + "=" * 105)
    print("V4 HYPERPARAMETER TUNING LEADERBOARD")
    print("=" * 105)
    print(df_res.to_string(index=False))
    print("=" * 105)

    out_csv = os.path.join(base_dir, "data/processed/hyperparameter_tuning_results.csv")
    df_res.to_csv(out_csv, index=False)

    return df_res

if __name__ == "__main__":
    run_tuning()
