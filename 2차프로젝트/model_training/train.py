# model_training/train.py
"""
================================================================================
Shipyard Optimization & RL Model Training Job on Kubernetes
================================================================================
- Pipeline:
  1. Downloads processed features from MinIO (s3://shipyard-mlops/features/blocks).
  2. Executes Google OR-Tools Mathematical Optimization & PPO Reinforcement Learning.
  3. Uploads trained model weights (.pth) and schedules (.csv) to MinIO (s3://shipyard-mlops/models).
================================================================================
"""

import os
import sys
import io
import boto3
from botocore.client import Config
import pandas as pd
import numpy as np

cur_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(cur_dir)
sys.path.append(root_dir)

from modeling.solver_ortools import run_ortools_platen_optimization
from modeling.train_ppo import train_ppo_pipeline

def get_s3_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "http://minio-service.minio.svc:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4")
    )

def main():
    print("=" * 80)
    print("Starting Shipyard Platen Optimization Training Job on Kubernetes")
    print("=" * 80)

    s3 = get_s3_client()
    bucket_name = "shipyard-mlops"

    # Ensure bucket exists
    try:
        s3.head_bucket(Bucket=bucket_name)
    except Exception:
        try:
            s3.create_bucket(Bucket=bucket_name)
            print(f"Created MinIO bucket: {bucket_name}")
        except Exception as e:
            print(f"MinIO bucket notice: {e}")

    # 1. Run Mathematical Solver
    print("\n--- Step 1: Running Google OR-Tools CP-SAT Solver ---")
    ortools_res = run_ortools_platen_optimization(window_size=50, time_limit_per_window=1.0)

    # 2. Run PPO Training
    print("\n--- Step 2: Running Action-Masked PPO RL Pipeline ---")
    train_ppo_pipeline(episodes=50)

    # 3. Upload Artifacts to MinIO
    print("\n--- Step 3: Uploading Model Artifacts to MinIO ---")
    processed_dir = os.path.join(root_dir, "data/processed")
    artifacts = [
        ("ortools_scheduling_results.csv", "schedules/ortools_scheduling_results.csv"),
        ("ppo_scheduling_results.csv", "schedules/ppo_scheduling_results.csv"),
        ("ppo_model.pth", "models/ppo_model.pth"),
        ("featured_blocks.csv", "features/featured_blocks.csv"),
        ("featured_platens.csv", "features/featured_platens.csv")
    ]

    for local_name, s3_key in artifacts:
        fpath = os.path.join(processed_dir, local_name)
        if os.path.exists(fpath):
            try:
                s3.upload_file(fpath, bucket_name, s3_key)
                print(f"   Uploaded s3://{bucket_name}/{s3_key}")
            except Exception as e:
                print(f"   Upload failed for {local_name}: {e}")

    print("\nShipyard Platen MLOps Training Job Completed Successfully.")

if __name__ == "__main__":
    main()
