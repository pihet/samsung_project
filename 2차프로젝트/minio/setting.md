# MinIO Distributed Object Storage 운영 가이드

> S3 호환 오브젝트 스토리지로, MLflow 모델 아티팩트(`s3://mlflow-artifacts/`) 및 PySpark Parquet 피처마트를 보관하는 운영 명령어 가이드입니다.

---

## 1. 인프라 배포 및 구성 명령어 (Setup & Deploy)

```bash
# 1. minio 네임스페이스 생성
kubectl create namespace minio --dry-run=client -o yaml | kubectl apply -f -

# 2. MinIO 스토리지 배포
kubectl apply -f minio/minio.yaml

# 3. 파드 상태 확인
kubectl get pods -n minio
```

---

## 2. 상태 확인 및 모니터링 명령어 (Verify & Monitor)

```bash
# 1. MinIO 웹 콘솔 및 S3 API 포트포워딩
kubectl port-forward -n minio svc/minio-service 9001:9001 9000:9000
# 웹 콘솔: http://localhost:9001 (계정: minioadmin / minioadmin123)
# S3 API : http://localhost:9000
```

---

## 3. 버킷 생성 및 데이터 초기화 명령어 (Run & Execute)

```bash
# 가상환경 활성화
pj2

# 1. MLflow 및 레이크하우스 필수 버킷 생성 (Python boto3)
python -c "
import boto3
s3 = boto3.client('s3', endpoint_url='http://localhost:9000', aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin123')
for b in ['mlflow-artifacts', 'shipyard-lakehouse', 'shipyard-mlops']:
    if b not in [bk['Name'] for bk in s3.list_buckets().get('Buckets', [])]:
        s3.create_bucket(Bucket=b)
        print(f'Created bucket: {b}')
"

# 2. 레이크하우스 메타데이터 및 초기 테이블 적재
python minio/lakehouse_init_tables.py
```
