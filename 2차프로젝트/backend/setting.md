# FastAPI 실시간 서빙 & 백엔드 빠른 시작 가이드 (setting.md)

이 문서는 Kubernetes 클러스터에 FastAPI 백엔드 서빙 파드를 배포하고 운영하기 위한 실전 구축 가이드입니다.

---

## Step 1. FastAPI 애플리케이션 및 데이터 ConfigMap 등록

```bash
# 1. 2차프로젝트 폴더로 이동
cd ~/workspace/samsung_project/2차프로젝트

# 2. main.py 코드를 ConfigMap으로 등록
kubectl create configmap fastapi-serving-app \
  --from-file=backend/app/main.py \
  --namespace default \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. 모델 결과 및 피처 데이터셋(featured_platens, ortools, ppo, dqn)을 ConfigMap으로 등록
kubectl create configmap fastapi-data-processed \
  --from-file=data/processed/featured_platens.csv \
  --from-file=data/processed/ortools_scheduling_results.csv \
  --from-file=data/processed/ppo_scheduling_results.csv \
  --from-file=data/processed/dqn_scheduling_results.csv \
  --namespace default \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## Step 2. FastAPI 고가용성 서빙 파드(2대) 배포

```bash
# 1. FastAPI Deployment 및 Service 배포
kubectl apply -f backend/k8s/fastapi-serving.yaml

# 2. 2대의 서빙 파드가 1/1 Running 될 때까지 관찰
kubectl get pods -l app=fastapi-serving -w
```

---

## Step 3. 실시간 백엔드 API 포트포워딩

```bash
# FastAPI 서빙 포트(8000) 포트포워딩
kubectl port-forward svc/fastapi-service 8000:8000
```

- Swagger 대화형 API 문서: http://localhost:8000/docs
- 11개 알고리즘 벤치마크 API: http://localhost:8000/api/benchmark
- 872개 블록 스케줄 API: http://localhost:8000/api/schedule/ortools
