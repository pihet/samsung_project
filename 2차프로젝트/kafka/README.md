# Apache Kafka on Kubernetes 운영 가이드

> 조선소 872개 블록 제조 공정 및 돌발 긴급 블록 스트리밍을 담당하는 Strimzi 기반 고가용성(HA) Kafka 브로커 운영 가이드입니다.

---

## 1. 주요 파일별 역할 및 기능

- [`cluster/kafka-ha-cluster.yaml`](./cluster/kafka-ha-cluster.yaml): Strimzi 기반 3-브로커 HA 클러스터 및 KRaft 컨트롤러 노드 배포 매니페스트.
- [`topics/shipyard-topics.yaml`](./topics/shipyard-topics.yaml): 872개 MES 블록 및 실시간 긴급 블록(`shipyard.emergency.blocks`) 토픽 선언 매니페스트.
- [`users/app-user.yaml`](./users/app-user.yaml): SCRAM-SHA-512 기반 클라이언트 보안 인증 계정 및 토픽별 ACL 권한 설정 매니페스트.
- [`producer_mes_blocks.py`](./producer_mes_blocks.py): 872개 마스터 제조 블록 데이터를 Kafka 브로커로 일괄 발행하는 배치 프로듀서.
- [`producer_emergency_stream.py`](./producer_emergency_stream.py): 현장 돌발 상황을 모사하여 0.5초 주기로 긴급 블록 이벤트를 실시간 발행하는 스트림 프로듀서.
- [`consumer_to_iceberg.py`](./consumer_to_iceberg.py): Kafka 토픽의 실시간 메시지를 수신하여 MinIO S3 레이크하우스로 적재하는 컨슈머.
- [`emergency_producer_job.yaml`](./emergency_producer_job.yaml): 긴급 블록 프로듀서를 클러스터 내부 Pod로 실행하는 Kubernetes Job 매니페스트.

---

## 2. 인프라 배포 및 실행 명령어

```bash
# 1. Strimzi Operator 설치 및 Kafka HA 클러스터 배포
helm upgrade --install strimzi-kafka-operator strimzi/strimzi-kafka-operator -n kafka --create-namespace
kubectl apply -f kafka/cluster/kafka-ha-cluster.yaml

# 2. 토픽 및 보안 사용자 계정 배포
kubectl apply -f kafka/topics/shipyard-topics.yaml
kubectl apply -f kafka/users/app-user.yaml

# 3. 긴급 블록 실시간 프로듀서 실행 (로컬)
pj2
python kafka/producer_emergency_stream.py

# 4. Kafka-UI 웹 대시보드 포트포워딩
kubectl port-forward -n kafka svc/kafka-ui 8088:8080
# 접속 주소: http://localhost:8088
```

---

## 3. 핵심 에러 발생 시 해결법 (Troubleshooting)

- **에러 1: `Strimzi Operator CrashLoopBackOff (CRD 버전 불일치)`**
  - **원인**: 구버전 v1beta2 CRD가 클러스터에 남아 최신 오퍼레이터 구동이 거부됨.
  - **해결**: 최신 v1 CRD 재적용 후 오퍼레이터 파드 재기동:
    ```bash
    kubectl apply -f https://github.com/strimzi/strimzi-kafka-operator/releases/download/1.1.0/strimzi-crds-1.1.0.yaml
    kubectl delete pod -n kafka -l name=strimzi-cluster-operator
    ```
- **에러 2: `NoBrokersAvailable` / `AuthenticationFailed (SASL SCRAM)`**
  - **원인**: SASL_PLAINTEXT 포트(9092) 접속 시 유저 비밀번호가 누락되거나 불일치함.
  - **해결**: k8s 시크릿에서 실제 비밀번호를 추출하여 프로듀서 설정에 적용:
    ```bash
    kubectl get secret my-app-user -n kafka -o jsonpath='{.data.password}' | base64 -d
    ```
