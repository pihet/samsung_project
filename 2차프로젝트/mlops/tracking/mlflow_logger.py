# mlops/tracking/mlflow_logger.py
"""
[조선소 스마트 정반 스케줄링 통합 MLflow 실험 추적 & 모델 레지스트리 로거]
--------------------------------------------------------------------------------
1. 주요 역할:
   - MLflow Tracking Server(http://localhost:5000)와 MinIO S3 아티팩트 스토어 연동
   - 10대 알고리즘(PPO, OR-Tools, DQN, Heuristics)의 파라미터, 메트릭, 결과 아티팩트 자동 기록
   - 최고 성능 PPO 강화학습 모델의 MLflow Model Registry 자동 등록 및 버전 관리 (v1, Production)
--------------------------------------------------------------------------------
"""

import os
import sys
import json
import time
from typing import Dict, Any, Optional
import mlflow
from mlflow.tracking import MlflowClient

# MLflow 환경 변수 및 엔드포인트 설정
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_EXPERIMENT_NAME = "Shipyard-Smart-Scheduling-Benchmark"

# MinIO S3 아티팩트 인증 환경변수
os.environ["MLFLOW_S3_ENDPOINT_URL"] = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
os.environ["AWS_ACCESS_KEY_ID"] = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


def init_mlflow_experiment(experiment_name: str = MLFLOW_EXPERIMENT_NAME) -> str:
    """MLflow Tracking URI 및 실험(Experiment) 초기화"""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        experiment_id = mlflow.create_experiment(
            name=experiment_name,
            artifact_location="s3://mlflow-artifacts/"
        )
    else:
        experiment_id = experiment.experiment_id
    mlflow.set_experiment(experiment_name)
    print(f"[MLflow Logger] Tracking URI: {MLFLOW_TRACKING_URI}, Experiment: {experiment_name} (ID: {experiment_id})")
    return experiment_id


def log_algorithm_run(
    algo_name: str,
    algo_type: str,
    params: Dict[str, Any],
    metrics: Dict[str, float],
    artifacts: Optional[Dict[str, str]] = None,
    tags: Optional[Dict[str, str]] = None
):
    """
    단일 알고리즘 실행 결과를 MLflow에 기록
    """
    init_mlflow_experiment()
    
    run_name = f"{algo_name}_{time.strftime('%Y%m%d_%H%M%S')}"
    with mlflow.start_run(run_name=run_name) as run:
        # 1) 태그 기록
        mlflow.set_tag("algorithm", algo_name)
        mlflow.set_tag("algorithm_type", algo_type)
        mlflow.set_tag("project", "Samsung-Heavy-Industries-Platen-Scheduling")
        if tags:
            for k, v in tags.items():
                mlflow.set_tag(k, v)

        # 2) 하이퍼파라미터 및 설정 기록
        for k, v in params.items():
            mlflow.log_param(k, v)

        # 3) 핵심 메트릭(Makespan, 지연 블록 수, 계산 시간) 기록
        for k, v in metrics.items():
            mlflow.log_metric(k, float(v))

        # 4) 아티팩트(스케줄 CSV, 모델 가중치, 차트 이미지 등) 업로드
        if artifacts:
            for art_name, art_path in artifacts.items():
                if os.path.exists(art_path):
                    mlflow.log_artifact(art_path)
                    print(f" -> 아티팩트 업로드: {art_name} ({art_path})")

        print(f"[MLflow Logger] Run '{run_name}' 기록 완료 (Run ID: {run.info.run_id})")
        return run.info.run_id


def register_ppo_production_model(
    model_path: str,
    metrics: Dict[str, float],
    model_name: str = "Shipyard-PPO-Scheduler"
):
    """
    학습된 최적 PPO 강화학습 모델을 MLflow Model Registry에 공식 등록
    """
    init_mlflow_experiment()
    client = MlflowClient()

    with mlflow.start_run(run_name="PPO_Production_Candidate") as run:
        # 모델 파라미터 및 성능 로깅
        mlflow.log_param("architecture", "Actor-Critic-MLP")
        mlflow.log_param("action_space", "66_Platens_Dynamic_Masked")
        for k, v in metrics.items():
            mlflow.log_metric(k, float(v))

        # 가중치 파일 로깅 및 모델 등록
        if os.path.exists(model_path):
            mlflow.log_artifact(model_path, artifact_path="model")
            artifact_uri = f"{run.info.artifact_uri}/model"
            
            # Model Registry 등록
            try:
                model_version = mlflow.register_model(
                    model_uri=f"runs:/{run.info.run_id}/model",
                    name=model_name
                )
                print(f"[Model Registry] 모델 '{model_name}' 버전 {model_version.version} 등록 성공!")
            except Exception as e:
                print(f"[Model Registry] 등록 알림: {e}")
