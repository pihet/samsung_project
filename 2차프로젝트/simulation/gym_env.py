# simulation/gym_env.py
"""
================================================================================
 [Simulation] 스마트 조선소 정반 배치 Gymnasium 표준 환경 래퍼 (Gym Environment)
================================================================================
"""

import os
import sys
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Any, Tuple, Optional

# simulator 임포트
cur_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(cur_dir)
from simulator import ShipyardPlatenSimulator

class ShipyardPlatenGymEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, data_dir: str = None, reward_version: str = "V2"):
        super(ShipyardPlatenGymEnv, self).__init__()
        self.simulator = ShipyardPlatenSimulator(data_dir=data_dir, reward_version=reward_version)
        self.num_platens = self.simulator.num_platens
        self.num_blocks = self.simulator.num_blocks

        self.action_space = spaces.Discrete(self.num_platens)
        obs_dim = len(self.simulator.get_observation())
        self.observation_space = spaces.Box(
            low=-10.0,
            high=10.0,
            shape=(obs_dim,),
            dtype=np.float32
        )

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            np.random.seed(seed)

        obs = self.simulator.reset()
        info = {
            "num_blocks": self.num_blocks,
            "num_platens": self.num_platens,
            "reward_version": self.simulator.reward_version
        }
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        next_obs, reward, terminated, info = self.simulator.step(int(action))
        truncated = False
        return next_obs, float(reward), terminated, truncated, info

    def render(self):
        curr = self.simulator.current_block_idx
        total = self.num_blocks
        reward = self.simulator.total_reward
        print(f" Step: {curr}/{total} | 누적보상: {reward:.2f}")

if __name__ == "__main__":
    env = ShipyardPlatenGymEnv()
    print(f" Gym Environment OK: Obs={env.observation_space.shape}, Act={env.action_space.n}")
