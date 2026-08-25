# modeling/train_ppo.py
"""
================================================================================
 [Modeling] PPO (Proximal Policy Optimization) Actor-Critic 강화학습 모델 훈련
================================================================================
- 핵심 기술:
  1. [Actor-Critic] 행동 정책(Actor)과 상태 가치 함수(Critic) 동시 학습
  2. [Action Masking] 66개 정반 중 제약조건을 만족하는 정반만 Softmax 확률 할당
  3. [Entropy Regularization] 특정 정반 쏠림을 방지하고 66개 정반을 균일하게 활용하도록 엔트로피 보너스 부여
  4. [GAE & Clipped Loss] 정책 업데이트 안정성을 극대화하여 조기 수렴 달성
================================================================================
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
from typing import Dict, Any, List, Tuple

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "simulation"))

from simulation.gym_env import ShipyardPlatenGymEnv

# =============================================================================
# 1. PPO Actor-Critic 신경망 아키텍처
# =============================================================================
class ActorCritic(nn.Module):
    def __init__(self, state_dim: int = 208, action_dim: int = 66):
        super(ActorCritic, self).__init__()
        # Actor: 정책 신경망 (State -> 66개 정반 Logits)
        self.actor = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.Tanh(),
            nn.Linear(256, 128),
            nn.Tanh(),
            nn.Linear(128, 64),
            nn.Tanh(),
            nn.Linear(64, action_dim)
        )
        # Critic: 가치 평가 신경망 (State -> V(s))
        self.critic = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.Tanh(),
            nn.Linear(256, 128),
            nn.Tanh(),
            nn.Linear(128, 1)
        )

    def forward(self, state: torch.Tensor, mask: torch.Tensor = None):
        logits = self.actor(state)
        if mask is not None:
            logits = torch.where(mask, logits, torch.tensor(-1e9, device=state.device))
        value = self.critic(state)
        return logits, value

    def get_action(self, state: torch.Tensor, mask: torch.Tensor = None) -> Tuple[int, torch.Tensor, torch.Tensor]:
        logits, value = self.forward(state, mask)
        dist = Categorical(logits=logits)
        action = dist.sample()
        log_prob = dist.log_prob(action)
        return action.item(), log_prob, value.squeeze(-1)

    def evaluate_actions(self, states: torch.Tensor, actions: torch.Tensor, masks: torch.Tensor):
        logits, values = self.forward(states, masks)
        dist = Categorical(logits=logits)
        log_probs = dist.log_prob(actions)
        entropy = dist.entropy().mean()
        return log_probs, values.squeeze(-1), entropy

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

# =============================================================================
# 2. PPO 훈련 파이프라인
# =============================================================================
def train_ppo(
    num_episodes: int = 30,
    lr: float = 3e-4,
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
    clip_eps: float = 0.2,
    ppo_epochs: int = 4,
    batch_size: int = 128
) -> Dict[str, Any]:
    print("=" * 80)
    print(" [PPO Actor-Critic Training] 엔트로피 규제 & 마스킹 기반 PPO 학습 시작")
    print("=" * 80)

    processed_dir = os.path.join(base_dir, "data/processed")
    env = ShipyardPlatenGymEnv(reward_version="V2")
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.n

    device = torch.device("cpu")
    model = ActorCritic(state_dim, action_dim).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    history_rewards = []
    history_makespans = []
    history_delays = []

    start_time = time.time()

    for ep in range(1, num_episodes + 1):
        obs, _ = env.reset()
        done = False

        states_buf = []
        actions_buf = []
        logprobs_buf = []
        rewards_buf = []
        values_buf = []
        masks_buf = []
        dones_buf = []

        while not done:
            mask = get_action_mask(env)
            s_tensor = torch.FloatTensor(obs).unsqueeze(0).to(device)
            m_tensor = torch.BoolTensor(mask).unsqueeze(0).to(device)

            with torch.no_grad():
                action, log_prob, value = model.get_action(s_tensor, m_tensor)

            next_obs, reward, term, trunc, _ = env.step(action)
            done = term or trunc

            states_buf.append(obs)
            actions_buf.append(action)
            logprobs_buf.append(log_prob.item())
            rewards_buf.append(reward)
            values_buf.append(value.item())
            masks_buf.append(mask)
            dones_buf.append(float(done))

            obs = next_obs

        # GAE (Generalized Advantage Estimation) 계산
        rewards = np.array(rewards_buf)
        values = np.array(values_buf)
        dones = np.array(dones_buf)
        advantages = np.zeros_like(rewards)
        last_gae = 0.0

        for t in reversed(range(len(rewards))):
            next_val = 0.0 if t == len(rewards) - 1 else values[t + 1]
            delta = rewards[t] + gamma * next_val * (1.0 - dones[t]) - values[t]
            advantages[t] = last_gae = delta + gamma * gae_lambda * (1.0 - dones[t]) * last_gae

        returns = advantages + values
        adv_norm = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # 텐서 변환
        t_states = torch.FloatTensor(np.array(states_buf)).to(device)
        t_actions = torch.LongTensor(actions_buf).to(device)
        t_old_logprobs = torch.FloatTensor(logprobs_buf).to(device)
        t_masks = torch.BoolTensor(np.array(masks_buf)).to(device)
        t_returns = torch.FloatTensor(returns).to(device)
        t_adv = torch.FloatTensor(adv_norm).to(device)

        # PPO 에폭 업데이트
        dataset_size = len(states_buf)
        indices = np.arange(dataset_size)

        for _ in range(ppo_epochs):
            np.random.shuffle(indices)
            for start in range(0, dataset_size, batch_size):
                end = start + batch_size
                b_idx = indices[start:end]

                logprobs, values, entropy = model.evaluate_actions(
                    t_states[b_idx], t_actions[b_idx], t_masks[b_idx]
                )

                # Ratio = pi_theta(a|s) / pi_old(a|s)
                ratios = torch.exp(logprobs - t_old_logprobs[b_idx])

                # Surrogate Loss
                surr1 = ratios * t_adv[b_idx]
                surr2 = torch.clamp(ratios, 1.0 - clip_eps, 1.0 + clip_eps) * t_adv[b_idx]
                actor_loss = -torch.min(surr1, surr2).mean()
                critic_loss = 0.5 * nn.MSELoss()(values, t_returns[b_idx])

                # Total Loss (엔트로피 보너스로 부하 균등 분산 촉진)
                loss = actor_loss + 0.5 * critic_loss - 0.01 * entropy

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 0.5)
                optimizer.step()

        metrics = env.simulator.get_summary_metrics()
        history_rewards.append(metrics['total_reward'])
        history_makespans.append(metrics['makespan'])
        history_delays.append(metrics['delayed_blocks'])

        if ep % 2 == 0 or ep == 1:
            print(f"    [Episode {ep:>2}/{num_episodes}] 누적보상: {metrics['total_reward']:>9.1f} | Makespan: {metrics['makespan']:>5}일 | 지연블록: {metrics['delayed_blocks']:>3}개 | 가동률: {metrics['utilization_pct']}%")

    train_duration = round(time.time() - start_time, 2)
    print(f"\n PPO Actor-Critic 훈련 완료 (소요 시간: {train_duration}초)")

    model_path = os.path.join(processed_dir, "ppo_model.pth")
    torch.save(model.state_dict(), model_path)
    print(f" PPO 모델 가중치 저장 완료: {model_path}")

    # =========================================================================
    # 3. [최종 결정론적 평가] 872개 블록 전수 시뮬레이션 평가
    # =========================================================================
    print("\n [Final Evaluation] 학습된 PPO 모델로 872개 블록 전수 배치 평가 중...")
    eval_env = ShipyardPlatenGymEnv(reward_version="V2")
    obs, _ = eval_env.reset()
    done = False
    model.eval()

    t_eval0 = time.time()
    with torch.no_grad():
        while not done:
            mask = get_action_mask(eval_env)
            s_tensor = torch.FloatTensor(obs).unsqueeze(0).to(device)
            m_tensor = torch.BoolTensor(mask).unsqueeze(0).to(device)
            logits, _ = model(s_tensor, m_tensor)
            action = logits.argmax(dim=1).item()
            obs, reward, term, trunc, _ = eval_env.step(action)
            done = term or trunc
    eval_time = round(time.time() - t_eval0, 3)

    final_metrics = eval_env.simulator.get_summary_metrics()
    eval_csv = os.path.join(processed_dir, "ppo_scheduling_results.csv")
    pd.DataFrame(eval_env.simulator.allocation_history).to_csv(eval_csv, index=False, encoding='utf-8')

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(history_rewards, 'b-o', label='Total Reward')
    ax1.set_xlabel('Episode')
    ax1.set_ylabel('Reward', color='b')
    ax1.tick_params(axis='y', labelcolor='b')

    ax2 = ax1.twinx()
    ax2.plot(history_makespans, 'g--s', label='Makespan (Days)')
    ax2.set_ylabel('Makespan (Days)', color='g')
    ax2.tick_params(axis='y', labelcolor='g')

    plt.title('PPO Actor-Critic Reinforcement Learning Training Curve', fontsize=12, fontweight='bold')
    fig.tight_layout()
    chart_path = os.path.join(processed_dir, "ppo_learning_curve.png")
    plt.savefig(chart_path, dpi=150)
    plt.close()

    print("\n" + "=" * 80)
    print(" [PPO Actor-Critic 심층 강화학습 최종 성적표]")
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
    train_ppo(num_episodes=30)
