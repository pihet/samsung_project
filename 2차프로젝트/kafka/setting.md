# Apache Kafka on Kubernetes 운영 가이드

> 조선소 872개 블록 제조 공정 및 돌발 긴급 블록 스트리밍을 담당하는 Strimzi 기반 고가용성(HA) Kafka 브로커 운영 명령어 가이드입니다.

---

## 1. 인프라 배포 및 구성 명령어 (Setup & Deploy)

```bash
# 1. kafka 네임스페이스 생성
kubectl create namespace kafka --dry-run=client -o yaml | kubectl apply -f -

# 2. Strimzi Kafka Operator 설치 (Helm)
helm repo add strimzi https://strimzi.io/charts/
helm repo update
helm upgrade --install strimzi-kafka-operator strimzi/strimzi-kafka-operator -n kafka

# 3. Kafka HA 3-브로커 클러스터 배포
kubectl apply -f kafka/cluster/kafka-ha-cluster.yaml

# 4. 토픽(Topics) 및 사용자 보안 계정(SCRAM-SHA-512) 배포
kubectl apply -f kafka/topics/shipyard-topics.yaml
kubectl apply -f kafka/users/app-user.yaml

# 5. Kafka-UI 웹 모니터링 대시보드 배포
kubectl apply -f kafka-ui/kafka-ui.yaml
```

---

## 2. 상태 확인 및 모니터링 명령어 (Verify & Monitor)

```bash
# 1. Kafka 브로커 및 컨트롤러 파드 상태 확인 (1/1 Running 확인)
kubectl get pods -n kafka

# 2. 등록된 Kafka 토픽 목록 확인
kubectl get kafkatopics -n kafka

# 3. Kafka-UI 웹 대시보드 포트포워딩 및 접속
kubectl port-forward -n kafka svc/kafka-ui 8088:8080
# 접속 주소: http://localhost:8088
```

---

## 3. 실시간 프로듀서 & 컨슈머 실행 명령어 (Run & Execute)

```bash
# 가상환경 활성화
pj2

# 방법 1: 로컬에서 872개 MES 블록 이벤트 일괄 발행
python kafka/producer_mes_blocks.py

# 방법 2: 긴급 돌발 블록 실시간 스트림 이벤트 발행
python kafka/producer_emergency_stream.py

# 방법 3: Kubernetes Job으로 긴급 블록 프로듀서 실행
kubectl apply -f kafka/emergency_producer_job.yaml
kubectl logs -n kafka -l job-name=emergency-producer-job -f

# Kafka 토픽 실시간 메시지 컨슘 테스트 (콘솔)
kubectl exec -it -n kafka my-cluster-broker-0 -- bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic shipyard.emergency.blocks \
  --from-beginning
```
