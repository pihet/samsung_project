# MinIO Distributed Object Storage 운영 가이드

> S3 호환 고성능 오브젝트 스토리지로, MLflow 모델 아티팩트(`s3://mlflow-artifacts/`) 및 PySpark Parquet 피처마트를 보관하는 스토리지 가이드입니다.

---

## 1. 주요 파일별 역할 및 기능

- [`minio.yaml`](./minio.yaml): MinIO 단일 노드/분산 스토리지 및 Web Console(9001), S3 API(9000) Service 매니페스트.
- [`lakehouse_init_tables.py`](./lakehouse_init_tables.py): S3 버킷 및 SQLite 메타데이터 카탈로그를 생성하고 기본 스키마를 초기화하는 스크립트.

---

## 2. 인프라 배포 및 실행 명령어

```bash
# 1. MinIO 스토리지 배포
kubectl create namespace minio --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f minio/minio.yaml

# 2. MinIO 포트포워딩
kubectl port-forward -n minio svc/minio-service 9001:9001 9000:9000
# 콘솔 접속: http://localhost:9001 (계정: minioadmin / minioadmin123)

# 3. 필수 버킷 초기화 (Python boto3)
pj2
python minio/lakehouse_init_tables.py
```

---

## 3. 핵심 에러 발생 시 해결법 (Troubleshooting)

- **에러 1: `NoSuchBucket (s3://mlflow-artifacts/)`**
  - **원인**: MLflow 실험 로깅 시 대상 버킷이 MinIO에 미리 생성되어 있지 않음.
  - **해결**: Python 또는 AWS CLI를 통해 버킷을 사전 생성:
    ```bash
    python -c "import boto3; s3=boto3.client('s3', endpoint_url='http://localhost:9000', aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin123'); s3.create_bucket(Bucket='mlflow-artifacts')"
    ```
- **에러 2: `SignatureDoesNotMatch (S3 API 인증 거부)`**
  - **원인**: MinIO 서명 버전 불일치 또는 잘못된 Access/Secret Key 입력.
  - **해결**: 클라이언트 설정에서 `s3v4` 서명 방식을 강제 지정하고 `minioadmin` / `minioadmin123` 키를 재확인.
