# Apache Airflow 3 on Kubernetes 운영 가이드

> KubernetesExecutor 기반으로 마스터 스케줄링 배치 파이프라인 및 MLOps Continuous Training (CT) 자동화 재학습을 관제하는 Airflow 운영 명령어 가이드입니다.

---

## 1. 인프라 배포 및 구성 명령어 (Setup & Deploy)

```bash
# 1. airflow 네임스페이스 생성
kubectl create namespace airflow --dry-run=client -o yaml | kubectl apply -f -

# 2. Apache Airflow 공식 Helm 차트 저장소 추가
helm repo add apache-airflow https://airflow.apache.org
helm repo update

# 3. KubernetesExecutor 기반 Airflow 3 배포
helm upgrade --install airflow apache-airflow/airflow \
  --namespace airflow \
  -f airflow/values.yaml

# 4. 파드 상태 확인 (API Server, Scheduler, DAG Processor)
kubectl get pods -n airflow
```

---

## 2. 상태 확인 및 모니터링 명령어 (Verify & Monitor)

```bash
# 1. Airflow 웹서버 포트포워딩
kubectl port-forward -n airflow svc/airflow-api-server 8080:8080
# 접속 주소: http://localhost:8080 (계정: admin / admin)

# 2. 등록된 DAG 목록 확인
kubectl exec -n airflow deployment/airflow-scheduler -c scheduler -- airflow dags list

# 3. DAG Processor 파싱 상태 로그 확인
kubectl logs -n airflow -l component=dag-processor --tail=50
```

---

## 3. DAG 파이프라인 트리거 및 실행 명령어 (Run & Execute)

```bash
# 방법 1: MLOps Continuous Training (CT) 지속적 재학습 파이프라인 즉시 트리거
kubectl exec -n airflow deployment/airflow-scheduler -c scheduler -- airflow dags trigger shipyard_mlops_continuous_training_pipeline

# 방법 2: 정기 마스터 플래닝 배치 파이프라인 즉시 트리거
kubectl exec -n airflow deployment/airflow-scheduler -c scheduler -- airflow dags trigger shipyard_master_planning_batch_pipeline

# 방법 3: 특정 DAG의 최신 실행 상태 및 태스크 인스턴스 확인
kubectl exec -n airflow deployment/airflow-scheduler -c scheduler -- airflow dags state shipyard_mlops_continuous_training_pipeline
```
