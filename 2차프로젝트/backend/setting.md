# FastAPI Model Serving Backend 운영 가이드

> PPO 강화학습 추론, 872개 블록 마스터 공정표 제공, Kafka 긴급 이벤트 스트림 발행을 담당하는 고성능 비동기 백엔드 운영 명령어 가이드입니다.

---

## 1. 인프라 배포 및 구성 명령어 (Setup & Deploy)

```bash
# 1. ConfigMap 및 FastAPI 서빙 파드 배포
kubectl apply -f backend/k8s/fastapi-serving.yaml

# 2. 파드 상태 확인
kubectl get pods -l app=fastapi-serving
```

---

## 2. 상태 확인 및 모니터링 명령어 (Verify & Monitor)

```bash
# 1. FastAPI 서비스 포트포워딩
kubectl port-forward -n default svc/fastapi-service 8000:8000
# API 문서: http://localhost:8000/docs
# 헬스체크: http://localhost:8000/health

# 2. 파드 로그 확인
kubectl logs -l app=fastapi-serving -f
```

---

## 3. 로컬 실행 및 테스트 명령어 (Run & Execute)

```bash
# 가상환경 활성화
pj2

# 방법 1: 로컬 개발 서버 기동 (Uvicorn)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 방법 2: 헬스체크 및 스케줄 API 직접 테스트 (CLI)
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/schedule/ortools | jq .
```
