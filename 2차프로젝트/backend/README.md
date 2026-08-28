# FastAPI Model Serving Backend 운영 가이드

> PPO 강화학습 추론, 872개 블록 마스터 공정표 제공, Kafka 긴급 이벤트 스트림 발행을 담당하는 고성능 비동기 백엔드 가이드입니다.

---

## 1. 주요 파일별 역할 및 기능

- [`app/main.py`](./app/main.py): 872개 블록 마스터 공정표 조회(`/api/schedule/{algorithm}`), PPO 모델 0.65초 실시간 추론, Kafka 긴급 이벤트 발행 엔드포인트를 제공하는 FastAPI 핵심 백엔드.
- [`k8s/fastapi-serving.yaml`](./k8s/fastapi-serving.yaml): FastAPI 서빙 파드 및 Service 배포 매니페스트.

---

## 2. 인프라 배포 및 실행 명령어

```bash
# 1. Kubernetes FastAPI 서빙 배포
kubectl apply -f backend/k8s/fastapi-serving.yaml

# 2. FastAPI 서비스 포트포워딩
kubectl port-forward -n default svc/fastapi-service 8000:8000
# Swagger API 문서: http://localhost:8000/docs
# 헬스체크 엔드포인트: http://localhost:8000/health

# 3. 로컬 Uvicorn 개발 서버 직접 실행
pj2
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 3. 핵심 에러 발생 시 해결법 (Troubleshooting)

- **에러 1: `FastAPI Health Check 실패 (platens_cache is None)`**
  - **원인**: `/data/standardized/platen_information.csv` 경로가 마운트되지 않음.
  - **해결**: `load_assets()` 함수가 정상 실행되도록 `featured_platens.csv` 및 `platen_information.csv` 데이터 파일 존재 여부 확인.
