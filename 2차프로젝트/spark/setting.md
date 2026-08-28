# Apache Spark on Kubernetes 운영 가이드

> Spark Operator 기반 분산 데이터 처리 엔진으로, Kafka 스트림 데이터 수집 및 MinIO Iceberg 피처마트(Parquet) 생성을 수행하는 운영 명령어 가이드입니다.

---

## 1. 인프라 배포 및 구성 명령어 (Setup & Deploy)

```bash
# 1. spark 및 spark-operator 네임스페이스 생성
kubectl create namespace spark --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace spark-operator --dry-run=client -o yaml | kubectl apply -f -

# 2. Spark Operator 설치 (Helm)
helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update
helm upgrade --install spark-operator spark-operator/spark-operator \
  --namespace spark-operator \
  --set webhook.enable=true

# 3. Spark RBAC 서비스 계정 및 권한 생성
kubectl create serviceaccount spark -n spark --dry-run=client -o yaml | kubectl apply -f -
kubectl create clusterrolebinding spark-role --clusterrole=edit --serviceaccount=spark:spark --namespace=spark --dry-run=client -o yaml | kubectl apply -f -
```

---

## 2. 상태 확인 및 모니터링 명령어 (Verify & Monitor)

```bash
# 1. Spark Operator 컨트롤러 파드 상태 확인
kubectl get pods -n spark-operator

# 2. Spark Application 실행 현황 확인
kubectl get sparkapplications -n spark

# 3. 실행 중인 Spark Driver 파드 로그 확인
kubectl logs -n spark -l spark-role=driver -f
```

---

## 3. Spark 파이프라인 실행 명령어 (Run & Execute)

```bash
# 가상환경 활성화
pj2

# 방법 1: PySpark 피처 엔지니어링 파이프라인 로컬 실행 (MinIO 피처마트 추출)
python spark/apps/spark_feature_pipeline.py

# 방법 2: Apache Iceberg 테이블 카탈로그 초기화
python spark/apps/create_iceberg_tables.py

# 방법 3: Kubernetes SparkApplication으로 분산 잡 제출
kubectl apply -f spark/apps/spark-kafka-job.yaml
kubectl get sparkapplications -n spark -w
```
