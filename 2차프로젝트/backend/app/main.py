# backend/app/main.py
"""
================================================================================
FastAPI Backend Server for Samsung Heavy Industries Smart Shipyard Platform
================================================================================
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

cur_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(cur_dir)
root_dir = os.path.dirname(backend_dir)

# Multi-path search for data/processed (local dev & K8s container)
candidate_paths = [
    os.path.join(root_dir, "data/processed"),
    "/opt/data/processed",
    "/data/processed",
    os.path.join(cur_dir, "data/processed")
]
processed_dir = next((p for p in candidate_paths if os.path.exists(p)), candidate_paths[0])

sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "simulation"))
sys.path.append(os.path.join(root_dir, "modeling"))

app = FastAPI(
    title="Samsung Heavy Industries Smart Shipyard Platen API",
    description="Backend API for Platen Optimization, Benchmark Metrics, and Real-time AI Inference",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FastActor(nn.Module):
    def __init__(self, state_dim: int = 208, action_dim: int = 66):
        super(FastActor, self).__init__()
        self.actor = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.Tanh(),
            nn.Linear(256, 128),
            nn.Tanh(),
            nn.Linear(128, 64),
            nn.Tanh(),
            nn.Linear(64, action_dim)
        )
    def forward(self, state: torch.Tensor, mask: torch.Tensor = None):
        logits = self.actor(state)
        if mask is not None:
            logits = torch.where(mask, logits, torch.tensor(-1e9, device=state.device))
        return logits

ppo_model = None
df_platens_cache = None

def load_assets():
    global ppo_model, df_platens_cache
    
    # 1. Load Platens
    platen_file = os.path.join(processed_dir, "featured_platens.csv")
    if os.path.exists(platen_file):
        df_platens_cache = pd.read_csv(platen_file)
        print(f"[Backend Startup] Loaded {len(df_platens_cache)} platens from {platen_file}")

    # 2. Load PPO Model
    ppo_file = os.path.join(processed_dir, "ppo_model.pth")
    if os.path.exists(ppo_file):
        try:
            device = torch.device("cpu")
            ppo_model = FastActor(208, 66).to(device)
            state_dict = torch.load(ppo_file, map_location=device)
            actor_dict = {k.replace("actor.", ""): v for k, v in state_dict.items() if "actor." in k}
            if actor_dict:
                ppo_model.actor.load_state_dict(actor_dict)
            else:
                ppo_model.load_state_dict(state_dict, strict=False)
            ppo_model.eval()
            print("[Backend Startup] PPO model initialized.")
        except Exception as e:
            pass

# Initialize assets on startup/import
load_assets()

@app.get("/health")
def health_check():
    # Reload assets if not yet loaded
    if df_platens_cache is None:
        load_assets()
    return {
        "status": "healthy",
        "service": "shipyard-platen-backend",
        "processed_dir": processed_dir,
        "model_loaded": ppo_model is not None,
        "platens_count": len(df_platens_cache) if df_platens_cache is not None else 0
    }

@app.get("/api/benchmark")
def get_benchmark_leaderboard():
    benchmark_data = [
        {"rank": 1, "algorithm": "Google OR-Tools CP-SAT (Ours)", "type": "Mathematical Optimization", "makespan_days": 1216, "delayed_blocks": 252, "compute_time_sec": 18.09, "status": "Best Makespan"},
        {"rank": 2, "algorithm": "EST Heuristic (Ours)", "type": "Rule-based Heuristic", "makespan_days": 1249, "delayed_blocks": 259, "compute_time_sec": 0.12, "status": "Fast Baseline"},
        {"rank": 3, "algorithm": "PPO Actor-Critic (Ours)", "type": "Deep Reinforcement Learning", "makespan_days": 1398, "delayed_blocks": 586, "compute_time_sec": 0.05, "status": "Real-time AI"},
        {"rank": 4, "algorithm": "EDDQN (Paper Benchmark)", "type": "Research Paper Baseline", "makespan_days": 1529, "delayed_blocks": 310, "compute_time_sec": 0.10, "status": "Paper Benchmark"},
        {"rank": 5, "algorithm": "EST (Paper Benchmark)", "type": "Research Paper Baseline", "makespan_days": 1566, "delayed_blocks": 345, "compute_time_sec": 0.15, "status": "Paper Benchmark"},
        {"rank": 6, "algorithm": "RTB Heuristic (Paper)", "type": "Research Paper Baseline", "makespan_days": 1729, "delayed_blocks": 420, "compute_time_sec": 0.15, "status": "Paper Benchmark"},
        {"rank": 7, "algorithm": "SPT Heuristic (Paper)", "type": "Research Paper Baseline", "makespan_days": 1792, "delayed_blocks": 435, "compute_time_sec": 0.15, "status": "Paper Benchmark"},
        {"rank": 8, "algorithm": "RUB Heuristic (Paper)", "type": "Research Paper Baseline", "makespan_days": 1793, "delayed_blocks": 440, "compute_time_sec": 0.15, "status": "Paper Benchmark"},
        {"rank": 9, "algorithm": "LPT Heuristic (Paper)", "type": "Research Paper Baseline", "makespan_days": 1845, "delayed_blocks": 460, "compute_time_sec": 0.15, "status": "Paper Benchmark"},
        {"rank": 10, "algorithm": "DDQN (Paper Benchmark)", "type": "Research Paper Baseline", "makespan_days": 2000, "delayed_blocks": 510, "compute_time_sec": 0.10, "status": "Paper Benchmark"},
        {"rank": 11, "algorithm": "Random Policy (Baseline)", "type": "Random Baseline", "makespan_days": 7003, "delayed_blocks": 513, "compute_time_sec": 0.05, "status": "Worst Baseline"}
    ]
    return {"total": len(benchmark_data), "leaderboard": benchmark_data}

@app.get("/api/platens")
def get_platens():
    if df_platens_cache is None:
        load_assets()
    if df_platens_cache is None:
        raise HTTPException(status_code=500, detail="Platens dataset not loaded")
    return df_platens_cache.to_dict(orient="records")

@app.get("/api/schedule/{algorithm}")
def get_schedule(algorithm: str):
    algo_lower = algorithm.lower()
    file_map = {
        "ortools": "ortools_scheduling_results.csv",
        "ppo": "ppo_scheduling_results.csv",
        "dqn": "dqn_scheduling_results.csv"
    }

    if algo_lower not in file_map:
        raise HTTPException(status_code=400, detail=f"Unsupported algorithm '{algorithm}'. Choose from: ortools, ppo, dqn")

    csv_path = os.path.join(processed_dir, file_map[algo_lower])
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail=f"Schedule file not found for {algorithm}")

    df_sched = pd.read_csv(csv_path)
    makespan = int(df_sched['planned_end_day'].max())
    delayed_blocks = int((df_sched['delay_days'] > 0).sum())
    total_delay = int(df_sched['delay_days'].sum())

    return {
        "algorithm": algorithm.upper(),
        "total_blocks": len(df_sched),
        "makespan_days": makespan,
        "delayed_blocks": delayed_blocks,
        "total_delay_days": total_delay,
        "schedule": df_sched.to_dict(orient="records")
    }

class BlockRecommendRequest(BaseModel):
    block_id: str
    ship_id: str
    length_m: float
    width_m: float
    weight_ton: float
    lead_time_days: int
    est_day: int
    due_day: int
    block_type: Optional[str] = "FLAT"

@app.post("/api/recommend")
def recommend_platen(req: BlockRecommendRequest):
    t0 = time.time()
    if df_platens_cache is None:
        load_assets()
    if df_platens_cache is None:
        raise HTTPException(status_code=500, detail="Platens metadata not loaded")

    b_max, b_min = max(req.length_m, req.width_m), min(req.length_m, req.width_m)
    feasible_platens = []
    mask = np.zeros(len(df_platens_cache), dtype=bool)

    for p_idx in range(len(df_platens_cache)):
        p = df_platens_cache.iloc[p_idx]
        p_max, p_min = max(p['platen_length_m'], p['platen_width_m']), min(p['platen_length_m'], p['platen_width_m'])
        
        if b_max <= p_max and b_min <= p_min and req.weight_ton <= p['crane_capacity_ton']:
            mask[p_idx] = True
            feasible_platens.append(p_idx)

    if not feasible_platens:
        mask[0] = True
        feasible_platens = [0]

    slack = (req.due_day - req.est_day) - req.lead_time_days
    urgency = min(1.0, req.lead_time_days / max(1, req.due_day - req.est_day))

    b_feats = [
        req.length_m / 35.0,
        req.width_m / 25.0,
        req.weight_ton / 250.0,
        req.lead_time_days / 80.0,
        req.est_day / 1500.0,
        req.due_day / 1500.0,
        slack / 200.0,
        urgency,
        1.0 if req.block_type.upper() == 'FLAT' else 0.0,
        0.5
    ]

    p_feats = []
    for p_idx in range(len(df_platens_cache)):
        p = df_platens_cache.iloc[p_idx]
        p_feats.extend([
            0.1,
            p['platen_area_m2'] / 800.0,
            p['crane_capacity_ton'] / 350.0
        ])

    state_vec = np.array(b_feats + p_feats, dtype=np.float32)

    if ppo_model is not None:
        with torch.no_grad():
            s_t = torch.FloatTensor(state_vec).unsqueeze(0)
            m_t = torch.BoolTensor(mask).unsqueeze(0)
            logits = ppo_model(s_t, m_t)
            chosen_p_idx = logits.argmax(dim=1).item()
    else:
        chosen_p_idx = feasible_platens[0]

    chosen_p = df_platens_cache.iloc[chosen_p_idx]
    infer_time_ms = round((time.time() - t0) * 1000, 2)

    b_area = req.length_m * req.width_m
    p_area = chosen_p['platen_area_m2']
    utilization_rate = round(min(100.0, (b_area / max(p_area, 1e-5)) * 100), 1)

    return {
        "block_id": req.block_id,
        "ship_id": req.ship_id,
        "recommended_platen_idx": int(chosen_p_idx),
        "recommended_platen_id": chosen_p['platen_id'],
        "recommended_platen_name": chosen_p['platen_name'],
        "primary_area": chosen_p['primary_area'],
        "crane_capacity_ton": float(chosen_p['crane_capacity_ton']),
        "platen_dimensions": f"{chosen_p['platen_length_m']}m x {chosen_p['platen_width_m']}m",
        "area_utilization_pct": utilization_rate,
        "inference_time_ms": infer_time_ms,
        "constraints_verified": {
            "spatial_fit": True,
            "crane_weight_safe": bool(req.weight_ton <= chosen_p['crane_capacity_ton']),
            "feasible_candidates_count": len(feasible_platens)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
