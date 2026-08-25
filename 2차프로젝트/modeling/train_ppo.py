# modeling/train_ppo.py
"""
================================================================================
Action-Masked Proximal Policy Optimization (PPO) for Shipyard Platen Scheduling
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
from torch.distributions.categorical import Categorical

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "simulation"))

from utils.paths import get_feature_path, MODELS_DIR, SCHEDULES_DIR, REPORTS_DIR, EXPERIMENTS_DIR
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

class MaskedActorCritic(nn.Module):
    def __init__(self, state_dim: int = 208, action_dim: int = 66, hidden_dim: int = 256):
        super(MaskedActorCritic, self).__init__()
        
        # Shared Feature Extractor (256 -> 128)
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.Tanh()
        )
        
        # Actor Head (128 -> 64 -> 66)
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.Tanh(),
            nn.Linear(hidden_dim // 4, action_dim)
        )
        
        # Critic Head (128 -> 64 -> 1)
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.Tanh(),
            nn.Linear(hidden_dim // 4, 1)
        )

    def forward(self, state: torch.Tensor, mask: Optional[torch.Tensor] = None):
        features = self.shared(state)
        logits = self.actor(features)
        value = self.critic(features)
        
        if mask is not None:
            # Mask invalid actions with a safe finite negative number to prevent NaN
            logits = torch.where(mask, logits, torch.tensor(-1e4, device=logits.device))
            
        return logits, value

    def get_action(self, state: torch.Tensor, mask: torch.Tensor):
        logits, value = self.forward(state, mask)
        dist = Categorical(logits=logits)
        action = dist.sample()
        return action.item(), dist.log_prob(action), dist.entropy().mean(), value

    def get_eval_action(self, state: torch.Tensor, mask: torch.Tensor, temperature: float = 0.5) -> int:
        logits, _ = self.forward(state, mask)
        if temperature <= 0.01:
            return int(torch.argmax(logits, dim=-1).item())
        else:
            scaled_logits = logits / max(0.01, temperature)
            dist = Categorical(logits=scaled_logits)
            return int(dist.sample().item())

    def evaluate_actions(self, states: torch.Tensor, masks: torch.Tensor, actions: torch.Tensor):
        features = self.shared(states)
        logits = self.actor(features)
        values = self.critic(features)
        
        logits = torch.where(masks, logits, torch.tensor(-1e4, device=logits.device))
        dist = Categorical(logits=logits)
        
        log_probs = dist.log_prob(actions)
        entropy = dist.entropy()
        return log_probs, values.squeeze(-1), entropy

class PPOTrainer:
    def __init__(
        self,
        lr: float = 1e-3,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_ratio: float = 0.2,
        entropy_coef: float = 0.05,
        value_coef: float = 0.5,
        batch_size: int = 128,
        update_epochs: int = 5,
        seed: int = 42,
        feature_version: str = "V2",
        reward_version: str = "V2"
    ):
        set_global_seeds(seed)
        self.feature_version = feature_version
        self.reward_version = reward_version
        self.seed = seed

        self.env = ShipyardPlatenGymEnv(
            feature_version=feature_version, 
            reward_version=reward_version, 
            order_by="est_urgency"
        )
        self.state_dim = self.env.observation_space.shape[0]
        self.action_dim = self.env.action_space.n

        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_ratio = clip_ratio
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef
        self.batch_size = batch_size
        self.update_epochs = update_epochs

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.ac_net = MaskedActorCritic(self.state_dim, self.action_dim).to(self.device)
        self.optimizer = optim.Adam(self.ac_net.parameters(), lr=lr, eps=1e-5)

    def collect_trajectory(self) -> Dict[str, torch.Tensor]:
        states, actions, rewards, masks, log_probs, values, dones = [], [], [], [], [], [], []
        obs, info = self.env.reset()
        done = False

        while not done:
            state_t = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
            mask_t = torch.BoolTensor(info['action_mask']).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                action, log_prob, _, val = self.ac_net.get_action(state_t, mask_t)

            next_obs, reward, terminated, truncated, next_info = self.env.step(action)
            done = terminated or truncated

            states.append(obs)
            actions.append(action)
            rewards.append(reward)
            masks.append(info['action_mask'])
            log_probs.append(log_prob.item())
            values.append(val.item())
            dones.append(done)

            obs = next_obs
            info = next_info

        # Compute GAE (Generalized Advantage Estimation)
        returns = []
        advantages = []
        gae = 0.0
        next_val = 0.0

        for t in reversed(range(len(rewards))):
            delta = rewards[t] + self.gamma * next_val * (1.0 - dones[t]) - values[t]
            gae = delta + self.gamma * self.gae_lambda * (1.0 - dones[t]) * gae
            advantages.insert(0, gae)
            returns.insert(0, gae + values[t])
            next_val = values[t]

        return {
            'states': torch.FloatTensor(np.array(states)).to(self.device),
            'actions': torch.LongTensor(actions).to(self.device),
            'masks': torch.BoolTensor(np.array(masks)).to(self.device),
            'old_log_probs': torch.FloatTensor(log_probs).to(self.device),
            'returns': torch.FloatTensor(returns).to(self.device),
            'advantages': torch.FloatTensor(advantages).to(self.device)
        }

    def train_step(self, trajectory: Dict[str, torch.Tensor]) -> Tuple[float, float, float]:
        states = trajectory['states']
        actions = trajectory['actions']
        masks = trajectory['masks']
        old_log_probs = trajectory['old_log_probs']
        returns = trajectory['returns']
        advantages = trajectory['advantages']

        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        dataset_size = len(states)

        for _ in range(self.update_epochs):
            indices = np.arange(dataset_size)
            np.random.shuffle(indices)

            for start in range(0, dataset_size, self.batch_size):
                end = start + self.batch_size
                batch_idx = indices[start:end]

                b_states = states[batch_idx]
                b_actions = actions[batch_idx]
                b_masks = masks[batch_idx]
                b_old_log_probs = old_log_probs[batch_idx]
                b_returns = returns[batch_idx]
                b_advantages = advantages[batch_idx]

                new_log_probs, new_values, entropy = self.ac_net.evaluate_actions(b_states, b_masks, b_actions)

                # Ratio for PPO clip
                ratios = torch.exp(new_log_probs - b_old_log_probs)
                surr1 = ratios * b_advantages
                surr2 = torch.clamp(ratios, 1.0 - self.clip_ratio, 1.0 + self.clip_ratio) * b_advantages
                actor_loss = -torch.min(surr1, surr2).mean()

                # Critic loss
                critic_loss = 0.5 * nn.MSELoss()(new_values, b_returns)
                entropy_loss = -entropy.mean()

                loss = actor_loss + self.value_coef * critic_loss + self.entropy_coef * entropy_loss

                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.ac_net.parameters(), max_norm=0.5)
                self.optimizer.step()

        return actor_loss.item(), critic_loss.item(), entropy_loss.item()

    def evaluate_and_save(self, save_name: str = "ppo", training_time_sec: float = 0.0) -> Tuple[Dict[str, Any], float]:
        self.ac_net.eval()
        t_eval_start = time.perf_counter()
        obs, info = self.env.reset()
        terminated = False

        while not terminated:
            state_t = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
            mask_t = torch.BoolTensor(info['action_mask']).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                action = self.ac_net.get_eval_action(state_t, mask_t, temperature=0.5)
                
            next_obs, _, terminated, _, next_info = self.env.step(action)
            obs = next_obs
            info = next_info

        eval_inference_time = round(time.perf_counter() - t_eval_start, 4)

        df_out = pd.DataFrame(self.env.simulator.allocation_history)
        
        # Decide output destination
        if save_name == "ppo":
            out_csv = os.path.join(SCHEDULES_DIR, f"{save_name}_scheduling_results.csv")
            model_path = os.path.join(MODELS_DIR, f"{save_name}_model.pth")
        else:
            out_csv = os.path.join(EXPERIMENTS_DIR, f"{save_name}_scheduling_results.csv")
            model_path = os.path.join(EXPERIMENTS_DIR, f"{save_name}_model.pth")

        df_out.to_csv(out_csv, index=False)
        torch.save(self.ac_net.state_dict(), model_path)

        blocks_csv = get_feature_path("featured_blocks.csv")
        platens_csv = get_feature_path("featured_platens.csv")
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

    trainer = PPOTrainer(
        lr=1e-3, 
        entropy_coef=0.05, 
        seed=seed, 
        feature_version=feature_version, 
        reward_version=reward_version
    )
    t_train_start = time.perf_counter()

    for ep in range(1, episodes + 1):
        trajectory = trainer.collect_trajectory()
        aloss, closs, eloss = trainer.train_step(trajectory)
        metrics = trainer.env.simulator.get_summary_metrics()

        if ep % 10 == 0 or ep == 1:
            print(f"   [Episode {ep:>3}/{episodes}] Reward: {metrics['total_reward']:>8.1f} | Makespan: {metrics['makespan']:>4}d | Delayed: {metrics['delayed_blocks']:>3}/872")

    training_time = time.perf_counter() - t_train_start
    print(f"\nPPO Training Complete ({training_time:.2f}s). Running Strict Policy Evaluation...")

    eval_res, eval_time = trainer.evaluate_and_save(save_name="ppo", training_time_sec=training_time)
    print("=" * 80)
    print("Action-Masked PPO Final Evaluation Results")
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
    train_ppo_pipeline(episodes=30, seed=42)
