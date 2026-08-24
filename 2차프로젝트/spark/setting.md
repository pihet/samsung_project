# ✨ Apache Spark on Kubernetes 빠른 시작 가이드 (setting.md)

이 문서는 처음 시작하는 사람도 **위에서부터 순서대로 명령어를 복사해서 터미널에 붙여넣기만 하면 100% 동일하게 동작**하도록 작성된 실전 구축 가이드입니다.

---

## 📋 0. 사전 준비 (Minikube 기동)

```bash
# Minikube 클러스터 기동
minikube start --driver=docker --cpus=6 --memory=12288
```

---

## 🛠️ Step 1. Spark on K8s Operator 공식 Helm 저장소 등록

쿠버네티스에서 분산 빅데이터 처리를 선언적(CRD)으로 관리할 수 있게 해주는 **Spark Operator**를 사용합니다.

```bash
# 1. Spark Operator 공식 Helm 레포지토리 등록
helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update
```

---

## 🚀 Step 2. Spark Operator 배포 (클러스터 전체 네임스페이스 감시)

```bash
# 1. spark-operator 배포 (클러스터 전체 네임스페이스 감시 및 권한 자동 설정)
helm install spark-operator spark-operator/spark-operator \
  --namespace spark-operator \
  --create-namespace \
  --set webhook.enable=true \
  --set 'spark.jobNamespaces={""}'

# 2. 오퍼레이터 및 웹훅 권한 부여 (v2.x 필수)
kubectl create clusterrolebinding spark-operator-controller-admin --clusterrole=cluster-admin --serviceaccount=spark-operator:spark-operator-controller
kubectl create clusterrolebinding spark-operator-webhook-admin --clusterrole=cluster-admin --serviceaccount=spark-operator:spark-operator-webhook

# 3. 오퍼레이터 파드 기동 확인 (2개 파드 모두 1/1 Running 될 때까지 대기)
kubectl get pods -n spark-operator
```

---

## 🔑 Step 3. Spark 작업을 위한 RBAC(권한) 및 ServiceAccount 생성

Spark Driver 파드가 Executor 파드들을 동적으로 생성하고 통제할 수 있도록 쿠버네티스 권한을 부여합니다.

```bash
# 1. spark 작업용 네임스페이스 생성
kubectl create namespace spark

# 2. spark 전용 서비스 어카운트 및 권한 부여
kubectl create serviceaccount spark -n spark
kubectl create clusterrolebinding spark-role --clusterrole=edit --serviceaccount=spark:spark --namespace=spark
```

---

## 📝 Step 4. 첫 번째 PySpark 분산 애플리케이션(`SparkApplication` CRD) 작성

`spark/examples/spark-pi.yaml` 파일을 작성합니다:

```yaml
# spark/examples/spark-pi.yaml
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
  name: pyspark-pi
  namespace: spark
spec:
  type: Python
  pythonVersion: "3"
  mode: cluster
  image: "docker.io/apache/spark:3.5.1"
  imagePullPolicy: IfNotPresent
  mainApplicationFile: "local:///opt/spark/examples/src/main/python/pi.py"
  sparkVersion: "3.5.1"
  restartPolicy:
    type: Never
  serviceAccount: spark
  driver:
    cores: 1
    coreLimit: "1200m"
    memory: "512m"
    labels:
      version: 3.5.1
    serviceAccount: spark
  executor:
    cores: 1
    instances: 2              # 👈 2대의 Executor 파드가 분산 병렬 연산 수행!
    memory: "512m"
    labels:
      version: 3.5.1
```

---

## 🎯 Step 5. Spark 분산 연산 실행 & 파드 관찰

```bash
# 1. Spark 작업 제출
kubectl apply -f spark/examples/spark-pi.yaml

# 2. Driver 파드와 2대의 Executor 파드가 동적으로 생성되는 과정 관찰
kubectl get pods -n spark -w
```

> **생성되는 파드 흐름:**
> 1. `pyspark-pi-driver` (총괄 지휘자 파드 생성)
> 2. `pyspark-pi-exec-1`, `pyspark-pi-exec-2` (2대의 일꾼 파드가 생성되어 대규모 분산 계산 수행)
> 3. 계산 완료 후 Executor 파드 자동 소멸 ➔ Driver 파드 `Completed` 완료!

### 📊 계산 결과 로그 확인
```bash
# Driver 파드의 콘솔 출력에서 파이(Pi) 계산 결과 확인
kubectl logs -n spark pyspark-pi-driver | grep "Pi is roughly"
```
> **출력 예시:** `Pi is roughly 3.14159265...`

---

## 🌐 Step 6. Kafka ➔ Spark 엔드투엔드 분산 처리 실습

1. **PySpark 데이터 처리 스크립트 작성 (`spark/apps/spark_kafka_consumer.py`):**
   - Kafka `my-topic`에 SCRAM-SHA-512 보안으로 접속.
   - 원천 주문 JSON 데이터 파싱 및 고객별/상품별 분산 집계.

2. **ConfigMap 등록:**
   ```bash
   kubectl create configmap spark-kafka-code \
     --from-file=spark/apps/spark_kafka_consumer.py \
     --namespace spark \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

3. **SparkApplication 배포 (`spark/apps/spark-kafka-job.yaml`):**
   ```bash
   kubectl apply -f spark/apps/spark-kafka-job.yaml
   ```

4. **분산 연산 결과 로그 실시간 확인:**
   ```bash
   kubectl logs -n spark spark-kafka-order-analytics-driver -f
   ```
