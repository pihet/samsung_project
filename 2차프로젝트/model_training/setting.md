# ✨ Keras 딥러닝 학습 & 모델 저장소 등록 가이드 (setting.md)

이 문서는 처음 시작하는 사람도 **위에서부터 순서대로 명령어를 복사해서 터미널에 붙여넣기만 하면 100% 동일하게 동작**하도록 작성된 실전 구축 가이드입니다.

---

## 🚀 Step 1. 학습 파이썬 스크립트 ConfigMap 등록

```bash
# 1. model_training 디렉토리로 이동
cd ~/workspace/samsung_project/2차프로젝트

# 2. train.py 코드를 ConfigMap으로 등록
kubectl create configmap keras-training-script \
  --from-file=model_training/train.py \
  --namespace default \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 🧠 Step 2. Keras 딥러닝 학습 Job 실행

```bash
# 1. 이전 실행 기록이 있다면 정리
kubectl delete job keras-model-training-job -n default --ignore-not-found

# 2. 딥러닝 학습 파드 실행
kubectl apply -f model_training/training-job.yaml

# 3. 실시간 딥러닝 학습 로그 관찰 (Epochs, Loss, Accuracy)
kubectl logs -f job/keras-model-training-job -n default
```

---

## 🖥️ Step 3. MinIO 웹 대시보드에서 학습된 모델 확인

학습이 성공적으로 완료되면 MinIO 웹 콘솔([http://localhost:9001](http://localhost:9001))의 **`models` 버킷**을 클릭하여 아래 파일들이 생성되었는지 확인합니다:

1. **`order_predictor.keras`**: 학습 완료된 딥러닝 신경망 모델 가중치 파일
2. **`model_meta.json`**: 모델 최종 정확도 및 메타데이터 정보

---

## 🔄 Step 4. 본 프로젝트 적용 시 변경 방법

나중에 실제 비즈니스 프로젝트로 전환할 때는:
- [`model_training/train.py`](./train.py) 내부의 `model = keras.Sequential([...])` 신경망 구조와 입력 피처만 내 프로젝트에 맞게 수정하면 됩니다!
