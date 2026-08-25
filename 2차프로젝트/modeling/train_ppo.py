# modeling/train_ppo.py
"""
================================================================================
Action-Masked Proximal Policy Optimization (PPO) for Shipyard Platen Scheduling
================================================================================
- Features:
  * Fixed 208-dim state input
  * Single-variable Ablation Support (feature_version V1/V2, reward_version V1/V2/V3)
  * Seed protocol (42, 100, 2024) and time.perf_counter() measurement
  * Output CSV & benchmark_metrics.json integration
================================================================================
"""

import os
import sys
import time
import json
import random
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "simulation"))

from simulation.gym_env import ShipyardPlatenGymEnv
from modeling.eval_metrics import MetricEvaluator

METRICS_JSON = os.path.join(base_dir, "data/processed/benchmark_metrics.json")

def set_global_seeds(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

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

class MaskedActorCritic(nn.Module):
    def __init__(self, state_dim: int, action_dim: int):
        super(MaskedActorCritic, self).__init__()
        # Shared Feature Extractor
        self.shared = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU()
        )
        # Policy Head (Actor)
        self.actor = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )
        # Value Head (Critic)
        self.critic = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        feat = self.shared(state)
        logits = self.actor(feat)
        value = self.critic(feat)
        return logits, value

    def get_action(self, state: torch.Tensor, mask: torch.Tensor) -> Tuple[int, torch.Tensor, torch.Tensor, torch.Tensor]:
        logits, value = self.forward(state)
        masked_logits = torch.where(mask, logits, torch.tensor(-1e9, device=state.device))
        dist = Categorical(logits=masked_logits)
        action = dist.sample()
        return action.item(), dist.log_prob(action), dist.entropy(), value.squeeze(-1)

    def get_greedy_action(self, state: torch.Tensor, mask: torch.Tensor) -> int:
        logits, _ = self.forward(state)
        masked_logits = torch.where(mask, logits, torch.tensor(-1e9, device=state.device))
        return torch.argmax(masked_logits).item()

    def get_eval_action(self, state: torch.Tensor, mask: torch.Tensor, temperature: float = 0.5) -> int:
        logits, _ = self.forward(state)
        masked_logits = torch.where(mask, logits, torch.tensor(-1e9, device=state.device))
        if temperature > 0.0:
            probs = torch.softmax(masked_logits / temperature, dim=-1)
            dist = Categorical(probs=probs)
            return dist.sample().item()
        return torch.argmax(masked_logits).item()

class PPOTrainer:
    def __init__(
        self,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_ratio: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.05,
        feature_version: str = "V2",
        reward_version: str = "V2",
        seed: int = 42
    ):
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_ratio = clip_ratio
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.feature_version = feature_version
        self.reward_version = reward_version
        self.seed = seed
        set_global_seeds(self.seed)

        self.env = ShipyardPlatenGymEnv(feature_version=self.feature_version, reward_version=self.reward_version)
        self.state_dim = self.env.observation_space.shape[0]
        self.action_dim = self.env.action_space.n

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.ac_net = MaskedActorCritic(self.state_dim, self.action_dim).to(self.device)
        self.optimizer = optim.Adam(self.ac_net.parameters(), lr=lr)

    def train_episode(self) -> Tuple[float, int, int]:
        obs, info = self.env.reset(seed=self.seed)
        states, actions, log_probs, rewards, values, masks, dones = [], [], [], [], [], [], []

        terminated = False
        while not terminated:
            state_t = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
            mask = info["action_mask"]
            mask_t = torch.BoolTensor(mask).unsqueeze(0).to(self.device)

            with torch.no_grad():
                action, log_prob, _, val = self.ac_net.get_action(state_t, mask_t)

            next_obs, reward, terminated, _, next_info = self.env.step(action)

            states.append(obs)
            actions.append(action)
            log_probs.append(log_prob.item())
            rewards.append(reward)
            values.append(val.item())
            masks.append(mask)
            dones.append(terminated)

            obs = next_obs
            info = next_info

        # Generalized Advantage Estimation (GAE)
        returns = []
        advantages = []
        gae = 0
        values.append(0)

        for step in reversed(range(len(rewards))):
            delta = rewards[step] + self.gamma * values[step + 1] * (1 - dones[step]) - values[step]
            gae = delta + self.gamma * self.gae_lambda * (1 - dones[step]) * gae
            advantages.insert(0, gae)
            returns.insert(0, gae + values[step])

        # PPO Update
        states_t = torch.FloatTensor(np.array(states)).to(self.device)
        actions_t = torch.LongTensor(actions).to(self.device)
        old_log_probs_t = torch.FloatTensor(log_probs).to(self.device)
        returns_t = torch.FloatTensor(returns).to(self.device)
        advantages_t = torch.FloatTensor(advantages).to(self.device)
        advantages_t = (advantages_t - advantages_t.mean()) / (advantages_t.std() + 1e-8)
        masks_t = torch.BoolTensor(np.array(masks)).to(self.device)

        for _ in range(4):
            logits, curr_values = self.ac_net(states_t)
            masked_logits = torch.where(masks_t, logits, torch.tensor(-1e9, device=self.device))
            dist = Categorical(logits=masked_logits)
            new_log_probs = dist.log_prob(actions_t)
            entropy = dist.entropy().mean()

            ratios = torch.exp(new_log_probs - old_log_probs_t)
            surr1 = ratios * advantages_t
            surr2 = torch.clamp(ratios, 1.0 - self.clip_ratio, 1.0 + self.clip_ratio) * advantages_t

            actor_loss = -torch.min(surr1, surr2).mean()
            critic_loss = nn.MSELoss()(curr_values.squeeze(-1), returns_t)
            total_loss = actor_loss + self.value_coef * critic_loss - self.entropy_coef * entropy

            self.optimizer.zero_grad()
            total_loss.backward()
            nn.utils.clip_grad_norm_(self.ac_net.parameters(), 0.5)
            self.optimizer.step()

        metrics = self.env.simulator.get_summary_metrics()
        return metrics["total_reward"], metrics["makespan"], metrics["delayed_blocks"]

    def evaluate_and_save(self, training_time_sec: float = 0.0, save_name: str = "ppo", temperature: float = 0.5) -> Tuple[Dict[str, Any], float]:
        """Evaluation with exact time measurement."""
        t_eval_start = time.perf_counter()

        obs, info = self.env.reset(seed=self.seed)
        terminated = False
        self.ac_net.eval()

        while not terminated:
            state_t = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
            mask = info["action_mask"]
            mask_t = torch.BoolTensor(mask).unsqueeze(0).to(self.device)

            with torch.no_grad():
                action = self.ac_net.get_eval_action(state_t, mask_t, temperature=temperature)

            next_obs, _, terminated, _, next_info = self.env.step(action)
            obs = next_obs
            info = next_info

        eval_inference_time = round(time.perf_counter() - t_eval_start, 4)

        df_out = pd.DataFrame(self.env.simulator.allocation_history)
        out_csv = os.path.join(base_dir, f"data/processed/{save_name}_scheduling_results.csv")
        df_out.to_csv(out_csv, index=False)

        model_path = os.path.join(base_dir, f"data/processed/{save_name}_model.pth")
        torch.save(self.ac_net.state_dict(), model_path)

        blocks_csv = os.path.join(base_dir, "data/processed/featured_blocks.csv")
        platens_csv = os.path.join(base_dir, "data/processed/featured_platens.csv")
        evaluator = MetricEvaluator(blocks_csv, platens_csv)
        eval_res = evaluator.evaluate(df_out, "PPO Actor-Critic (Ours)")

        update_metrics_json(save_name, {
            "algorithm": "PPO Actor-Critic (Ours)",
            "feature_version": self.feature_version,
            "reward_version": self.reward_version,
            "seed": self.seed,
            "compute_time_sec": eval_inference_time,
            "training_time_sec": round(training_time_sec, 2),
            "makespan_days": eval_res["makespan_days"],
            "delayed_blocks": eval_res["delayed_blocks_count"],
            "timestamp": time.time()
        })

        return eval_res, eval_inference_time

def train_ppo_pipeline(episodes: int = 30, seed: int = 42, feature_version: str = "V2", reward_version: str = "V2"):
    print("=" * 80)
    print(f"Training Action-Masked PPO for {episodes} Episodes (Seed: {seed}, Feat: {feature_version}, Reward: {reward_version})")
    print("=" * 80)

    trainer = PPOTrainer(lr=3e-4, entropy_coef=0.05, feature_version=feature_version, reward_version=reward_version, seed=seed)
    t_train_start = time.perf_counter()

    for ep in range(1, episodes + 1):
        r, m, d = trainer.train_episode()
        if ep % 10 == 0 or ep == 1:
            print(f"   [Episode {ep:>3}/{episodes}] Reward: {r:>8.1f} | Makespan: {m:>4}d | Delayed: {d:>3}/872")

    training_time = time.perf_counter() - t_train_start
    print(f"\nPPO Training Complete ({training_time:.2f}s). Running Evaluation...")

    eval_res, eval_time = trainer.evaluate_and_save(training_time_sec=training_time, save_name="ppo", temperature=0.5)
    print("=" * 80)
    print("PPO Actor-Critic Final Evaluation Results")
    print("=" * 80)
    print(f"   Makespan: {eval_res['makespan_days']} Days")
    print(f"   Delayed Blocks: {eval_res['delayed_blocks_count']} / 872 ({eval_res['delayed_blocks_pct']}%)")
    print(f"   Average Delay: {eval_res['avg_delay_days_all']} Days")
    print(f"   Platen Utilization: {eval_res['utilization_pct']} %")
    print(f"   Integrity: {'PASS' if eval_res['integrity']['passed'] else 'FAIL'}")
    print(f"   Constraint Violations: {eval_res['violations']['total']}")
    print(f"   100% Feasible: {eval_res['is_100pct_feasible']}")
    print(f"   Inference Time: {eval_time:.4f}s (Logged to benchmark_metrics.json)")
    print("=" * 80)
    return eval_res

if __name__ == "__main__":
    train_ppo_pipeline(episodes=30, seed=42, feature_version="V2", reward_version="V2")
