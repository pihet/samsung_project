# Apache Flink on Kubernetes 운영 가이드

> 조선소 긴급 블록 이벤트를 0.01초 내에 실시간 감지하고 66개 정반 물리 제약을 메모리 상주 상태(Stateful)로 초저지연 검증하는 Flink 클러스터 운영 명령어 가이드입니다.

---

## 1. 인프라 배포 및 구성 명령어 (Setup & Deploy)

```bash
# 1. flink 네임스페이스 생성
kubectl create namespace flink --dry-run=client -o yaml | kubectl apply -f -

# 2. Flink 세션 클러스터 (JobManager + TaskManager 2대) 배포
kubectl apply -f flink/cluster/flink-session-cluster.yaml

# 3. 파드 상태 확인 (1/1 Running 확인)
kubectl get pods -n flink
```

---

## 2. 상태 확인 및 모니터링 명령어 (Verify & Monitor)

```bash
# 1. Flink Web 대시보드 포트포워딩
kubectl port-forward -n flink svc/flink-jobmanager 8082:8081
# 접속 주소: http://localhost:8082

# 2. Flink CLI로 실행 중인 잡 목록 확인
kubectl exec -n flink deployment/flink-jobmanager -- ./bin/flink list

# 3. Flink 잡 취소(종료)
kubectl exec -n flink deployment/flink-jobmanager -- ./bin/flink cancel <JOB_ID>
```

---

## 3. Flink 스트리밍 잡 실행 명령어 (Run & Execute)

```bash
# 가상환경 활성화
pj2

# 방법 1: Flink 클러스터에 실시간 분산 스트리밍 잡 제출 (백그라운드)
kubectl exec -n flink deployment/flink-jobmanager -- ./bin/flink run -d ./examples/streaming/StateMachineExample.jar

# 방법 2: 로컬 파이썬 긴급 블록 스트림 검증기 실행
python flink/apps/flink_emergency_stream_job.py

# 방법 3: Kubernetes 전용 Flink 스트림 Job 배포
kubectl apply -f flink/apps/flink_stream_job.yaml
kubectl logs -n kafka -l job-name=flink-stream-job -f
```
