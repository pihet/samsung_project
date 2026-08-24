# 🚀 Apache Kafka on Kubernetes 빠른 시작 가이드 (setting.md)

이 문서는 처음 시작하는 사람도 **위에서부터 순서대로 명령어를 복사해서 터미널에 붙여넣기만 하면 100% 동일하게 동작**하도록 작성된 실전 구축 가이드입니다.

---

## 📋 0. 사전 준비 (Minikube 기동)

```bash
# Minikube 클러스터 기동 (권장: 6 CPU, 12GB RAM)
minikube start --driver=docker --cpus=6 --memory=12288

# 윈도우 OpenLens 사용자일 경우 동기화
sync-kube
```

---

## 🛠️ Step 1. Strimzi Kafka Operator 설치

Kafka를 쿠버네티스 CRD로 관리해 주는 **Strimzi 오퍼레이터**를 배포합니다.

```bash
# 1. Strimzi 최신 v1 CRD 수동 등록
kubectl apply -f https://github.com/strimzi/strimzi-kafka-operator/releases/download/1.1.0/strimzi-crds-1.1.0.yaml

# 2. Helm 레포지토리 등록 및 업데이트
helm repo add strimzi https://strimzi.io/charts/
helm repo update

# 3. kafka 네임스페이스에 오퍼레이터 배포
helm install strimzi-operator strimzi/strimzi-kafka-operator --namespace kafka --create-namespace

# 4. 오퍼레이터 파드 기동 확인 (1/1 Running 될 때까지 대기)
kubectl get pods -n kafka -l name=strimzi-cluster-operator -w
```

---

## 🏛️ Step 2. Kafka 4.3.1 KRaft 고가용성(HA) 클러스터 배포

ZooKeeper 없이 **컨트롤러 3대 + 브로커 3대 + SCRAM 보안 자물쇠**가 적용된 6대 노드 클러스터를 배포합니다.

```bash
# 1. 클러스터 매니페스트 적용
kubectl apply -f kafka/cluster/kafka-ha-cluster.yaml

# 2. 6대 노드 파드 생성 관찰 (약 1~2분 소요, 모두 1/1 Running 될 때까지 대기)
kubectl get pods -n kafka -l app.kubernetes.io/name=kafka -w
```

---

## 📊 Step 3. Kafka-UI 웹 대시보드 배포

웹 브라우저에서 토픽과 브로커 상태를 볼 수 있는 **Kafka-UI**를 배포합니다.

```bash
# 1. Kafka-UI 배포
kubectl apply -f kafka-ui/kafka-ui.yaml

# 2. 웹 UI 파드 정상 기동 확인
kubectl get pods -n kafka -l app=kafka-ui

# 3. 웹 브라우저 접속을 위한 포트포워딩 실행 (터미널 1개 유지)
kubectl port-forward -n kafka svc/kafka-ui 8080:8080
```
> 🌐 **웹 접속:** 브라우저에서 [`http://localhost:8080`](http://localhost:8080) 접속

---

## 📜 Step 4. 카프카 토픽(`KafkaTopic`) 생성

```bash
# 1. 'my-topic' (파티션 3개, 복제본 3개) 생성
kubectl apply -f kafka/topics/kafka-topic.yaml

# 2. 토픽 생성 완료 상태 확인 (READY: True 확인)
kubectl get kafkatopics -n kafka
```

---

## 🔐 Step 5. 보안 계정(`KafkaUser`) 생성 & 비밀번호 발급

```bash
# 1. SCRAM-SHA-512 인증 계정(my-app-user) 생성
kubectl apply -f kafka/users/app-user.yaml

# 2. 계정 상태 확인 (READY: True 확인)
kubectl get kafkausers -n kafka

# 3. 쿠버네티스 Secret에서 자동 발급된 비밀번호 추출
USER_PASS=$(kubectl get secret -n kafka my-app-user -o jsonpath='{.data.password}' | base64 --decode)
echo "발급된 비밀번호: $USER_PASS"
```

---

## 🧪 Step 6. 메시지 송수신 검증 테스트

### 1) 실시간 수신 대기 (Consumer)
새 터미널 창을 열고 컨슈머를 켜둡니다:
```bash
USER_PASS=$(kubectl get secret -n kafka my-app-user -o jsonpath='{.data.password}' | base64 --decode)

kubectl -n kafka run secure-consumer -ti --image=quay.io/strimzi/kafka:1.2.0-kafka-4.3.1 --rm=true --restart=Never -- /bin/bash -c "
cat <<EOF > /tmp/client.properties
security.protocol=SASL_PLAINTEXT
sasl.mechanism=SCRAM-SHA-512
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required username=\"my-app-user\" password=\"$USER_PASS\";
EOF
bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9092 --topic my-topic --consumer.config /tmp/client.properties --from-beginning
"
```

### 2) 메시지 전송 (Producer)
다른 터미널 창에서 프로듀서로 메시지를 전송합니다:
```bash
USER_PASS=$(kubectl get secret -n kafka my-app-user -o jsonpath='{.data.password}' | base64 --decode)

kubectl -n kafka run secure-producer -ti --image=quay.io/strimzi/kafka:1.2.0-kafka-4.3.1 --rm=true --restart=Never -- /bin/bash -c "
cat <<EOF > /tmp/client.properties
security.protocol=SASL_PLAINTEXT
sasl.mechanism=SCRAM-SHA-512
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required username=\"my-app-user\" password=\"$USER_PASS\";
EOF
bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9092 --topic my-topic --producer.config /tmp/client.properties
"
```
> `>` 프롬프트가 뜨면 메시지(예: `hello kafka!`)를 입력하고 엔터를 칩니다. 컨슈머 화면에 메시지가 즉시 출력되면 성공!
