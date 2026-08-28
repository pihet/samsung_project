# React Digital Twin Frontend 운영 가이드

> 66개 정반 및 872개 블록의 2D 시각화 간트차트와 실시간 긴급 블록 스트림 처리를 시각화하는 디지털 트윈 프론트엔드 운영 명령어 가이드입니다.

---

## 1. 인프라 배포 및 구성 명령어 (Setup & Deploy)

```bash
# 1. React 프론트엔드 파드 및 서비스 배포
kubectl apply -f frontend/k8s/react-frontend.yaml

# 2. 파드 상태 확인
kubectl get pods -l app=react-frontend
```

---

## 2. 상태 확인 및 모니터링 명령어 (Verify & Monitor)

```bash
# 1. React 프론트엔드 포트포워딩
kubectl port-forward -n default svc/react-frontend-service 3000:3000
# 대시보드 접속: http://localhost:3000

# 2. 파드 로그 확인
kubectl logs -l app=react-frontend -f
```

---

## 3. 로컬 실행 명령어 (Run & Execute)

```bash
# 로컬 개발 모드로 프론트엔드 기동
cd frontend
npm start
```
