# Apache Kafka on Kubernetes (Strimzi Operator & Kafka-UI)

Kubernetes(Minikube) 환경에서 **Strimzi Kafka Operator**를 사용하여 Apache Kafka(KRaft 모드)와 **Kafka-UI 웹 대시보드**를 구축하고, **OpenLens GUI 연동 및 실전 트러블슈팅**을 체계적으로 정리한 실습 문서입니다.

---

## 📑 목차
1. [전체 아키텍처 구성](#1-전체-아키텍처-구성)
2. [Kafka 4.x & Strimzi 버전 선택 가이드](#2-kafka-4x--strimzi-버전-선택-가이드)
3. [배포 절차 및 매니페스트](#3-배포-절차-및-매니페스트)
   - [3-1. Strimzi Operator 설치](#3-1-strimzi-operator-설치)
   - [3-2. Kafka 4.3.1 KRaft 단일 노드 클러스터 배포](#3-2-kafka-431-kraft-단일-노드-클러스터-배포)
   - [3-3. Kafka-UI 웹 대시보드 배포](#3-3-kafka-ui-웹-대시보드-배포)
4. [외부 접속 및 GUI 모니터링 (OpenLens / Web UI)](#4-외부-접속-및-gui-모니터링-openlens--web-ui)
5. [🔥 실전 트러블슈팅 케이스 스터디 (Issues & Solutions)](#5--실전-트러블슈팅-케이스-스터디-issues--solutions)
   - [Case 1: Strimzi Operator CrashLoopBackOff (CRD 버전 불일치)](#case-1-strimzi-operator-crashloopbackoff-crd-버전-불일치)
   - [Case 2: Kafka 리스너 수정 시 Validation 에러 (`tls: Required value`)](#case-2-kafka-리스너-수정-시-validation-에러-tls-required-value)
   - [Case 3: OpenLens 연결 실패 (`proxy exited with code: 255`)](#case-3-openlens-연결-실패-proxy-exited-with-code-255)
   - [Case 4: OpenLens에서 네임스페이스 선택 후에도 Pod가 빈 화면(0 items)으로 보이는 현상](#case-4-openlens에서-네임스페이스-선택-후에도-pod가-빈-화면0-items으로-보이는-현상)
6. [주요 학습 포인트 정리](#6-주요-학습-포인트-정리)

---

## 1. 전체 아키텍처 구성

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Kubernetes Cluster (Minikube)                      │
│                                                                             │
│  [ Strimzi Cluster Operator ]                                               │
│    └─ CRD 감시 & 카프카 인프라 생명주기 관리                                 │
│                                                                             │
│  [ Kafka Broker & Controller (KRaft) ]  (Pod: my-cluster-dual-role-0)       │
│    ├─ Port 9092 (Internal Plain) ◀─────────────┐ (ClusterIP)                │
│    ├─ Port 9093 (Internal TLS)                 │                            │
│    ├─ Port 9094 (External NodePort: 3xxxx)     │                            │
│    └─ Storage: PersistentClaim 10Gi (Bound)    │                            │
│                                                │ (내부 통신)                 │
│  [ Kafka-UI Dashboard ]  (Pod: kafka-ui) ──────┘                            │
│    └─ Port 8080 (ClusterIP) ──(port-forward: 8080)──► [ 웹 브라우저 (Chrome) ]│
└─────────────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ (kubectl config flatten 인증서 연동)
                         [ OpenLens GUI 툴 ]
```

---

## 2. Kafka 4.x & Strimzi 버전 선택 가이드

1. **Kafka 4.x의 핵심 변화 (KRaft 전용)**:
   - ZooKeeper가 완전히 제거되고 **KRaft(Kafka Raft)** 모드만 지원됩니다.
   - Broker와 Controller 역할을 정의하기 위해 `KafkaNodePool` 리소스를 필수로 사용합니다.
2. **Strimzi CRD v1 표준**:
   - Strimzi 1.0.0 이후부터 기존 `v1beta2` 등이 폐기되고 `apiVersion: kafka.strimzi.io/v1`이 필수입니다.
3. **버전 선택 기준**:
   - 신규 구축 시 최신 안정 버전인 **Kafka 4.3.1 / 4.3.0**을 최우선 권장합니다.

---

## 3. 배포 절차 및 매니페스트

### 3-1. Strimzi Operator 설치
```bash
# 1. Strimzi 1.1+ 최신 CRD 수동 등록
kubectl apply -f https://github.com/strimzi/strimzi-kafka-operator/releases/download/1.1.0/strimzi-crds-1.1.0.yaml

# 2. Helm 저장소 추가 및 Operator 배포
helm repo add strimzi https://strimzi.io/charts/
helm repo update
helm install strimzi-operator strimzi/strimzi-kafka-operator --namespace kafka --create-namespace
```

### 3-2. Kafka 4.3.1 KRaft 단일 노드 클러스터 배포
[`cluster/kafka-single-node.yaml`](./cluster/kafka-single-node.yaml)
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: dual-role
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 1
  roles:
    - controller
    - broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 10Gi
        kraftMetadata: shared
---
apiVersion: kafka.strimzi.io/v1
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
spec:
  kafka:
    version: 4.3.1
    metadataVersion: 4.3-IV0
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
      - name: tls
        port: 9093
        type: internal
        tls: true
      - name: external
        port: 9094
        type: nodeport
        tls: false
    config:
      offsets.topic.replication.factor: 1
      transaction.state.log.replication.factor: 1
      transaction.state.log.min.isr: 1
      default.replication.factor: 1
      min.insync.replicas: 1
  entityOperator:
    topicOperator: {}
    userOperator: {}
```
```bash
kubectl apply -f cluster/kafka-single-node.yaml
```

### 3-3. Kafka 4.3.1 KRaft 고가용성(HA) 분리형 클러스터 배포 (Controller 3대 + Broker 3대)
[`cluster/kafka-ha-cluster.yaml`](./cluster/kafka-ha-cluster.yaml)
```yaml
# 1. Controller 노드풀 (3대) - KRaft 메타데이터 Quorum
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: controller
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
    - controller
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 5Gi
        kraftMetadata: shared
---
# 2. Broker 노드풀 (3대) - 실제 데이터 분산 저장 및 트래픽 처리
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: broker
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
    - broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 5Gi
        kraftMetadata: shared
---
# 3. Kafka 클러스터 메인 설정
apiVersion: kafka.strimzi.io/v1
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
spec:
  kafka:
    version: 4.3.1
    metadataVersion: 4.3-IV0
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
        authentication:
          type: scram-sha-512
      - name: tls
        port: 9093
        type: internal
        tls: true
    authorization:
      type: simple
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
      default.replication.factor: 3
      min.insync.replicas: 2
  entityOperator:
    topicOperator: {}
    userOperator: {}
```
```bash
# 배포
kubectl apply -f cluster/kafka-ha-cluster.yaml
```

### 3-4. Kafka 토픽 배포 (`KafkaTopic` CRD)
[`topics/kafka-topic.yaml`](./topics/kafka-topic.yaml)
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: my-topic
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 3
  replicas: 3
  config:
    retention.ms: "7200000"
    segment.bytes: "10485760"
```
```bash
kubectl apply -f topics/kafka-topic.yaml
```

### 3-5. KafkaUser 보안 계정 & ACL 권한 배포 (`KafkaUser` CRD)
[`users/app-user.yaml`](./users/app-user.yaml)
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: my-app-user
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: my-topic
          patternType: literal
        operations:
          - All
      - resource:
          type: group
          name: "*"
          patternType: literal
        operations:
          - Read
```
```bash
kubectl apply -f users/app-user.yaml
```

### 3-6. Kafka-UI 웹 대시보드 배포
[`../kafka-ui/kafka-ui.yaml`](../kafka-ui/kafka-ui.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kafka-ui
  namespace: kafka
  labels:
    app: kafka-ui
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kafka-ui
  template:
    metadata:
      labels:
        app: kafka-ui
    spec:
      containers:
        - name: kafka-ui
          image: provectuslabs/kafka-ui:latest
          ports:
            - containerPort: 8080
          env:
            - name: KAFKA_CLUSTERS_0_NAME
              value: "my-cluster"
            - name: KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS
              value: "my-cluster-kafka-bootstrap.kafka.svc:9092"
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: kafka-ui
  namespace: kafka
spec:
  type: ClusterIP
  ports:
    - port: 8080
      targetPort: 8080
  selector:
    app: kafka-ui
```
```bash
kubectl apply -f kafka-ui.yaml
```

---

## 4. 외부 접속 및 GUI 모니터링 (OpenLens / Web UI)

### 1) Kafka-UI 웹 대시보드 접속
```bash
kubectl port-forward -n kafka svc/kafka-ui 8080:8080
```
- 브라우저 접속: `http://localhost:8080`

### 2) OpenLens에서 쿠버네티스 & 카프카 리소스 확인
- **Pod/Deployment**: `Workloads ➔ Pods`에서 상단 네임스페이스를 `kafka`로 선택
- **Kafka CRD**: 좌측 하단 `Custom Resources` ➔ `kafka.strimzi.io` ➔ `Kafkas`, `KafkaTopics` 확인

---

## 5. 🔥 실전 트러블슈팅 케이스 스터디 (Issues & Solutions)

### Case 1: Strimzi Operator CrashLoopBackOff (CRD 버전 불일치)
- **증상**: 오퍼레이터 파드가 `Running`과 `Error`를 반복하며 재시작.
- **진단 (`kubectl logs --previous`)**:
  ```text
  Failure executing: GET at: .../apis/kafka.strimzi.io/v1/namespaces/kafka/kafkamirrormaker2s. Message: Not Found.
  ```
- **원인**:
  - Helm은 기존 클러스터의 CRD를 자동 업그레이드하지 않아 구버전(`v1beta2`) CRD가 남아있었음.
  - 최신 1.1+ 오퍼레이터는 `v1` API를 요청했으나 API Server가 404를 반환.
  - `kubectl apply`로 CRD 갱신 시 k8s `status.storedVersions` 제약으로 실패.
- **해결**:
  ```bash
  # 구버전 CRD 삭제 -> 최신 v1 CRD 재적용 -> 오퍼레이터 파드 재기동
  kubectl get crd -o name | grep strimzi.io | xargs kubectl delete
  kubectl apply -f https://github.com/strimzi/strimzi-kafka-operator/releases/download/1.1.0/strimzi-crds-1.1.0.yaml
  kubectl delete pod -n kafka -l name=strimzi-cluster-operator
  ```

---

### Case 2: Kafka 리스너 수정 시 Validation 에러 (`tls: Required value`)
- **증상**: `kubectl apply -f kafka-single-node.yaml` 실행 시 아래 에러와 함께 거부됨:
  ```text
  The Kafka "my-cluster" is invalid: spec.kafka.listeners[1].tls: Required value
  ```
- **원인**:
  - `listeners[1]` (`name: tls`)에서 필수 필드인 `tls: true` 라인이 누락되어 CRD 스키마 검증 실패.
- **해결**:
  - 모든 리스너 항목(`plain`, `tls`, `external`)에 `tls: true/false` 명시.

---

### Case 3: OpenLens 연결 실패 (`proxy exited with code: 255`)
- **증상**: Windows OpenLens에서 Minikube 클러스터 연결 또는 포트포워딩 시 프로세스가 exit code 255로 종료.
- **원인**:
  1. `~/.kube/config` 내 인증서 파일 경로가 Linux 파일 시스템 경로(`/home/kjc/.minikube/...`)로 되어 있어 Windows OpenLens의 프록시가 인증서를 찾지 못함.
  2. `minikube service ...` 터널 프로세스를 터미널에서 종료(`^C`)하여 연결 스트림이 끊김.
  3. OpenLens의 내장 포트포워드는 HTTP 웹 전용인데 Kafka 브로커는 TCP 바이너리 통신 프로토콜임.
- **해결**:
  - 인증서 파일 경로 대신 Base64 데이터가 텍스트로 내장된 Kubeconfig 추출 후 OpenLens에 등록:
  ```bash
  kubectl config view --flatten --minify
  ```
  - 출력된 YAML 전체를 복사하여 OpenLens의 `Add Cluster (Paste as text)`로 추가.

---

### Case 4: OpenLens에서 네임스페이스 선택 후에도 Pod가 빈 화면(0 items)으로 보이는 현상
- **증상**: Namespaces 테이블에서 `kafka` 체크박스를 선택했음에도 `Workloads ➔ Pods` 화면에 `0 items`로 아무것도 안 뜸.
- **원인**:
  - 좌측 메뉴 `Namespaces` 테이블의 체크박스는 일괄 작업용 선택일 뿐, 활성 필터가 아님.
  - `Pods` 화면 우측 상단의 `Namespace: default` 드롭다운이 여전히 `default`로 설정되어 있었음.
- **해결**:
  - `Pods` 화면 우측 상단의 **`Namespace: default ▼` 드롭다운**을 클릭하여 **`kafka`** (또는 `All Namespaces`)로 변경.

### Case 5: Strimzi v1 KafkaUser CRD의 `operations` 배열(Array) 스키마 검증 에러
- **증상**: `kubectl apply -f app-user.yaml` 실행 시 아래 에러와 함께 거부됨:
  ```text
  The KafkaUser "my-app-user" is invalid: spec.authorization.acls[0].operations in body must be of type array: "string"
  ```
- **원인**:
  - 구버전(v1beta2)에서는 `operation: All` 단수형 문자열을 사용했으나, 최신 Strimzi `v1` CRD에서는 `operations:` 복수형 **배열(Array)** 문법으로 변경됨.
- **해결**:
  - `operations:` 아래에 하이픈(`-`)을 붙여 리스트 형태로 선언:
  ```yaml
  operations:
    - All
  ```

---

## 6. 주요 학습 포인트 정리

1. **Strimzi 선언적 업데이트 (Declarative In-place Update)**:
   - 클러스터를 삭제/재배포할 필요 없이 YAML의 `listeners`, `storage` 등을 수정한 후 `kubectl apply`만 하면 오퍼레이터가 파드를 무중단/안전 롤링 업데이트함.
2. **쿠버네티스 CRD & Helm의 특성**:
   - Helm은 데이터 손실 위험 방지를 위해 CRD를 자동 업그레이드하지 않으므로, 오퍼레이터 버전업 시 CRD 수동 관리가 필수적임.
3. **크로스 플랫폼(Linux ➔ Windows) Kubeconfig 관리**:
   - 서로 다른 OS 간에 `kubeconfig`를 공유할 때는 파일 경로 대신 `--flatten` 플래그로 인증서 데이터를 임베딩하는 방식이 가장 안전함.

---

## 7. 🏢 실무 기업들의 카프카 활용 4대 시나리오

실제 대규모 기업(쿠팡, 토스, 배달의민족, 넷플릭스 등)에서는 구축된 카프카 인프라를 다음과 같이 활용합니다:

1. **DB 변경분 실시간 복제 (CDC: Change Data Capture)**
   - Debezium / Kafka Connect를 통해 RDBMS(MySQL, PostgreSQL)의 binlog를 실시간 감지하여 Elasticsearch, Redis, S3로 실시간 복제.
2. **마이크로서비스(MSA) 비동기 이벤트 분리 (Decoupling & Event-Driven Architecture)**
   - 결제 완료 이벤트 발행 시 주문, 재고, 배송, 알림 서비스가 카프카를 통해 서로 간섭 없이 독립적으로 처리.
3. **대규모 실시간 스트리밍 처리 (Spark Streaming / Flink)**
   - 이상 금융거래 탐지(FDS), 실시간 추천 알고리즘, 위치 추적 등 초당 수십만 건의 데이터를 실시간 분석.
4. **엔터프라이즈 데이터 레이크 수집 (Airflow + Spark ➔ S3 / Data Lake)**
   - 카프카에 적재된 대용량 원시(Raw) 데이터를 Airflow 스케줄러와 Spark 분산 엔진이 주기적으로 정제하여 데이터 레이크에 저장.

