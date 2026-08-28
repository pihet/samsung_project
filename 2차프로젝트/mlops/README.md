# MLflow Tracking & Model Registry 운영 가이드

> 10대 알고리즘 실험 지표(Makespan, 지연 블록, 가동률, 연산 시간) 추적 및 `Shipyard-PPO-Scheduler` 프로덕션 모델 레지스트리를 관리하는 MLOps 가이드입니다.

---

## 1. 주요 파일별 역할 및 기능

- [`k8s/mlflow-server.yaml`](./k8s/mlflow-server.yaml): 4GiB 메모리 한도, SQLite 백엔드, MinIO S3 아티팩트 연동이 적용된 Kubernetes MLflow 배포 매니페스트.
- [`scripts/run_all_experiments_mlflow.py`](./scripts/run_all_experiments_mlflow.py): 10대 알고리즘 전수 벤치마크 지표를 MLflow에 일괄 등록하고 최적 PPO 모델을 Model Registry에 정식 등록하는 스크립트.
- [`tracking/mlflow_logger.py`](./tracking/mlflow_logger.py): MLflow SDK 및 REST API를 통해 파라미터, 지표, 모델 아티팩트를 업로드하는 핵심 모듈.

---

## 2. 인프라 배포 및 실행 명령어

```bash
# 1. MLflow Tracking Server 배포
kubectl apply -f mlops/k8s/mlflow-server.yaml

# 2. 10대 알고리즘 벤치마크 실험 로깅 및 모델 등록
pj2
python mlops/scripts/run_all_experiments_mlflow.py

# 3. MLflow Web UI 포트포워딩
kubectl port-forward -n default svc/mlflow-service 5000:5000
# 접속 주소: http://localhost:5000
```

---

## 3. 핵심 에러 발생 시 해결법 (Troubleshooting)

- **에러 1: `OOMKilled (Exit Code 137) 발생`**
  - **원인**: MLflow 컨테이너 내부에서 `pip install` 빌드 시 메모리가 부족하여 파드가 강제 종료됨.
  - **해결**: `mlflow-server.yaml`의 메모리 제한을 `4096Mi`로 상향 조정:
    ```yaml
    resources:
      limits:
        memory: "4096Mi"
    ```
- **에러 2: `등록된 모델(Registered Model)이 UI에 보이지 않음`**
  - **원인**: SQLite 백엔드 DB 재시작 또는 Run 연결 누락.
  - **해결**: `python mlops/scripts/run_all_experiments_mlflow.py`를 재실행하여 Model Registry 메타데이터를 즉시 갱신.
