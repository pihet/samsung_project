# Apache Airflow 3 on Kubernetes 운영 가이드

> KubernetesExecutor 기반으로 마스터 스케줄링 배치 파이프라인 및 MLOps Continuous Training (CT) 자동화 재학습을 관제하는 Airflow 가이드입니다.

---

## 1. 주요 파일별 역할 및 기능

- [`dags/shipyard_master_planning_dag.py`](./dags/shipyard_master_planning_dag.py): MinIO 데이터 감지 -> PySpark 피처 엔지니어링 -> PostgreSQL DB 적재를 수행하는 일간 정기 마스터 플래닝 배치 파이프라인.
- [`dags/shipyard_mlops_continuous_training_dag.py`](./dags/shipyard_mlops_continuous_training_dag.py): 데이터 드리프트 감지 -> 피처마트 갱신 -> PPO 재학습 & MLflow 로깅 -> 모델 레지스트리 승격을 자동화하는 5단계 MLOps CT 파이프라인.
- [`dags/kafka_producer_pipeline.py`](./dags/kafka_producer_pipeline.py): Kafka 브로커로 블록 제조 공정 이벤트를 주기적으로 발행하는 자동화 파이프라인.
- [`values.yaml`](./values.yaml): KubernetesExecutor, PostgreSQL 백엔드, Git-Sync 주기 및 리소스 제한이 정의된 Airflow 3 Helm 설정 파일.

---

## 2. 인프라 배포 및 실행 명령어

```bash
# 1. Apache Airflow 3 Helm 배포
helm repo add apache-airflow https://airflow.apache.org
helm repo update
helm upgrade --install airflow apache-airflow/airflow --namespace airflow --create-namespace -f airflow/values.yaml

# 2. MLOps Continuous Training (CT) 파이프라인 CLI 즉시 트리거
kubectl exec -n airflow deployment/airflow-scheduler -c scheduler -- airflow dags trigger shipyard_mlops_continuous_training_pipeline

# 3. Airflow Webserver 포트포워딩
kubectl port-forward -n airflow svc/airflow-api-server 8080:8080
# 접속 주소: http://localhost:8080 (계정: admin / admin)
```

---

## 3. 핵심 에러 발생 시 해결법 (Troubleshooting)

- **에러 1: `DAG 수정 후 Airflow UI에 즉시 반영되지 않음`**
  - **원인**: Airflow 3에서는 DAG Processor가 독립된 백그라운드 프로세스로 동작하며 일정 주기(Bundle Refresh Interval)마다 파일을 파싱함.
  - **해결**: DAG Processor 로그를 확인하여 파싱 완료 시점을 파악하거나 파드를 재기동:
    ```bash
    kubectl logs -n airflow -l component=dag-processor --tail=30
    ```
- **에러 2: `Task 실행 중 403 Forbidden (MLflow 지표 로깅 실패)`**
  - **원인**: MLflow 3.x의 Host 차단 보안 미들웨어로 인해 `airflow` 네임스페이스에서의 REST API 요청이 거부됨.
  - **해결**: `mlflow-server.yaml`의 구동 인자에 `--allowed-hosts "*"` 플래그를 추가하여 클러스터 내부 통신을 허용.
