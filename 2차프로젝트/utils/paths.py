# utils/paths.py
"""
================================================================================
Centralized Path Management Module for Shipyard Platen Scheduling Project
================================================================================
- Standardized directory layout:
    data/processed/
    ├── features/      (featured_blocks.csv, featured_platens.csv)
    ├── models/        (best_rl_model.pth, ppo_model.pth, dqn_model.pth)
    ├── schedules/     (ortools, heuristic_*, ppo, dqn schedules)
    ├── reports/       (benchmark_metrics.json, *.png charts)
    └── experiments/   (ablation, tuning, dynamic scenarios, MCDA)
================================================================================
"""

import os

# Root directories
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
STANDARDIZED_DIR = os.path.join(DATA_DIR, "standardized")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# Standardized Subdirectories
FEATURES_DIR = os.path.join(PROCESSED_DIR, "features")
MODELS_DIR = os.path.join(PROCESSED_DIR, "models")
SCHEDULES_DIR = os.path.join(PROCESSED_DIR, "schedules")
REPORTS_DIR = os.path.join(PROCESSED_DIR, "reports")
EXPERIMENTS_DIR = os.path.join(PROCESSED_DIR, "experiments")

# Ensure all subdirectories exist safely
for _dir in [PROCESSED_DIR, FEATURES_DIR, MODELS_DIR, SCHEDULES_DIR, REPORTS_DIR, EXPERIMENTS_DIR]:
    os.makedirs(_dir, exist_ok=True)

# Standard file path getters with backward-compatibility fallbacks:

def get_feature_path(filename: str) -> str:
    """Returns path in features/, fallback to processed/ then standardized/."""
    p_feat = os.path.join(FEATURES_DIR, filename)
    if os.path.exists(p_feat):
        return p_feat
    p_proc = os.path.join(PROCESSED_DIR, filename)
    if os.path.exists(p_proc):
        return p_proc
    return os.path.join(STANDARDIZED_DIR, filename)

def get_model_path(filename: str) -> str:
    """Returns path in models/, fallback to processed/ then experiments/."""
    p_mod = os.path.join(MODELS_DIR, filename)
    if os.path.exists(p_mod):
        return p_mod
    p_proc = os.path.join(PROCESSED_DIR, filename)
    if os.path.exists(p_proc):
        return p_proc
    return os.path.join(EXPERIMENTS_DIR, filename)

def get_schedule_path(filename: str) -> str:
    """Returns path in schedules/, fallback to processed/ then experiments/ then standardized/."""
    p_sch = os.path.join(SCHEDULES_DIR, filename)
    if os.path.exists(p_sch):
        return p_sch
    p_proc = os.path.join(PROCESSED_DIR, filename)
    if os.path.exists(p_proc):
        return p_proc
    p_exp = os.path.join(EXPERIMENTS_DIR, filename)
    if os.path.exists(p_exp):
        return p_exp
    return os.path.join(STANDARDIZED_DIR, filename)

def get_report_path(filename: str) -> str:
    """Returns path in reports/, fallback to processed/."""
    p_rep = os.path.join(REPORTS_DIR, filename)
    if os.path.exists(p_rep):
        return p_rep
    return os.path.join(PROCESSED_DIR, filename)

def get_experiment_path(filename: str) -> str:
    """Returns path in experiments/, fallback to processed/."""
    p_exp = os.path.join(EXPERIMENTS_DIR, filename)
    if os.path.exists(p_exp):
        return p_exp
    return os.path.join(PROCESSED_DIR, filename)
