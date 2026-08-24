# ✨ React 프론트엔드 대시보드 빠른 시작 가이드 (setting.md)

이 문서는 처음 시작하는 사람도 **위에서부터 순서대로 명령어를 복사해서 터미널에 붙여넣기만 하면 100% 동일하게 동작**하도록 작성된 실전 구축 가이드입니다.

---

## 🚀 방법 1: 로컬 개발 환경에서 즉시 실행 (가장 빠름 & 강력 추천 ⭐)

Node.js(npm)가 설치된 환경에서 아래 3줄로 즉시 개발 서버를 띄울 수 있습니다:

```bash
# 1. frontend 디렉토리로 이동
cd ~/workspace/samsung_project/2차프로젝트/frontend

# 2. 의존성 패키지 설치
npm install

# 3. React 프론트엔드 대시보드 구동
npm start
```

- 🖥️ **브라우저 접속 URL:** [http://localhost:3000](http://localhost:3000)

---

## ☸️ 방법 2: 쿠버네티스 클러스터 파드로 배포

```bash
# 1. 프론트엔드 소스 코드를 ConfigMap으로 일괄 등록
kubectl create configmap react-src-code --from-file=frontend/src/ --namespace default --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap react-public-code --from-file=frontend/public/ --namespace default --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap react-pkg-code --from-file=frontend/package.json --namespace default --dry-run=client -o yaml | kubectl apply -f -

# 2. React 프론트엔드 파드 배포
kubectl apply -f frontend/k8s/react-frontend.yaml

# 3. 파드가 Running 상태가 되면 포트포워딩
kubectl port-forward svc/react-frontend-service 3000:3000
```

---

## 🎮 실시간 대시보드 기능 소개

1. **상태 배너:** Kubernetes 클러스터, Kafka, MinIO, FastAPI 백엔드 연동 상태 및 실시간 모델 정확도(99.37%) 확인
2. **인터랙티브 시뮬레이터:** 슬라이더를 조절하여 주문 금액/시간대/카테고리를 입력하고 **`⚡ 실시간 딥러닝 추론 실행`**
3. **VIP 판정 & 초고속 지연시간:** 모델의 VIP 확률 판정 결과 및 0.002초(2ms) 미만의 추론 소요 시간 실시간 시각화
4. **최근 추론 스트림 이력:** 실시간 요청 이력을 테이블로 모니터링
