# Apache Spark on Kubernetes 운영 가이드

> Spark Operator 기반 분산 처리 엔진으로, 대규모 블록 제조 데이터 피처 엔지니어링 및 MinIO Iceberg 피처마트(Parquet) 생성을 수행하는 가이드입니다.

---

## 1. 주요 파일별 역할 및 기능

- [`apps/spark_feature_pipeline.py`](./apps/spark_feature_pipeline.py): PySpark를 통해 872개 블록 및 66개 정반의 4대 피처마트(Master, Workload, Cluster, Feature)를 분산 추출하여 MinIO에 Parquet로 저장하는 핵심 파이프라인.
- [`apps/create_iceberg_tables.py`](./apps/create_iceberg_tables.py): MinIO S3 및 SQLite 카탈로그 기반으로 Apache Iceberg 테이블 스키마를 초기화하는 스크립트.
- [`apps/spark_kafka_consumer.py`](./apps/spark_kafka_consumer.py): Kafka 토픽 스트림을 실시간 구독하여 MinIO 데이터 레이크하우스로 분산 적재하는 PySpark 컨슈머.
- [`apps/spark-kafka-job.yaml`](./apps/spark-kafka-job.yaml): SparkApplication CRD를 통해 클러스터 내 Driver와 Executor를 자동 생성/소멸시키는 Kubernetes 분산 잡 매니페스트.

---

## 2. 인프라 배포 및 실행 명령어

```bash
# 1. Spark Operator 설치 및 RBAC 권한 구성
helm upgrade --install spark-operator spark-operator/spark-operator \
  --namespace spark-operator --create-namespace --set webhook.enable=true
kubectl create serviceaccount spark -n spark --dry-run=client -o yaml | kubectl apply -f -
kubectl create clusterrolebinding spark-role --clusterrole=edit --serviceaccount=spark:spark --namespace=spark --dry-run=client -o yaml | kubectl apply -f -

# 2. PySpark 피처 엔지니어링 파이프라인 로컬 실행
pj2
python spark/apps/spark_feature_pipeline.py

# 3. Kubernetes SparkApplication 분산 작업 제출
kubectl apply -f spark/apps/spark-kafka-job.yaml
kubectl get sparkapplications -n spark -w
```

---

## 3. 핵심 에러 발생 시 해결법 (Troubleshooting)

- **에러 1: `Spark Operator Webhook Connection Refused`**
  - **원인**: Spark Operator의 뮤테이팅 웹훅(Mutating Webhook) 설정이 비활성화되어 Driver 파드 생성이 차단됨.
  - **해결**: Helm 업그레이드 시 `--set webhook.enable=true` 플래그를 추가하고 네임스페이스 서비스 어카운트에 `edit` 권한 바인딩:
    ```bash
    helm upgrade --install spark-operator spark-operator/spark-operator -n spark-operator --set webhook.enable=true
    ```
- **에러 2: `AmazonS3Exception / NoSuchBucket (s3a://...)`**
  - **원인**: MinIO S3에 대상 버킷이 존재하지 않거나 S3A 엔드포인트 URL 설정이 누락됨.
  - **해결**: MinIO S3 버킷을 사전에 생성하고 PySpark 세션 빌더에 `spark.hadoop.fs.s3a.endpoint`와 접근 키를 명시.
