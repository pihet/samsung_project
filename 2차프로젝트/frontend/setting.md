# React 프론트엔드 대시보드 빠른 시작 가이드 (setting.md)

이 문서는 Kubernetes 클러스터에 React 대시보드 파드를 배포하거나 로컬에서 개발 서버를 구동하기 위한 가이드입니다.

---

## 방법 1: 로컬 개발 환경에서 즉시 실행 (추천)

Node.js(npm)가 설치된 환경에서 아래 3줄로 즉시 개발 서버를 띄울 수 있습니다:

```bash
# 1. frontend 디렉토리로 이동
cd ~/workspace/samsung_project/2차프로젝트/frontend

# 2. 의존성 패키지 설치
npm install

# 3. React 프론트엔드 대시보드 구동
npm start
```

- 브라우저 접속 URL: http://localhost:3000

---

## 방법 2: 쿠버네티스 클러스터 파드로 배포

```bash
# 1. 2차프로젝트 폴더로 이동
cd ~/workspace/samsung_project/2차프로젝트

# 2. 프론트엔드 소스 코드를 ConfigMap으로 등록
kubectl create configmap react-src-code --from-file=frontend/src/ --namespace default --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap react-public-code --from-file=frontend/public/ --namespace default --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap react-pkg-code --from-file=frontend/package.json --namespace default --dry-run=client -o yaml | kubectl apply -f -

# 3. React 프론트엔드 파드 배포
kubectl apply -f frontend/k8s/react-frontend.yaml

# 4. 파드가 Running 상태가 되면 포트포워딩
kubectl port-forward svc/react-frontend-service 3000:3000
```
