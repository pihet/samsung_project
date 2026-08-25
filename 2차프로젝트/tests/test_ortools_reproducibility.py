# tests/test_ortools_reproducibility.py
"""
Automated Exact Reproducibility Test for Google OR-Tools CP-SAT Solver.
Validates that running CP-SAT twice with deterministic parameters
(num_workers=1, random_seed=42, max_deterministic_time) produces
100% byte-for-byte identical schedule DataFrames and SHA-256 hashes.
"""

import unittest
import hashlib
import os
import sys

cur_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(cur_dir)
sys.path.append(base_dir)

from modeling.solver_ortools import run_ortools_platen_optimization

class TestORToolsDeterministicReproducibility(unittest.TestCase):
    def test_deterministic_sha256_repeatability(self):
        print("\n[Test] Running OR-Tools CP-SAT Deterministic Run 1...")
        eval_res1, df1 = run_ortools_platen_optimization(
            window_size=50, 
            max_deterministic_time=0.05, 
            random_seed=42, 
            save_artifact=False
        )
        csv1_bytes = df1.to_csv(index=False).encode('utf-8')
        hash1 = hashlib.sha256(csv1_bytes).hexdigest()

        print("\n[Test] Running OR-Tools CP-SAT Deterministic Run 2...")
        eval_res2, df2 = run_ortools_platen_optimization(
            window_size=50, 
            max_deterministic_time=0.05, 
            random_seed=42, 
            save_artifact=False
        )
        csv2_bytes = df2.to_csv(index=False).encode('utf-8')
        hash2 = hashlib.sha256(csv2_bytes).hexdigest()

        print(f"\n[Test Result] Run 1 SHA-256: {hash1}")
        print(f"[Test Result] Run 2 SHA-256: {hash2}")
        print(f"[Test Result] Exact SHA-256 Match: {hash1 == hash2}")

        # Assertions
        self.assertEqual(hash1, hash2, "Schedule CSV SHA-256 hashes must be 100% identical across runs.")
        self.assertEqual(len(df1), len(df2), "Total scheduled block counts must be identical.")
        self.assertEqual(eval_res1["makespan_days"], eval_res2["makespan_days"], "Makespan must be identical.")
        self.assertEqual(eval_res1["delayed_blocks_count"], eval_res2["delayed_blocks_count"], "Delayed block counts must be identical.")
        self.assertTrue(eval_res1["is_100pct_feasible"], "Run 1 must be 100% feasible.")
        self.assertTrue(eval_res2["is_100pct_feasible"], "Run 2 must be 100% feasible.")

if __name__ == "__main__":
    unittest.main()
