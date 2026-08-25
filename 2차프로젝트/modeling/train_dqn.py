# modeling/train_dqn.py
"""
================================================================================
Action-Masked Deep Q-Network (DQN) for Shipyard Platen Scheduling
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

from utils.paths import get_feature_path, MODELS_DIR, SCHEDULES_DIR, REPORTS_DIR
from simulation.gym_env import ShipyardPlatenGymEnv
from modeling.eval_metrics import MetricEvaluator

METRICS_JSON = os.path.join(REPORTS_DIR, "benchmark_metrics.json")

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
    def __init__(self, state_dim: int = 208, action_dim: int = 66, hidden_dim: int = 256):
        super(MaskedQNetwork, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim)
        )

    def forward(self, state: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        q_values = self.net(state)
        if mask is not None:
            # Safe large negative value for invalid actions without float overflow
            q_values = torch.where(mask, q_values, torch.tensor(-1e4, device=q_values.device))
        return q_values

class ReplayBuffer:
    def __init__(self, capacity: int = 50000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, next_mask, done):
        self.buffer.append((state, action, reward, next_state, next_mask, done))

    def sample(self, batch_size: int):
        batch = random.sample(self.buffer, batch_size)
        state, action, reward, next_state, next_mask, done = zip(*batch)
        return (
            torch.FloatTensor(np.array(state)),
            torch.LongTensor(action),
            torch.FloatTensor(reward),
            torch.FloatTensor(np.array(next_state)),
            torch.BoolTensor(np.array(next_mask)),
            torch.FloatTensor(done)
        )

    def __len__(self):
        return len(self.buffer)

class DQNTrainer:
    def __init__(
        self,
        lr: float = 3e-4,
        gamma: float = 0.99,
        batch_size: int = 128,
        buffer_capacity: int = 50000,
        target_update_freq: int = 5,
        seed: int = 42
    ):
        set_global_seeds(seed)
        self.env = ShipyardPlatenGymEnv(feature_version="V2", reward_version="V2", order_by="est_urgency")
        self.state_dim = self.env.observation_space.shape[0]
        self.action_dim = self.env.action_space.n
        self.gamma = gamma
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.seed = seed

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.q_net = MaskedQNetwork(self.state_dim, self.action_dim).to(self.device)
        self.target_net = MaskedQNetwork(self.state_dim, self.action_dim).to(self.device)
        self.target_net.load_state_dict(self.q_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.q_net.parameters(), lr=lr)
        self.memory = ReplayBuffer(buffer_capacity)
        self.loss_fn = nn.SmoothL1Loss()

    def select_action(self, state: np.ndarray, mask: np.ndarray, epsilon: float = 0.1) -> int:
        valid_actions = np.where(mask)[0]
        if len(valid_actions) == 0:
            return 0  # Simulator will handle fallback safely

        if random.random() < epsilon:
            return int(random.choice(valid_actions))

        with torch.no_grad():
            s_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            m_tensor = torch.BoolTensor(mask).unsqueeze(0).to(self.device)
            q_values = self.q_net(s_tensor, m_tensor)
            return int(torch.argmax(q_values, dim=1).item())

    def update_model(self):
        if len(self.memory) < self.batch_size:
            return 0.0

        states, actions, rewards, next_states, next_masks, dones = self.memory.sample(self.batch_size)
        states = states.to(self.device)
        actions = actions.unsqueeze(1).to(self.device)
        rewards = rewards.unsqueeze(1).to(self.device)
        next_states = next_states.to(self.device)
        next_masks = next_masks.to(self.device)
        dones = dones.unsqueeze(1).to(self.device)

        # Current Q-values
        curr_q = self.q_net(states).gather(1, actions)

        # Double DQN / Target Q-values with Action Masking
        with torch.no_grad():
            next_q = self.target_net(next_states, next_masks)
            # Check if any next action is valid
            has_valid_next = next_masks.any(dim=1, keepdim=True)
            max_next_q, _ = torch.max(next_q, dim=1, keepdim=True)
            # If no valid actions in next state, treat as terminal Q=0
            max_next_q = torch.where(has_valid_next, max_next_q, torch.zeros_like(max_next_q))
            target_q = rewards + (1.0 - dones) * self.gamma * max_next_q

        loss = self.loss_fn(curr_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_net.parameters(), max_norm=1.0)
        self.optimizer.step()
        return loss.item()

    def train_episode(self, epsilon: float) -> Tuple[float, int, int]:
        obs, info = self.env.reset()
        total_reward = 0.0
        done = False

        while not done:
            mask = info['action_mask']
            action = self.select_action(obs, mask, epsilon)
            next_obs, reward, terminated, truncated, next_info = self.env.step(action)
            done = terminated or truncated

            next_mask = next_info.get('action_mask', np.ones(self.action_dim, dtype=bool))
            self.memory.push(obs, action, reward, next_obs, next_mask, float(done))

            obs = next_obs
            info = next_info
            total_reward += reward
            self.update_model()

        metrics = self.env.simulator.get_summary_metrics()
        return total_reward, metrics['makespan'], metrics['delayed_blocks']

    def evaluate_and_save(self, training_time_sec: float) -> Tuple[Dict[str, Any], float]:
        self.q_net.eval()
        t_eval_start = time.perf_counter()
        obs, info = self.env.reset()
        terminated = False

        while not terminated:
            mask = info['action_mask']
            valid_actions = np.where(mask)[0]
            if len(valid_actions) == 0:
                action = 0
            else:
                with torch.no_grad():
                    s_tensor = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
                    m_tensor = torch.BoolTensor(mask).unsqueeze(0).to(self.device)
                    q_vals = self.q_net(s_tensor, m_tensor)
                    action = int(torch.argmax(q_vals, dim=1).item())

            next_obs, _, terminated, _, next_info = self.env.step(action)
            obs = next_obs
            info = next_info

        eval_inference_time = round(time.perf_counter() - t_eval_start, 4)

        df_out = pd.DataFrame(self.env.simulator.allocation_history)
        out_csv = os.path.join(SCHEDULES_DIR, "dqn_scheduling_results.csv")
        df_out.to_csv(out_csv, index=False)

        model_path = os.path.join(MODELS_DIR, "dqn_model.pth")
        torch.save(self.q_net.state_dict(), model_path)

        blocks_csv = get_feature_path("featured_blocks.csv")
        platens_csv = get_feature_path("featured_platens.csv")
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
