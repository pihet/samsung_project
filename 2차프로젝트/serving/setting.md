# ✨ FastAPI 딥러닝 서빙 & 웹 대시보드 빠른 시작 가이드 (setting.md)

이 문서는 처음 시작하는 사람도 **위에서부터 순서대로 명령어를 복사해서 터미널에 붙여넣기만 하면 100% 동일하게 동작**하도록 작성된 실전 구축 가이드입니다.

---

## 🚀 Step 1. FastAPI 애플리케이션 ConfigMap 등록

```bash
# 1. 2차프로젝트 폴더로 이동
cd ~/workspace/samsung_project/2차프로젝트

# 2. main.py 코드를 ConfigMap으로 등록
kubectl create configmap fastapi-serving-app \
  --from-file=serving/app/main.py \
  --namespace default \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## ⚡ Step 2. FastAPI 고가용성 서빙 파드(2대) 배포

```bash
# 1. FastAPI Deployment 및 Service 배포
kubectl apply -f serving/k8s/fastapi-serving.yaml

# 2. 2대의 서빙 파드가 1/1 Running 될 때까지 관찰
kubectl get pods -l app=fastapi-serving -w
```

---

## 🌐 Step 3. 실시간 웹 대시보드 접속 (포트포워딩)

서빙 파드가 `Running` 상태가 되면, **별도의 터미널 창**을 열고 아래 명령어를 실행합니다:

```bash
# FastAPI 서빙 포트(8000) 포트포워딩
kubectl port-forward svc/fastapi-service 8000:8000
```

- 🖥️ **인터랙티브 웹 대시보드:** [http://localhost:8000](http://localhost:8000)
- 📖 **Swagger 자동 대화형 API 문서:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🎮 Step 4. 실시간 딥러닝 추론 테스트

1. 웹 브라우저에서 [http://localhost:8000](http://localhost:8000) 에 접속합니다.
2. 좌측 입력창에서 **주문 금액(KRW), 시간대, 카테고리**를 조절하고 **`⚡ 실시간 딥러닝 추론 실행`** 버튼을 누릅니다.
3. 우측 화면에 **VIP 고객 확률 및 판정 결과, 그리고 0.002초(2ms) 미만의 초고속 추론 속도**가 실시간으로 표시됩니다!

---

## 🔄 Step 5. 모델 핫 리로드 (무중단 최신 모델 반영)

MinIO에 새로운 AI 모델이 업로드되었을 때, 상단의 **`🔄 모델 핫 리로드 (MinIO)`** 버튼을 누르면 서버 재시작 없이 즉시 새 모델로 스위칭됩니다!
