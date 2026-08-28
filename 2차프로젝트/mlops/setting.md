# MLflow Tracking & Model Registry 운영 가이드

> 10대 알고리즘 실험 지표(Makespan, 지연 블록, 가동률, 연산 시간) 추적 및 `Shipyard-PPO-Scheduler` 프로덕션 모델 레지스트리를 관리하는 MLOps 가이드입니다.

---

## 1. 인프라 배포 및 구성 명령어 (Setup & Deploy)

```bash
# 1. MLflow Tracking Server 배포 (4GiB 메모리 최적화)
kubectl apply -f mlops/k8s/mlflow-server.yaml

# 2. 파드 상태 확인
kubectl get pods -l app=mlflow-server
```

---

## 2. 상태 확인 및 모니터링 명령어 (Verify & Monitor)

```bash
# 1. MLflow Web UI 포트포워딩
kubectl port-forward -n default svc/mlflow-service 5000:5000
# 대시보드 접속: http://localhost:5000

# 2. 파드 로그 확인
kubectl logs -l app=mlflow-server -f
```

---

## 3. 벤치마크 로깅 및 모델 등록 명령어 (Run & Execute)

```bash
# 가상환경 활성화
pj2

# 1. 10대 알고리즘 전수 실험 추적 및 PPO 모델 레지스트리 자동 등록
python mlops/scripts/run_all_experiments_mlflow.py

# 2. MLflow REST API로 등록된 모델 목록 조회
curl -s "http://localhost:5000/api/2.0/mlflow/registered-models/search" | jq .

# 3. 실험 지표 및 Run 목록 조회
curl -s "http://localhost:5000/api/2.0/mlflow/runs/search" \
  -H "Content-Type: application/json" \
  -d '{"experiment_ids": ["1"]}' | jq .
```
