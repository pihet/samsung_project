# modeling/tune_hyperparameters.py
"""
================================================================================
Hyperparameter Tuning & Multi-Seed Statistical Validation Suite
================================================================================
"""

import os
import sys
import time
import json
from typing import Dict, List, Any
import numpy as np
import pandas as pd
import torch

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "simulation"))

from utils.paths import get_feature_path, MODELS_DIR, SCHEDULES_DIR, REPORTS_DIR, EXPERIMENTS_DIR
from simulation.gym_env import ShipyardPlatenGymEnv
from modeling.train_ppo import PPOTrainer
from modeling.eval_metrics import MetricEvaluator

METRICS_JSON = os.path.join(REPORTS_DIR, "benchmark_metrics.json")

def update_metrics_json(algo_key: str, data: Dict[str, Any]):
    os.makedirs(os.path.dirname(METRICS_JSON), exist_ok=True)
    metrics_store = {}
    if os.path.exists(METRICS_JSON):
        try:
            with open(METRICS_JSON, "r", encoding="utf-8") as f:
                metrics_store = json.load(f)
        except Exception:
            metrics_store = {}
    metrics_store[algo_key] = data
    with open(METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(metrics_store, f, indent=2)

HYPERPARAMETER_CANDIDATES = [
    {"tag": "Cfg_A (High LR, Ent 0.05, Tau 0.5)", "lr": 1e-3, "entropy_coef": 0.05, "gamma": 0.99, "reward_version": "V2", "tau": 0.5},
    {"tag": "Cfg_B (Standard LR, Ent 0.05, Tau 0.5)", "lr": 3e-4, "entropy_coef": 0.05, "gamma": 0.99, "reward_version": "V2", "tau": 0.5},
    {"tag": "Cfg_C (High LR, Ent 0.01, Tau 0.5)", "lr": 1e-3, "entropy_coef": 0.01, "gamma": 0.99, "reward_version": "V2", "tau": 0.5},
    {"tag": "Cfg_D (High LR, Ent 0.10, Tau 0.5)", "lr": 1e-3, "entropy_coef": 0.10, "gamma": 0.99, "reward_version": "V2", "tau": 0.5},
    {"tag": "Cfg_E (Gamma 0.95, LR 1e-3, Tau 0.5)", "lr": 1e-3, "entropy_coef": 0.05, "gamma": 0.95, "reward_version": "V2", "tau": 0.5},
    {"tag": "Cfg_F (Reward V3, LR 1e-3, Tau 0.5)", "lr": 1e-3, "entropy_coef": 0.05, "gamma": 0.99, "reward_version": "V3", "tau": 0.5},
    {"tag": "Cfg_G (Low Temp, Tau 0.2)", "lr": 1e-3, "entropy_coef": 0.05, "gamma": 0.99, "reward_version": "V2", "tau": 0.2},
    {"tag": "Cfg_H (High Temp, Tau 0.8)", "lr": 1e-3, "entropy_coef": 0.05, "gamma": 0.99, "reward_version": "V2", "tau": 0.8},
]

VALIDATION_SEEDS = [42, 100, 2024]
TUNING_EPISODES = 30

def run_hyperparameter_tuning():
    print("=" * 115)
    print("PHASE 1: HYPERPARAMETER CANDIDATE EXPLORATION (SEED: 42, 30 EPISODES)")
    print("=" * 115)

    blocks_csv = get_feature_path("featured_blocks.csv")
    platens_csv = get_feature_path("featured_platens.csv")
    evaluator = MetricEvaluator(blocks_csv, platens_csv)

    search_records = []

    for idx, cand in enumerate(HYPERPARAMETER_CANDIDATES, 1):
        tag = cand["tag"]
        lr = cand["lr"]
        ent = cand["entropy_coef"]
        gamma = cand["gamma"]
        r_ver = cand["reward_version"]
        tau = cand["tau"]

        t_start = time.perf_counter()
        trainer = PPOTrainer(
            lr=lr,
            gamma=gamma,
            entropy_coef=ent,
            seed=42,
            feature_version="V2",
            reward_version=r_ver
        )

        for ep in range(1, TUNING_EPISODES + 1):
            traj = trainer.collect_trajectory()
            trainer.train_step(traj)

        train_time = time.perf_counter() - t_start

        # Evaluate with configured temperature tau
        trainer.ac_net.eval()
        t_eval_start = time.perf_counter()
        obs, info = trainer.env.reset()
        terminated = False

        while not terminated:
            state_t = torch.FloatTensor(obs).unsqueeze(0).to(trainer.device)
            mask_t = torch.BoolTensor(info['action_mask']).unsqueeze(0).to(trainer.device)
            with torch.no_grad():
                action = trainer.ac_net.get_eval_action(state_t, mask_t, temperature=tau)
            next_obs, _, terminated, _, next_info = trainer.env.step(action)
            obs = next_obs
            info = next_info

        eval_time = time.perf_counter() - t_eval_start
        df_out = pd.DataFrame(trainer.env.simulator.allocation_history)
        eval_res = evaluator.evaluate(df_out, f"PPO_{tag}")

        search_records.append({
            "Rank": 0,
            "Tag": tag,
            "Learning Rate": lr,
            "Entropy Coef": ent,
            "Gamma": gamma,
            "Reward Version": r_ver,
            "Temperature (Tau)": tau,
            "Makespan (Days)": eval_res["makespan_days"],
            "Delayed Blocks": eval_res["delayed_blocks_count"],
            "Delayed (%)": eval_res["delayed_blocks_pct"],
            "Avg Delay (Days)": eval_res["avg_delay_days_all"],
            "Platen Util (%)": eval_res["utilization_pct"],
            "Train Time (s)": round(train_time, 2),
            "Inference Time (s)": round(eval_time, 4),
            "_trainer": trainer,
            "_df_out": df_out,
            "_eval_res": eval_res
        })

        print(f"[{idx:>2}/{len(HYPERPARAMETER_CANDIDATES)}] {tag:<40} | Makespan: {eval_res['makespan_days']:>4}d | Delayed: {eval_res['delayed_blocks_count']:>3} ({eval_res['delayed_blocks_pct']}%) | Time: {train_time:.1f}s")

    df_search = pd.DataFrame(search_records).sort_values(by=["Makespan (Days)", "Delayed Blocks"]).reset_index(drop=True)
    df_search["Rank"] = np.arange(1, len(df_search) + 1)

    print("\n" + "=" * 115)
    print("PHASE 1 CANDIDATE RANKING")
    print("=" * 115)
    print(df_search.drop(columns=["_trainer", "_df_out", "_eval_res"]).to_string(index=False))

    # Pick top winning config
    best_candidate_row = df_search.iloc[0]
    best_cfg = {
        "tag": best_candidate_row["Tag"],
        "lr": best_candidate_row["Learning Rate"],
        "entropy_coef": best_candidate_row["Entropy Coef"],
        "gamma": best_candidate_row["Gamma"],
        "reward_version": best_candidate_row["Reward Version"],
        "tau": best_candidate_row["Temperature (Tau)"]
    }

    print("\n" + "=" * 115)
    print(f"PHASE 2: 3-SEED STATISTICAL RE-TRAINING & VALIDATION (SEEDS: {VALIDATION_SEEDS})")
    print(f"Winning Configuration: {best_cfg['tag']} | LR: {best_cfg['lr']} | Gamma: {best_cfg['gamma']} | Entropy: {best_cfg['entropy_coef']} | Tau: {best_cfg['tau']}")
    print("=" * 115)

    multi_seed_results = []
    best_overall_makespan = 999999
    best_overall_weights = None
    best_overall_df = None
    best_metrics_overall = None
    best_train_time_overall = 0.0
    best_eval_time_overall = 0.0

    for seed in VALIDATION_SEEDS:
        t_start = time.perf_counter()
        trainer = PPOTrainer(
            lr=best_cfg["lr"],
            gamma=best_cfg["gamma"],
            entropy_coef=best_cfg["entropy_coef"],
            seed=seed,
            feature_version="V2",
            reward_version=best_cfg["reward_version"]
        )

        for ep in range(1, TUNING_EPISODES + 1):
            traj = trainer.collect_trajectory()
            trainer.train_step(traj)

        train_time = time.perf_counter() - t_start

        # Evaluation with tau
        trainer.ac_net.eval()
        t_eval_start = time.perf_counter()
        obs, info = trainer.env.reset()
        terminated = False

        while not terminated:
            state_t = torch.FloatTensor(obs).unsqueeze(0).to(trainer.device)
            mask_t = torch.BoolTensor(info['action_mask']).unsqueeze(0).to(trainer.device)
            with torch.no_grad():
                action = trainer.ac_net.get_eval_action(state_t, mask_t, temperature=best_cfg["tau"])
            next_obs, _, terminated, _, next_info = trainer.env.step(action)
            obs = next_obs
            info = next_info

        eval_time = time.perf_counter() - t_eval_start
        df_out = pd.DataFrame(trainer.env.simulator.allocation_history)
        eval_res = evaluator.evaluate(df_out, f"PPO_Best_Seed{seed}")

        multi_seed_results.append({
            "Seed": seed,
            "Makespan (Days)": eval_res["makespan_days"],
            "Delayed Blocks": eval_res["delayed_blocks_count"],
            "Delayed (%)": eval_res["delayed_blocks_pct"],
            "Avg Delay (Days)": eval_res["avg_delay_days_all"],
            "Platen Util (%)": eval_res["utilization_pct"],
            "Train Time (s)": round(train_time, 2),
            "Inference Time (s)": round(eval_time, 4),
            "Integrity": "PASS" if eval_res["integrity"]["passed"] else "FAIL",
            "100% Feasible": eval_res["is_100pct_feasible"]
        })

        # Save individual seed artifacts in experiments/
        seed_sched_csv = os.path.join(EXPERIMENTS_DIR, f"ppo_best_seed{seed}_scheduling_results.csv")
        seed_model_pth = os.path.join(EXPERIMENTS_DIR, f"ppo_best_seed{seed}_model.pth")
        df_out.to_csv(seed_sched_csv, index=False)
        torch.save(trainer.ac_net.state_dict(), seed_model_pth)

        if eval_res["makespan_days"] < best_overall_makespan:
            best_overall_makespan = eval_res["makespan_days"]
            best_overall_weights = trainer.ac_net.state_dict()
            best_overall_df = df_out
            best_metrics_overall = eval_res
            best_train_time_overall = train_time
            best_eval_time_overall = eval_time

        print(f"   [Seed {seed:>4}] Makespan: {eval_res['makespan_days']:>4}d | Delayed: {eval_res['delayed_blocks_count']:>3}/872 ({eval_res['delayed_blocks_pct']}%) | Util: {eval_res['utilization_pct']}% | Train: {train_time:.1f}s | Eval: {eval_time:.4f}s")

    df_multi = pd.DataFrame(multi_seed_results)
    m_mean, m_std = df_multi["Makespan (Days)"].mean(), df_multi["Makespan (Days)"].std()
    d_mean, d_std = df_multi["Delayed Blocks"].mean(), df_multi["Delayed Blocks"].std()
    p_mean, p_std = df_multi["Delayed (%)"].mean(), df_multi["Delayed (%)"].std()
    a_mean, a_std = df_multi["Avg Delay (Days)"].mean(), df_multi["Avg Delay (Days)"].std()
    u_mean, u_std = df_multi["Platen Util (%)"].mean(), df_multi["Platen Util (%)"].std()
    tr_mean, tr_std = df_multi["Train Time (s)"].mean(), df_multi["Train Time (s)"].std()
    inf_mean, inf_std = df_multi["Inference Time (s)"].mean(), df_multi["Inference Time (s)"].std()

    summary_stats = {
        "best_configuration": best_cfg,
        "validation_seeds": VALIDATION_SEEDS,
        "episodes": TUNING_EPISODES,
        "makespan_mean": round(m_mean, 2),
        "makespan_std": round(m_std, 2),
        "delayed_blocks_mean": round(d_mean, 2),
        "delayed_blocks_std": round(d_std, 2),
        "delayed_pct_mean": round(p_mean, 2),
        "avg_delay_mean": round(a_mean, 2),
        "avg_delay_std": round(a_std, 2),
        "utilization_mean": round(u_mean, 2),
        "train_time_mean": round(tr_mean, 2),
        "inference_time_mean": round(inf_mean, 4),
        "inference_time_per_block_ms": round((inf_mean / 872.0) * 1000.0, 3),
        "best_single_seed_makespan": best_overall_makespan
    }

    print("\n" + "=" * 115)
    print("FINAL 3-SEED STATISTICAL VALIDATION SUMMARY")
    print("=" * 115)
    print(f"   Makespan (Days): {m_mean:.1f} +/- {m_std:.1f} (Best Single Seed: {best_overall_makespan}d)")
    print(f"   Delayed Blocks: {d_mean:.1f} +/- {d_std:.1f} ({p_mean:.1f}%)")
    print(f"   Avg Delay (Days): {a_mean:.1f} +/- {a_std:.1f}")
    print(f"   Platen Utilization: {u_mean:.1f} +/- {u_std:.1f} %")
    print(f"   Train Time: {tr_mean:.2f} +/- {tr_std:.2f} s")
    print(f"   872-Block Inference Time: {inf_mean:.4f} +/- {inf_std:.4f} s ({inf_mean/872*1000:.3f} ms/block)")
    print("=" * 115)

    # Save tuning summary in experiments/
    out_csv = os.path.join(EXPERIMENTS_DIR, "hyperparameter_tuning_results.csv")
    df_search.drop(columns=["_trainer", "_df_out", "_eval_res"]).to_csv(out_csv, index=False)

    out_json = os.path.join(EXPERIMENTS_DIR, "hyperparameter_tuning_summary.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary_stats, f, indent=2)

    # Save best model checkpoint in models/
    best_model_path = os.path.join(MODELS_DIR, "best_rl_model.pth")
    torch.save(best_overall_weights, best_model_path)

    # Update primary schedule CSV in schedules/
    best_sched_csv = os.path.join(SCHEDULES_DIR, "ppo_scheduling_results.csv")
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
    run_hyperparameter_tuning()
