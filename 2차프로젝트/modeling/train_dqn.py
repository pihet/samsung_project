# modeling/train_dqn.py
"""
================================================================================
 [Modeling] Action-Masked Double DQN (EDDQN) 강화학습 모델 훈련
================================================================================
"""

import os
import sys
import time
import random
from collections import deque
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.optim as optim

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "simulation"))

from simulation.gym_env import ShipyardPlatenGymEnv

class MaskedQNetwork(nn.Module):
    def __init__(self, state_dim: int = 208, action_dim: int = 66):
        super(MaskedQNetwork, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )

    def forward(self, x: torch.Tensor, mask: torch.Tensor = None) -> torch.Tensor:
        q_vals = self.net(x)
        if mask is not None:
            q_vals = torch.where(mask, q_vals, torch.tensor(-1e9, device=x.device))
        return q_vals

class ReplayBuffer:
    def __init__(self, capacity: int = 20000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done, next_mask):
        self.buffer.append((state, action, reward, next_state, done, next_mask))

    def sample(self, batch_size: int):
        states, actions, rewards, next_states, dones, next_masks = zip(*random.sample(self.buffer, batch_size))
        return (
            torch.FloatTensor(np.array(states)),
            torch.LongTensor(actions),
            torch.FloatTensor(rewards),
            torch.FloatTensor(np.array(next_states)),
            torch.FloatTensor(dones),
            torch.BoolTensor(np.array(next_masks))
        )

    def __len__(self):
        return len(self.buffer)

def get_action_mask(env: ShipyardPlatenGymEnv) -> np.ndarray:
    curr_b = env.simulator.current_block_idx
    if curr_b >= env.simulator.num_blocks:
        return np.ones(env.num_platens, dtype=bool)
    mask = np.zeros(env.num_platens, dtype=bool)
    for p in range(env.num_platens):
        feas, _ = env.simulator.check_feasibility(curr_b, p)
        if feas:
            mask[p] = True
    if not np.any(mask):
        mask[0] = True
    return mask

def train_masked_dqn(num_episodes: int = 25, batch_size: int = 64, lr: float = 1e-3):
    print("=" * 80)
    print(" [Action-Masked EDDQN Training] 제약조건 마스킹 기반 Double DQN 학습 시작")
    print("=" * 80)

    processed_dir = os.path.join(base_dir, "data/processed")
    env = ShipyardPlatenGymEnv(reward_version="V2")
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.n

    device = torch.device("cpu")
    q_net = MaskedQNetwork(state_dim, action_dim).to(device)
    target_net = MaskedQNetwork(state_dim, action_dim).to(device)
    target_net.load_state_dict(q_net.state_dict())
    target_net.eval()

    optimizer = optim.Adam(q_net.parameters(), lr=lr)
    loss_fn = nn.SmoothL1Loss()
    memory = ReplayBuffer(capacity=20000)

    epsilon_start = 1.0
    epsilon_end = 0.05
    total_steps_decay = num_episodes * 872 * 0.4

    history_rewards = []
    history_makespans = []
    history_delays = []

    global_step = 0
    start_time = time.time()

    for ep in range(1, num_episodes + 1):
        obs, _ = env.reset()
        ep_reward = 0.0
        done = False

        while not done:
            global_step += 1
            mask = get_action_mask(env)
            valid_actions = np.where(mask)[0]

            epsilon = max(epsilon_end, epsilon_start - (epsilon_start - epsilon_end) * (global_step / max(1, total_steps_decay)))

            if random.random() < epsilon:
                action = int(np.random.choice(valid_actions))
            else:
                with torch.no_grad():
                    s_tensor = torch.FloatTensor(obs).unsqueeze(0).to(device)
                    m_tensor = torch.BoolTensor(mask).unsqueeze(0).to(device)
                    q_values = q_net(s_tensor, m_tensor)
                    action = q_values.argmax(dim=1).item()

            next_obs, reward, term, trunc, _ = env.step(action)
            done = term or trunc
            next_mask = get_action_mask(env)

            memory.push(obs, action, reward, next_obs, float(done), next_mask)
            obs = next_obs
            ep_reward += reward

            if len(memory) >= 500:
                s_b, a_b, r_b, ns_b, d_b, nm_b = memory.sample(batch_size)
                q_eval = q_net(s_b).gather(1, a_b.unsqueeze(1)).squeeze(1)

                with torch.no_grad():
                    next_actions = q_net(ns_b, nm_b).argmax(dim=1, keepdim=True)
                    q_next = target_net(ns_b).gather(1, next_actions).squeeze(1)
                    q_target = r_b + (1 - d_b) * 0.99 * q_next

                loss = loss_fn(q_eval, q_target)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            if global_step % 500 == 0:
                target_net.load_state_dict(q_net.state_dict())

        metrics = env.simulator.get_summary_metrics()
        history_rewards.append(metrics['total_reward'])
        history_makespans.append(metrics['makespan'])
        history_delays.append(metrics['delayed_blocks'])

        if ep % 2 == 0 or ep == 1:
            print(f"    [Episode {ep:>2}/{num_episodes}] 누적보상: {metrics['total_reward']:>9.1f} | Makespan: {metrics['makespan']:>5}일 | 지연블록: {metrics['delayed_blocks']:>3}개 | Epsilon: {epsilon:.3f}")

    train_duration = round(time.time() - start_time, 2)
    print(f"\n Masked EDDQN 학습 완료 (소요 시간: {train_duration}초)")

    model_path = os.path.join(processed_dir, "masked_dqn_model.pth")
    torch.save(q_net.state_dict(), model_path)

    # 최종 평가
    eval_env = ShipyardPlatenGymEnv(reward_version="V2")
    obs, _ = eval_env.reset()
    done = False
    q_net.eval()

    t_eval0 = time.time()
    with torch.no_grad():
        while not done:
            mask = get_action_mask(eval_env)
            s_tensor = torch.FloatTensor(obs).unsqueeze(0).to(device)
            m_tensor = torch.BoolTensor(mask).unsqueeze(0).to(device)
            action = q_net(s_tensor, m_tensor).argmax(dim=1).item()
            obs, reward, term, trunc, _ = eval_env.step(action)
            done = term or trunc
    eval_time = round(time.time() - t_eval0, 3)

    final_metrics = eval_env.simulator.get_summary_metrics()
    eval_csv = os.path.join(processed_dir, "dqn_scheduling_results.csv")
    pd.DataFrame(eval_env.simulator.allocation_history).to_csv(eval_csv, index=False, encoding='utf-8')

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(history_rewards, 'b-o', label='Total Reward')
    ax1.set_xlabel('Episode')
    ax1.set_ylabel('Reward', color='b')
    ax1.tick_params(axis='y', labelcolor='b')

    ax2 = ax1.twinx()
    ax2.plot(history_makespans, 'r--s', label='Makespan (Days)')
    ax2.set_ylabel('Makespan (Days)', color='r')
    ax2.tick_params(axis='y', labelcolor='r')

    plt.title('Action-Masked Double DQN Training Curve', fontsize=12, fontweight='bold')
    fig.tight_layout()
    chart_path = os.path.join(processed_dir, "dqn_learning_curve.png")
    plt.savefig(chart_path, dpi=150)
    plt.close()

    print("\n" + "=" * 80)
    print(" [Action-Masked EDDQN 최종 성적표]")
    print("=" * 80)
    print(f"    총 소요 공기 (Makespan): {final_metrics['makespan']} 일")
    print(f"    납기 지연 블록 수: {final_metrics['delayed_blocks']} 개 / 872개 ({final_metrics['delayed_blocks']/872*100:.1f}%)")
    print(f"    평균 지연 일수: {final_metrics['avg_delay_days']} 일")
    print(f"    정반 평균 가동률: {final_metrics['utilization_pct']} %")
    print(f"    최종 누적 보상: {final_metrics['total_reward']}")
    print(f"    총 훈련 시간: {train_duration} 초 | 872개 전수 추론 시간: {eval_time} 초")
    print(f"    결과 CSV: {eval_csv}")
    print("=" * 80)

    return final_metrics

if __name__ == "__main__":
    train_masked_dqn(num_episodes=25)
