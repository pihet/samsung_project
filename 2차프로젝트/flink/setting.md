# Apache Flink on Kubernetes 실시간 스트리밍 빠른 시작 가이드 (setting.md)

이 문서는 조선소 스마트 정반 스케줄링 시스템에서 **돌발 긴급 블록 이벤트를 0.01초 만에 실시간으로 감지하고 물리 제약(크기/크레인 하중)을 사전 검증하는 Apache Flink 분산 스트리밍 클러스터 구축 가이드**입니다.

---

## 1. 아키텍처 상의 Flink 역할

```
[조선소 현장] ──▶ [Kafka: shipyard.emergency.blocks] 
                       │ (실시간 스트림)
                       ▼
            [Apache Flink on K8s]
             ├─ 1) 실시간 이벤트 역직렬화 (JSON Parse)
             ├─ 2) 66개 정반 물리 제약 메모리 대조 (Stateful Filter)
             └─ 3) 적합 후보 정반 리스트 태깅 후 FastAPI 전달
                       │
                       ▼
            [FastAPI ➔ EST 배정 & PPO Shadow AI] ➔ [PostgreSQL / MLflow]
```

---

## 2. Flink 세션 클러스터 (JobManager + TaskManager) 배포

```bash
# 1. flink 네임스페이스 생성
kubectl create namespace flink --dry-run=client -o yaml | kubectl apply -f -

# 2. Flink JobManager 및 TaskManager 배포
kubectl apply -f flink/cluster/flink-session-cluster.yaml

# 3. 파드 기동 확인 (1/1 Running 확인)
kubectl get pods -n flink -w
```

---

## 3. Flink Web UI 대시보드 접속

```bash
# Flink 대시보드 포트포워딩 (로컬 8082 포트)
kubectl port-forward -n flink svc/flink-jobmanager 8082:8081
```
- 브라우저 접속: [`http://localhost:8082`](http://localhost:8082)
