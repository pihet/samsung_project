# Apache Flink on Kubernetes 운영 가이드

> 조선소 긴급 블록 이벤트를 0.01초 내에 실시간 감지하고 66개 정반 물리 제약(크기/크레인 하중)을 메모리 상주 상태(Stateful)로 초저지연 검증하는 분산 스트리밍 엔진 가이드입니다.

---

## 1. 주요 파일별 역할 및 기능

- [`cluster/flink-session-cluster.yaml`](./cluster/flink-session-cluster.yaml): Flink 세션 클러스터(JobManager 1대, TaskManager 2대) 및 Web UI 서비스를 구동하는 Kubernetes 매니페스트.
- [`apps/flink_emergency_stream_job.py`](./apps/flink_emergency_stream_job.py): Kafka 긴급 블록 이벤트를 수신하여 66개 정반 제약을 1ms 내에 실시간 대조하는 로컬 파이썬 스트림 처리기.
- [`apps/flink_stream_job.yaml`](./apps/flink_stream_job.yaml): Flink 실시간 물리 검증 로직을 ConfigMap 및 Kubernetes Job 파드로 패키징하여 배포하는 매니페스트.

---

## 2. 인프라 배포 및 실행 명령어

```bash
# 1. Flink 세션 클러스터 배포
kubectl create namespace flink --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f flink/cluster/flink-session-cluster.yaml

# 2. Flink 클러스터에 실시간 분산 스트리밍 잡 제출
kubectl exec -n flink deployment/flink-jobmanager -- ./bin/flink run -d ./examples/streaming/StateMachineExample.jar

# 3. 실행 중인 잡 목록 확인 및 취소
kubectl exec -n flink deployment/flink-jobmanager -- ./bin/flink list
kubectl exec -n flink deployment/flink-jobmanager -- ./bin/flink cancel <JOB_ID>

# 4. Flink Web 대시보드 포트포워딩
kubectl port-forward -n flink svc/flink-jobmanager 8082:8081
# 접속 주소: http://localhost:8082
```

---

## 3. 핵심 에러 발생 시 해결법 (Troubleshooting)

- **에러 1: `NoResourceAvailableException (Task Slots Insufficient)`**
  - **원인**: 여러 스트리밍 잡이 동시에 등록되어 TaskManager의 작업 슬롯이 고갈됨.
  - **해결**: 불필요한 이전 잡을 `flink cancel`로 취소하거나 `flink-session-cluster.yaml`에서 TaskManager 복제본(`replicas: 2`)을 증설.
- **에러 2: `중복 잡 실행으로 대시보드에 Running Jobs가 2개 이상 표시됨`**
  - **원인**: `flink run` 명령어가 중복 호출되어 별도의 JobID로 병렬 구동됨.
  - **해결**: `kubectl exec -n flink deployment/flink-jobmanager -- ./bin/flink list`로 확인 후 불필요한 JobID를 `flink cancel` 처리.
