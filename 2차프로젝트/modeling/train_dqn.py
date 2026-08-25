# modeling/train_dqn.py
"""
================================================================================
Action-Masked Deep Q-Network (DQN) for Shipyard Platen Scheduling
================================================================================
- Features:
  * Fixed 208-dim state input
  * Action-masked epsilon-greedy exploration & safe target Q estimation
  * Explicit rejection handling without -1e9 Q-value pollution
  * Seed protocol (42, 100, 2024) and time.perf_counter() measurement
  * Output CSV & benchmark_metrics.json integration
================================================================================
"""

import os
import sys
import time
import json
import random
from collections import deque
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

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

class MaskedQNetwork(nn.Module):
    def __init__(self, state_dim: int, action_dim: int):
        super(MaskedQNetwork, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state)

    def get_action(self, state: torch.Tensor, mask: torch.Tensor, epsilon: float = 0.0) -> int:
        valid_indices = torch.where(mask)[0]
        if len(valid_indices) == 0:
            return 0  # Infeasible block

        if random.random() < epsilon:
            idx = random.choice(valid_indices.tolist())
            return idx
        else:
            q_values = self.forward(state)
            masked_q = torch.where(mask, q_values, torch.tensor(-1e9, device=state.device))
            return torch.argmax(masked_q).item()

class ReplayBuffer:
    def __init__(self, capacity: int = 50000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done, next_mask):
        self.buffer.append((state, action, reward, next_state, done, next_mask))

    def sample(self, batch_size: int):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones, next_masks = zip(*batch)
        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones, dtype=np.float32),
            np.array(next_masks, dtype=bool)
        )

    def __len__(self):
        return len(self.buffer)

class DQNTrainer:
    def __init__(
        self,
        lr: float = 3e-4,
        gamma: float = 0.99,
        buffer_capacity: int = 50000,
        batch_size: int = 64,
        target_update_freq: int = 5,
        feature_version: str = "V2",
        reward_version: str = "V2",
        seed: int = 42
    ):
        self.gamma = gamma
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.seed = seed
        set_global_seeds(self.seed)

        self.env = ShipyardPlatenGymEnv(feature_version=feature_version, reward_version=reward_version)
        self.state_dim = self.env.observation_space.shape[0]
        self.action_dim = self.env.action_space.n

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.q_net = MaskedQNetwork(self.state_dim, self.action_dim).to(self.device)
        self.target_net = MaskedQNetwork(self.state_dim, self.action_dim).to(self.device)
        self.target_net.load_state_dict(self.q_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.q_net.parameters(), lr=lr)
        self.buffer = ReplayBuffer(capacity=buffer_capacity)

    def train_episode(self, epsilon: float) -> Tuple[float, int, int]:
        obs, info = self.env.reset(seed=self.seed)
        terminated = False
        total_loss = 0.0

        while not terminated:
            state_t = torch.FloatTensor(obs).to(self.device)
            mask_t = torch.BoolTensor(info["action_mask"]).to(self.device)

            action = self.q_net.get_action(state_t, mask_t, epsilon=epsilon)
            next_obs, reward, terminated, _, next_info = self.env.step(action)

            self.buffer.push(obs, action, reward, next_obs, terminated, next_info["action_mask"])

            obs = next_obs
            info = next_info

            # Gradient step
            if len(self.buffer) >= self.batch_size:
                b_states, b_actions, b_rewards, b_next_states, b_dones, b_next_masks = self.buffer.sample(self.batch_size)

                states_t = torch.FloatTensor(b_states).to(self.device)
                actions_t = torch.LongTensor(b_actions).unsqueeze(1).to(self.device)
                rewards_t = torch.FloatTensor(b_rewards).unsqueeze(1).to(self.device)
                next_states_t = torch.FloatTensor(b_next_states).to(self.device)
                dones_t = torch.FloatTensor(b_dones).unsqueeze(1).to(self.device)
                next_masks_t = torch.BoolTensor(b_next_masks).to(self.device)

                curr_q = self.q_net(states_t).gather(1, actions_t)

                with torch.no_grad():
                    next_q_all = self.target_net(next_states_t)
                    # Safe action-masked target estimation
                    masked_next_q = torch.where(next_masks_t, next_q_all, torch.tensor(-1e9, device=self.device))
                    max_next_q = torch.max(masked_next_q, dim=1, keepdim=True)[0]
                    # Replace -1e9 for all-False masks (terminal / infeasible) with 0.0
                    max_next_q = torch.where(max_next_q < -1e8, torch.tensor(0.0, device=self.device), max_next_q)
                    target_q = rewards_t + (1 - dones_t) * self.gamma * max_next_q

                loss = nn.MSELoss()(curr_q, target_q)
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.q_net.parameters(), 1.0)
                self.optimizer.step()
                total_loss += loss.item()

        metrics = self.env.simulator.get_summary_metrics()
        return metrics["total_reward"], metrics["makespan"], metrics["delayed_blocks"]

    def evaluate_and_save(self, training_time_sec: float = 0.0) -> Tuple[Dict[str, Any], float]:
        """Strict Greedy evaluation without exploration noise."""
        t_eval_start = time.perf_counter()
        obs, info = self.env.reset(seed=self.seed)
        terminated = False
        self.q_net.eval()

        while not terminated:
            state_t = torch.FloatTensor(obs).to(self.device)
            mask_t = torch.BoolTensor(info["action_mask"]).to(self.device)

            with torch.no_grad():
                action = self.q_net.get_action(state_t, mask_t, epsilon=0.0)

            next_obs, _, terminated, _, next_info = self.env.step(action)
            obs = next_obs
            info = next_info

        eval_inference_time = round(time.perf_counter() - t_eval_start, 4)

        df_out = pd.DataFrame(self.env.simulator.allocation_history)
        out_csv = os.path.join(base_dir, "data/processed/dqn_scheduling_results.csv")
        df_out.to_csv(out_csv, index=False)

        model_path = os.path.join(base_dir, "data/processed/dqn_model.pth")
        torch.save(self.q_net.state_dict(), model_path)

        blocks_csv = os.path.join(base_dir, "data/processed/featured_blocks.csv")
        platens_csv = os.path.join(base_dir, "data/processed/featured_platens.csv")
        evaluator = MetricEvaluator(blocks_csv, platens_csv)
        eval_res = evaluator.evaluate(df_out, "Action-Masked DQN (Ours)")

        update_metrics_json("dqn", {
            "algorithm": "Action-Masked DQN (Ours)",
            "compute_time_sec": eval_inference_time,
            "training_time_sec": round(training_time_sec, 2),
            "makespan_days": eval_res["makespan_days"],
            "delayed_blocks": eval_res["delayed_blocks_count"],
            "timestamp": time.time()
        })

        return eval_res, eval_inference_time

def run_dqn_training(episodes: int = 30, seed: int = 42):
    print("=" * 80)
    print(f"Training Action-Masked DQN for {episodes} Episodes (Seed: {seed})")
    print("=" * 80)

    trainer = DQNTrainer(lr=3e-4, seed=seed)
    t_train_start = time.perf_counter()

    eps_start = 1.0
    eps_end = 0.05
    eps_decay = (eps_start - eps_end) / max(1, episodes - 5)

    for ep in range(1, episodes + 1):
        eps = max(eps_end, eps_start - (ep - 1) * eps_decay)
        r, m, d = trainer.train_episode(epsilon=eps)

        if ep % trainer.target_update_freq == 0:
            trainer.target_net.load_state_dict(trainer.q_net.state_dict())

        if ep % 10 == 0 or ep == 1:
            print(f"   [Episode {ep:>3}/{episodes}] Eps: {eps:.2f} | Reward: {r:>8.1f} | Makespan: {m:>4}d | Delayed: {d:>3}/872")

    training_time = time.perf_counter() - t_train_start
    print(f"\nDQN Training Complete ({training_time:.2f}s). Running Strict Greedy Evaluation...")

    eval_res, eval_time = trainer.evaluate_and_save(training_time_sec=training_time)
    print("=" * 80)
    print("Action-Masked DQN Final Evaluation Results")
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
    run_dqn_training(episodes=30, seed=42)
