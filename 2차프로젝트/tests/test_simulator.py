# tests/test_simulator.py
"""
================================================================================
Unit Tests for Shipyard Platen Simulator (Toy 3 Platens x 5 Blocks)
================================================================================
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd

cur_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(cur_dir)
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "simulation"))

from simulation.simulator import ShipyardPlatenSimulator

class TestShipyardSimulator(unittest.TestCase):
    def setUp(self):
        # 3 Platens (Small, Medium, Large/Heavy)
        self.df_platens = pd.DataFrame([
            {"seq_id": 0, "platen_id": "P_SMALL", "platen_name": "Small Platen", "platen_length_m": 15.0, "platen_width_m": 15.0, "platen_area_m2": 225.0, "crane_capacity_ton": 100.0, "primary_area": "Yard-A"},
            {"seq_id": 1, "platen_id": "P_MED", "platen_name": "Med Platen", "platen_length_m": 25.0, "platen_width_m": 20.0, "platen_area_m2": 500.0, "crane_capacity_ton": 150.0, "primary_area": "Yard-B"},
            {"seq_id": 2, "platen_id": "P_LARGE", "platen_name": "Large Platen", "platen_length_m": 35.0, "platen_width_m": 25.0, "platen_area_m2": 875.0, "crane_capacity_ton": 250.0, "primary_area": "Yard-C"}
        ])

        # 5 Blocks
        self.df_blocks = pd.DataFrame([
            {"seq_id": 0, "block_id": "B0", "ship_id": "S1", "length_m": 10.0, "width_m": 10.0, "weight_ton": 50.0, "lead_time_days": 10, "earliest_start_date": "2018-02-24", "due_date": "2018-03-26", "est_day": 0, "due_day": 30, "slack_days": 20, "urgency_ratio": 0.33, "block_type": "FLAT", "cluster_id": 0},
            {"seq_id": 1, "block_id": "B1", "ship_id": "S1", "length_m": 20.0, "width_m": 15.0, "weight_ton": 120.0, "lead_time_days": 15, "earliest_start_date": "2018-03-01", "due_date": "2018-04-10", "est_day": 5, "due_day": 45, "slack_days": 25, "urgency_ratio": 0.375, "block_type": "FLAT", "cluster_id": 1},
            {"seq_id": 2, "block_id": "B2", "ship_id": "S1", "length_m": 18.0, "width_m": 18.0, "weight_ton": 220.0, "lead_time_days": 20, "earliest_start_date": "2018-02-24", "due_date": "2018-04-15", "est_day": 0, "due_day": 50, "slack_days": 30, "urgency_ratio": 0.40, "block_type": "FLAT", "cluster_id": 2},
            {"seq_id": 3, "block_id": "B3", "ship_id": "S1", "length_m": 22.0, "width_m": 12.0, "weight_ton": 80.0, "lead_time_days": 10, "earliest_start_date": "2018-03-06", "due_date": "2018-04-05", "est_day": 10, "due_day": 40, "slack_days": 20, "urgency_ratio": 0.33, "block_type": "FLAT", "cluster_id": 3},
            {"seq_id": 4, "block_id": "B4", "ship_id": "S1", "length_m": 40.0, "width_m": 30.0, "weight_ton": 300.0, "lead_time_days": 30, "earliest_start_date": "2018-02-24", "due_date": "2018-05-25", "est_day": 0, "due_day": 90, "slack_days": 60, "urgency_ratio": 0.33, "block_type": "FLAT", "cluster_id": 2}
        ])

        self.toy_blocks_file = "/tmp/toy_blocks.csv"
        self.toy_platens_file = "/tmp/toy_platens.csv"
        self.df_blocks.to_csv(self.toy_blocks_file, index=False)
        self.df_platens.to_csv(self.toy_platens_file, index=False)

        # Initialize simulator with raw order for deterministic unit testing
        self.sim = ShipyardPlatenSimulator(self.toy_blocks_file, self.toy_platens_file, order_by="raw")

    def test_spatial_constraint(self):
        """Test that B0 fits in all platens, but B1 does not fit in P_SMALL."""
        feas_0_p0, _ = self.sim.check_feasibility(0, 0)
        feas_1_p0, _ = self.sim.check_feasibility(1, 0) # B1 (20x15) in P_SMALL (15x15)
        feas_1_p1, _ = self.sim.check_feasibility(1, 1) # B1 (20x15) in P_MED (25x20)

        self.assertTrue(feas_0_p0, "B0 should fit in P_SMALL")
        self.assertFalse(feas_1_p0, "B1 should NOT fit in P_SMALL due to spatial limit")
        self.assertTrue(feas_1_p1, "B1 should fit in P_MED")

    def test_crane_capacity_constraint(self):
        """Test that heavy block B2 (220T) only fits in P_LARGE (250T crane), not P_MED (150T crane)."""
        feas_2_p1, _ = self.sim.check_feasibility(2, 1) # 220T in 150T
        feas_2_p2, _ = self.sim.check_feasibility(2, 2) # 220T in 250T

        self.assertFalse(feas_2_p1, "B2 (220T) should be rejected by P_MED (150T crane)")
        self.assertTrue(feas_2_p2, "B2 (220T) should be accepted by P_LARGE (250T crane)")

    def test_rotation_allowance(self):
        """Test that B3 (22m x 12m) fits in P_MED (25m x 20m) via rotation."""
        feas_3_p1, _ = self.sim.check_feasibility(3, 1)
        self.assertTrue(feas_3_p1, "B3 (22m x 12m) must fit in P_MED (25m x 20m)")

    def test_sequential_non_overlapping_schedule(self):
        """Test that placing B0 then B1 on the same platen updates available day strictly without overlap."""
        self.sim.reset()
        # Allocate B0 (duration 10, EST 0) to P_LARGE
        res_0 = self.sim.step(2)
        self.assertEqual(res_0["planned_start_day"], 0)
        self.assertEqual(res_0["planned_end_day"], 10)
        self.assertEqual(self.sim.platen_available_days[2], 10)

        # Allocate B1 (duration 15, EST 5) to P_LARGE (platen free at 10)
        res_1 = self.sim.step(2)
        self.assertEqual(res_1["planned_start_day"], 10, "B1 start must wait until P_LARGE is free at day 10")
        self.assertEqual(res_1["planned_end_day"], 25)
        self.assertEqual(self.sim.platen_available_days[2], 25)

    def test_invalid_action_safe_fallback_and_penalty(self):
        """Test that passing an invalid action (e.g. B1 to P_SMALL) safely falls back to a feasible platen with penalty."""
        self.sim.reset()
        # B0: Allocate to P_SMALL (valid)
        self.sim.step(0)
        
        # B1: Try allocating to P_SMALL (invalid - spatial limit exceeded)
        res_invalid = self.sim.step(0)
        
        # Requested action was invalid
        self.assertFalse(res_invalid["requested_feasible"], "Requested action should be flagged as infeasible")
        # Actual allocated platen must be feasible (P_MED or P_LARGE)
        self.assertIn(res_invalid["platen_idx"], [1, 2], "Actual allocated platen must be a safe feasible fallback")
        self.assertTrue(res_invalid["is_feasible"], "Recorded schedule must be 100% feasible")
        # Large penalty was applied
        self.assertLess(res_invalid["reward"], -400.0, "Heavy penalty must be applied for invalid action")

    def test_state_dimension_and_cluster_feature(self):
        """Test that state vector includes cluster feature and matches 10 + 3*num_platens dimension."""
        self.sim.reset()
        state = self.sim._get_state()
        expected_dim = 10 + 3 * len(self.df_platens) # 10 + 3*3 = 19
        self.assertEqual(len(state), expected_dim, f"State dimension should be {expected_dim}")
        # B0 has cluster_id=0 -> feature should be 0.0
        self.assertEqual(state[9], 0.0)

if __name__ == "__main__":
    unittest.main()
