# simulation/gym_env.py
"""
================================================================================
Shipyard Platen Gymnasium Standard Environment Wrapper
================================================================================
"""

import os
import sys
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Any, Tuple, Optional

cur_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(cur_dir)
from simulator import ShipyardPlatenSimulator

class ShipyardPlatenGymEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self, 
        blocks_source=None, 
        platens_source=None, 
        reward_version: str = "V2",
        order_by: str = "est_urgency"
    ):
        super(ShipyardPlatenGymEnv, self).__init__()
        self.simulator = ShipyardPlatenSimulator(
            blocks_source=blocks_source,
            platens_source=platens_source,
            reward_version=reward_version,
            order_by=order_by
        )
        self.num_platens = self.simulator.num_platens
        self.num_blocks = self.simulator.num_blocks

        self.action_space = spaces.Discrete(self.num_platens)
        obs_dim = 10 + self.num_platens * 3
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
            "action_mask": self.simulator.get_action_mask(0)
        }
        return obs, info

    def get_action_mask(self, block_idx: Optional[int] = None) -> np.ndarray:
        return self.simulator.get_action_mask(block_idx)

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        rec = self.simulator.step(int(action))
        terminated = (self.simulator.current_block_idx >= self.num_blocks)
        truncated = False
        next_obs = self.simulator._get_state()
        mask = self.simulator.get_action_mask() if not terminated else np.ones(self.num_platens, dtype=bool)

        info = {
            "record": rec,
            "action_mask": mask,
            "current_block_idx": self.simulator.current_block_idx
        }
        return next_obs, float(rec["reward"]), terminated, truncated, info

if __name__ == "__main__":
    env = ShipyardPlatenGymEnv()
    obs, info = env.reset()
    print(f"Gym Environment Initialized: Obs Shape={obs.shape}, Action Dim={env.action_space.n}")
