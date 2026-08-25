# simulation/gym_env.py
"""
================================================================================
Shipyard Platen Gymnasium Environment
================================================================================
"""

import os
import sys
from typing import Dict, Any, Tuple, Optional
import numpy as np
import gymnasium as gym
from gymnasium import spaces

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)

from simulation.simulator import ShipyardPlatenSimulator

class ShipyardPlatenGymEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        blocks_source: Optional[str] = None,
        platens_source: Optional[str] = None,
        feature_version: str = "V2",
        reward_version: str = "V2",
        order_by: str = "est_urgency"
    ):
        super().__init__()
        self.simulator = ShipyardPlatenSimulator(
            blocks_source=blocks_source,
            platens_source=platens_source,
            feature_version=feature_version,
            reward_version=reward_version,
            order_by=order_by
        )

        self.num_platens = self.simulator.num_platens
        self.num_blocks = self.simulator.num_blocks

        self.action_space = spaces.Discrete(self.num_platens)
        # Fixed 208 dimensions: 10 block features + 66 * 3 platen features
        state_dim = 10 + self.num_platens * 3
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(state_dim,), dtype=np.float32
        )

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        obs = self.simulator.reset()
        action_mask = self.simulator.get_action_mask()
        info = {
            "action_mask": action_mask,
            "block_idx": self.simulator.current_block_idx,
            "num_blocks": self.num_blocks
        }
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        record = self.simulator.step(action)
        reward = record["reward"]
        terminated = (self.simulator.current_block_idx >= self.num_blocks)
        truncated = False

        obs = self.simulator._get_state() if not terminated else np.zeros(self.observation_space.shape, dtype=np.float32)
        action_mask = self.simulator.get_action_mask() if not terminated else np.ones(self.num_platens, dtype=bool)

        info = {
            "record": record,
            "action_mask": action_mask,
            "is_feasible": record["is_feasible"],
            "requested_feasible": record["requested_feasible"],
            "status": record.get("status", "ALLOCATED"),
            "delayed_blocks": (self.simulator.platen_available_days > 0).sum()
        }

        return obs, reward, terminated, truncated, info

    def render(self):
        metrics = self.simulator.get_summary_metrics()
        print(f"Step: {self.simulator.step_count}/{self.num_blocks} | Makespan: {metrics.get('makespan', 0)}d | Delayed: {metrics.get('delayed_blocks', 0)}")
