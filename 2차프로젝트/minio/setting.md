#  MinIO 로컬 S3 스토리지 빠른 시작 가이드 (setting.md)

이 문서는 처음 시작하는 사람도 **위에서부터 순서대로 명령어를 복사해서 터미널에 붙여넣기만 하면 100% 동일하게 동작**하도록 작성된 실전 구축 가이드입니다.

---

##  Step 1. MinIO 로컬 S3 스토리지 배포

```bash
# 1. MinIO 배포 (Namespace, Secret, PVC, Deployment, Service 일괄 생성)
kubectl apply -f minio/minio.yaml

# 2. MinIO 파드 기동 확인 (1/1 Running 될 때까지 대기)
kubectl get pods -n minio -w
```

---

##  Step 2. MinIO 웹 대시보드 접속 (포트포워딩)

MinIO 콘솔과 S3 API가 원활하게 통신할 수 있도록 **9000번(API)과 9001번(콘솔)** 포트를 동시에 포트포워딩합니다:

```bash
# S3 API(9000) 및 웹 콘솔(9001) 동시 포트포워딩
kubectl port-forward -n minio svc/minio-service 9000:9000 9001:9001
```

-  **웹 대시보드 URL:** [http://localhost:9001](http://localhost:9001)
-  **로그인 계정:**
  - **Username:** `minioadmin`
  - **Password:** `minioadmin123`

---

##  Step 3. 필수 버킷(Bucket) 생성

MinIO 웹 콘솔에 로그인한 뒤, 좌측 메뉴의 **Buckets  Create Bucket**을 클릭하여 아래 2개의 버킷을 생성합니다:

1. **`features`**: Spark가 가공한 머신러닝/딥러닝 피처 Parquet 데이터셋 저장용
2. **`models`**: 딥러닝(Keras/PyTorch) 학습 완료된 모델 아티팩트(`my_model.keras` 등) 저장용

---

##  Step 4. 내부 서비스 연결 정보 (K8s 클러스터 내부용)

- **S3 API 엔드포인트 URL:** `http://minio-service.minio.svc:9000`
- **Access Key:** `minioadmin`
- **Secret Key:** `minioadmin123`
