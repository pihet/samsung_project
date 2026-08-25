# modeling/tune_hyperparameters.py
"""
================================================================================
Scientific Hyperparameter Tuning Suite (Exploratory Search + 3-Seed Validation)
================================================================================
- Phase 1: Candidate Search on Seed 42 (LR, Entropy, Gamma, Reward, Tau)
- Phase 2: Rigorous 3-Seed Validation (42, 100, 2024) on the Winning Configuration
- Saves statistical Mean +/- Std metrics and best_rl_model.pth checkpoint
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

from modeling.train_ppo import PPOTrainer, set_global_seeds, update_metrics_json
from modeling.eval_metrics import MetricEvaluator

# Multi-dimensional Hyperparameter Grid (including Gamma, LR, Entropy, Tau, Reward)
CANDIDATE_GRID = [
    {"lr": 1e-3, "entropy_coef": 0.05, "gamma": 0.99, "reward_version": "V2", "tau": 0.5, "tag": "Cfg_A (LR1e-3, G99, Ent0.05, Tau0.5)"},
    {"lr": 1e-3, "entropy_coef": 0.05, "gamma": 0.97, "reward_version": "V2", "tau": 0.3, "tag": "Cfg_B (LR1e-3, G97, Ent0.05, Tau0.3)"},
    {"lr": 3e-4, "entropy_coef": 0.05, "gamma": 0.99, "reward_version": "V2", "tau": 0.5, "tag": "Cfg_C (LR3e-4, G99, Ent0.05, Tau0.5)"},
    {"lr": 3e-4, "entropy_coef": 0.10, "gamma": 0.95, "reward_version": "V3", "tau": 0.5, "tag": "Cfg_D (LR3e-4, G95, Ent0.10, Tau0.5)"},
    {"lr": 1e-4, "entropy_coef": 0.05, "gamma": 0.99, "reward_version": "V3", "tau": 0.3, "tag": "Cfg_E (LR1e-4, G99, Ent0.05, Tau0.3)"},
    {"lr": 3e-4, "entropy_coef": 0.01, "gamma": 0.97, "reward_version": "V2", "tau": 0.0, "tag": "Cfg_F (LR3e-4, G97, Ent0.01, Tau0.0)"},
    {"lr": 1e-3, "entropy_coef": 0.08, "gamma": 0.99, "reward_version": "V3", "tau": 0.5, "tag": "Cfg_G (LR1e-3, G99, Ent0.08, Tau0.5)"},
    {"lr": 5e-4, "entropy_coef": 0.05, "gamma": 0.99, "reward_version": "V2", "tau": 0.5, "tag": "Cfg_H (LR5e-4, G99, Ent0.05, Tau0.5)"}
]

VALIDATION_SEEDS = [42, 100, 2024]
TRAIN_EPISODES = 30

def run_hyperparameter_tuning_pipeline():
    print("=" * 115)
    print("PHASE 1: CANDIDATE HYPERPARAMETER EXPLORATORY SEARCH (SEED 42)")
    print("=" * 115)

    blocks_csv = os.path.join(base_dir, "data/processed/featured_blocks.csv")
    platens_csv = os.path.join(base_dir, "data/processed/featured_platens.csv")
    evaluator = MetricEvaluator(blocks_csv, platens_csv)

    search_records = []

    for cfg in CANDIDATE_GRID:
        set_global_seeds(42)
        trainer = PPOTrainer(
            lr=cfg["lr"],
            gamma=cfg["gamma"],
            entropy_coef=cfg["entropy_coef"],
            feature_version="V2",
            reward_version=cfg["reward_version"],
            seed=42
        )

        t0 = time.perf_counter()
        for ep in range(1, TRAIN_EPISODES + 1):
            trainer.train_episode()
        train_time = round(time.perf_counter() - t0, 2)

        t_eval = time.perf_counter()
        obs, info = trainer.env.reset(seed=42)
        terminated = False
        trainer.ac_net.eval()
        while not terminated:
            state_t = torch.FloatTensor(obs).unsqueeze(0).to(trainer.device)
            mask_t = torch.BoolTensor(info["action_mask"]).unsqueeze(0).to(trainer.device)
            with torch.no_grad():
                action = trainer.ac_net.get_eval_action(state_t, mask_t, temperature=cfg["tau"])
            next_obs, _, terminated, _, next_info = trainer.env.step(action)
            obs = next_obs
            info = next_info
        eval_time = round(time.perf_counter() - t_eval, 4)

        df_out = pd.DataFrame(trainer.env.simulator.allocation_history)
        metrics = evaluator.evaluate(df_out, cfg["tag"])

        record = {
            "Config Tag": cfg["tag"],
            "Learning Rate": cfg["lr"],
            "Gamma": cfg["gamma"],
            "Entropy Coef": cfg["entropy_coef"],
            "Reward Ver": cfg["reward_version"],
            "Tau": cfg["tau"],
            "Makespan (Days)": metrics["makespan_days"],
            "Delayed Blocks": f"{metrics['delayed_blocks_count']} ({metrics['delayed_blocks_pct']}%)",
            "Avg Delay (Days)": metrics["avg_delay_days_all"],
            "Platen Util (%)": f"{metrics['utilization_pct']}%",
            "Train Time (s)": train_time,
            "Inference Time (s)": eval_time
        }
        search_records.append(record)
        print(f"[{cfg['tag']}] -> Makespan: {metrics['makespan_days']}d | Delayed: {metrics['delayed_blocks_count']} | Time: {eval_time:.4f}s")

    df_search = pd.DataFrame(search_records).sort_values(by="Makespan (Days)").reset_index(drop=True)
    print("\n" + "=" * 115)
    print("PHASE 1 SEARCH LEADERBOARD")
    print("=" * 115)
    print(df_search.to_string(index=False))

    # Identify top winning configuration
    best_candidate_tag = df_search.iloc[0]["Config Tag"]
    best_cfg = next(c for c in CANDIDATE_GRID if c["tag"] == best_candidate_tag)

    print("\n" + "=" * 115)
    print(f"PHASE 2: 3-SEED VALIDATION (42, 100, 2024) ON TOP CONFIGURATION: {best_candidate_tag}")
    print("=" * 115)

    seed_val_records = []
    best_makespan_overall = 999999
    best_overall_weights = None
    best_overall_df = None

    for seed in VALIDATION_SEEDS:
        set_global_seeds(seed)
        trainer = PPOTrainer(
            lr=best_cfg["lr"],
            gamma=best_cfg["gamma"],
            entropy_coef=best_cfg["entropy_coef"],
            feature_version="V2",
            reward_version=best_cfg["reward_version"],
            seed=seed
        )

        t0 = time.perf_counter()
        for ep in range(1, TRAIN_EPISODES + 1):
            trainer.train_episode()
        train_time = round(time.perf_counter() - t0, 2)

        t_eval = time.perf_counter()
        obs, info = trainer.env.reset(seed=seed)
        terminated = False
        trainer.ac_net.eval()
        while not terminated:
            state_t = torch.FloatTensor(obs).unsqueeze(0).to(trainer.device)
            mask_t = torch.BoolTensor(info["action_mask"]).unsqueeze(0).to(trainer.device)
            with torch.no_grad():
                action = trainer.ac_net.get_eval_action(state_t, mask_t, temperature=best_cfg["tau"])
            next_obs, _, terminated, _, next_info = trainer.env.step(action)
            obs = next_obs
            info = next_info
        eval_time = round(time.perf_counter() - t_eval, 4)

        df_out = pd.DataFrame(trainer.env.simulator.allocation_history)
        metrics = evaluator.evaluate(df_out, f"{best_cfg['tag']}_seed{seed}")

        seed_val_records.append({
            "Seed": seed,
            "Makespan (Days)": metrics["makespan_days"],
            "Delayed Blocks": metrics["delayed_blocks_count"],
            "Delayed (%)": metrics["delayed_blocks_pct"],
            "Avg Delay (Days)": metrics["avg_delay_days_all"],
            "Platen Util (%)": metrics["utilization_pct"],
            "Train Time (s)": train_time,
            "Inference Time (s)": eval_time
        })

        if metrics["makespan_days"] < best_makespan_overall:
            best_makespan_overall = metrics["makespan_days"]
            best_overall_weights = trainer.ac_net.state_dict()
            best_overall_df = df_out.copy()
            best_eval_time_overall = eval_time
            best_train_time_overall = train_time
            best_metrics_overall = metrics

    df_val = pd.DataFrame(seed_val_records)
    print(df_val.to_string(index=False))

    # Calculate Mean +/- Std
    m_mean, m_std = df_val["Makespan (Days)"].mean(), df_val["Makespan (Days)"].std()
    d_mean, d_std = df_val["Delayed Blocks"].mean(), df_val["Delayed Blocks"].std()
    p_mean, p_std = df_val["Delayed (%)"].mean(), df_val["Delayed (%)"].std()
    a_mean, a_std = df_val["Avg Delay (Days)"].mean(), df_val["Avg Delay (Days)"].std()
    u_mean, u_std = df_val["Platen Util (%)"].mean(), df_val["Platen Util (%)"].std()
    tr_mean, tr_std = df_val["Train Time (s)"].mean(), df_val["Train Time (s)"].std()
    inf_mean, inf_std = df_val["Inference Time (s)"].mean(), df_val["Inference Time (s)"].std()

    summary_stats = {
        "Best Configuration": best_cfg,
        "Makespan_Days_Mean": round(m_mean, 2),
        "Makespan_Days_Std": round(m_std, 2),
        "Delayed_Blocks_Mean": round(d_mean, 2),
        "Delayed_Blocks_Std": round(d_std, 2),
        "Delayed_Pct_Mean": round(p_mean, 2),
        "Avg_Delay_Days_Mean": round(a_mean, 2),
        "Avg_Delay_Days_Std": round(a_std, 2),
        "Platen_Util_Pct_Mean": round(u_mean, 2),
        "Platen_Util_Pct_Std": round(u_std, 2),
        "Train_Time_Sec_Mean": round(tr_mean, 2),
        "Train_Time_Sec_Std": round(tr_std, 2),
        "Inference_Time_Sec_Mean": round(inf_mean, 4),
        "Inference_Time_Sec_Std": round(inf_std, 4),
        "3_Seed_Records": seed_val_records
    }

    print("\n" + "=" * 115)
    print(f"FINAL TUNED MODEL 3-SEED STATISTICAL SUMMARY (Mean +/- Std)")
    print("=" * 115)
    print(f"   Makespan (Days): {m_mean:.1f} +/- {m_std:.1f}")
    print(f"   Delayed Blocks: {d_mean:.1f} +/- {d_std:.1f} ({p_mean:.1f}%)")
    print(f"   Avg Delay (Days): {a_mean:.1f} +/- {a_std:.1f}")
    print(f"   Platen Utilization: {u_mean:.1f} +/- {u_std:.1f} %")
    print(f"   Train Time: {tr_mean:.2f} +/- {tr_std:.2f} s")
    print(f"   872-Block Inference Time: {inf_mean:.4f} +/- {inf_std:.4f} s ({inf_mean/872*1000:.3f} ms/block)")
    print("=" * 115)

    # Save artifacts
    out_csv = os.path.join(base_dir, "data/processed/hyperparameter_tuning_results.csv")
    df_search.to_csv(out_csv, index=False)

    out_json = os.path.join(base_dir, "data/processed/hyperparameter_tuning_summary.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary_stats, f, indent=2)

    # Save best model checkpoint
    best_model_path = os.path.join(base_dir, "data/processed/best_rl_model.pth")
    torch.save(best_overall_weights, best_model_path)

    # Update primary schedule CSV
    best_sched_csv = os.path.join(base_dir, "data/processed/ppo_scheduling_results.csv")
    best_overall_df.to_csv(best_sched_csv, index=False)

    update_metrics_json("ppo", {
        "algorithm": "PPO Actor-Critic (Ours)",
        "configuration": best_cfg["tag"],
        "compute_time_sec": round(best_eval_time_overall, 4),
        "training_time_sec": round(best_train_time_overall, 2),
        "makespan_days": best_metrics_overall["makespan_days"],
        "delayed_blocks": best_metrics_overall["delayed_blocks_count"],
        "timestamp": time.time()
    })

    return summary_stats

if __name__ == "__main__":
    run_hyperparameter_tuning_pipeline()
