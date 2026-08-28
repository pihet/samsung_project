# React Digital Twin Frontend 운영 가이드

> 66개 정반 및 872개 블록의 2D 시각화 간트차트와 실시간 긴급 블록 스트림 처리를 시각화하는 디지털 트윈 프론트엔드 가이드입니다.

---

## 1. 주요 파일별 역할 및 기능

- [`src/App.js`](./src/App.js): 66개 정반 실시간 2D 간트차트, 10대 알고리즘 성능 비교 리더보드, 실시간 긴급 블록 스트림 이벤트 피드를 렌더링하는 React 메인 컴포넌트.
- [`src/App.css`](./src/App.css): 다크 모드 기반 엔터프라이즈 디지털 트윈 대시보드 스타일시트.
- [`k8s/react-frontend.yaml`](./k8s/react-frontend.yaml): React 웹 애플리케이션 파드 및 Nginx 웹서버 배포 매니페스트.

---

## 2. 인프라 배포 및 실행 명령어

```bash
# 1. Kubernetes 프론트엔드 배포
kubectl apply -f frontend/k8s/react-frontend.yaml

# 2. React 대시보드 포트포워딩
kubectl port-forward -n default svc/react-frontend-service 3000:3000
# 대시보드 접속: http://localhost:3000

# 3. 로컬 React 개발 서버 기동
cd frontend
npm install
npm start
```

---

## 3. 핵심 에러 발생 시 해결법 (Troubleshooting)

- **에러 1: `대시보드에서 백엔드 데이터가 로드되지 않음 (CORS 오류)`**
  - **원인**: 브라우저에서 `localhost:8000` 호출 시 CORS 헤더 누락.
  - **해결**: FastAPI 백엔드(`backend/app/main.py`)에 `CORSMiddleware`가 `allow_origins=["*"]`로 설정되어 있는지 확인하고 포트 8000이 열려있는지 확인.
