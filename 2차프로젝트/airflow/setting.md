# 🌪️ Apache Airflow on Kubernetes 빠른 시작 가이드 (setting.md)

이 문서는 처음 시작하는 사람도 **위에서부터 순서대로 명령어를 복사해서 터미널에 붙여넣기만 하면 100% 동일하게 동작**하도록 작성된 실전 구축 가이드입니다.

---

## 📋 0. 사전 준비 (Minikube 기동)

```bash
# Minikube 클러스터 기동
minikube start --driver=docker --cpus=6 --memory=12288
```

---

## 🛠️ Step 1. 공식 Helm 저장소 등록

```bash
# 1. 아파치 에어플로우 공식 레포지토리 추가
helm repo add apache-airflow https://airflow.apache.org

# 2. 최신 차트 목록 업데이트
helm repo update
```

---

## 📝 Step 2. 로컬 최적화 `values.yaml` 생성 (Git-Sync 자동 동기화 포함 ⭐)

Airflow를 가볍고 강력한 **`KubernetesExecutor`**와 **`Git-Sync`** 방식으로 돌리기 위한 설정 파일입니다.

```bash
# airflow 폴더로 이동
cd ~/workspace/k8s_study/airflow
```

`airflow/values.yaml` 파일을 생성하고 아래 내용을 저장합니다:

```yaml
# airflow/values.yaml

# 1. 실행 엔진: KubernetesExecutor (태스크마다 K8s 파드를 동적으로 띄워 실행 ⭐)
executor: "KubernetesExecutor"

# 2. 불필요한 데몬 비활성화 (메모리 절약)
triggerer:
  enabled: false
statsd:
  enabled: false

# 3. 웹서버 설정 (Admin 로그인 계정 자동 생성)
webserver:
  replicas: 1
  defaultUser:
    enabled: true
    role: Admin
    username: admin
    password: admin
    email: admin@example.com
    firstName: Admin
    lastName: User

# 4. 스케줄러 1대
scheduler:
  replicas: 1

# 5. 메타데이터 DB (PostgreSQL 5Gi 영구 디스크)
postgresql:
  enabled: true
  persistence:
    size: 5Gi

# 6. 로그 저장용 영구 볼륨 (워커 파드가 삭제되어도 웹 UI에서 로그 영구 보존 ⭐)
logs:
  persistence:
    enabled: true
    size: 2Gi

# 7. 파이썬 DAG 파일 Git-Sync 자동 동기화 ⭐ (persistence 대신 emptyDir로 모든 파드에 git-sync 사이드카 연동)
dags:
  persistence:
    enabled: false
  gitSync:
    enabled: true
    repo: "https://github.com/pihet/k8s_study.git"   # 👈 내 깃 저장소 주소
    branch: "main"
    subPath: "airflow/dags"                           # 👈 깃 저장소 내 DAG 폴더 경로
    wait: 30                                          # 👈 30초마다 GitHub 자동 동기화!
```

---

## 🚀 Step 3. Airflow 클러스터 최초 배포 및 갱신

```bash
# 1. 최초 배포 시 (create-namespace 포함)
helm install airflow apache-airflow/airflow --namespace airflow --create-namespace -f values.yaml

# 2. values.yaml 수정 후 설정 반영(업그레이드) 시
helm upgrade airflow apache-airflow/airflow --namespace airflow -f values.yaml
```

---

## ⏳ Step 4. 배포 완료 확인 및 웹 UI 접속

```bash
# 1. 파드 기동 상태 실시간 관찰 (약 1~2분 소요, 모두 Running 될 때까지 대기)
kubectl get pods -n airflow -w
```

> **정상 파드 목록 예시:**
> - `airflow-postgresql-0` (1/1 Running)
> - `airflow-scheduler-xxxx` (2/2 Running)
> - `airflow-api-server-xxxx` (1/1 Running)
> - `airflow-dag-processor-xxxx` (3/3 Running - git-sync 포함)

### 🌐 웹 브라우저 접속 (포트포워딩)
```bash
# Airflow 웹 UI 포트포워딩 실행 (8081 포트로 실행)
kubectl port-forward -n airflow svc/airflow-api-server 8081:8080
```
> 🌐 **웹 접속:** 브라우저에서 [`http://localhost:8081`](http://localhost:8081) 접속  
> 🔑 **로그인:** ID: **`admin`** / PW: **`admin`**

---

## 📜 Step 5. 파이썬 DAG 작성 & Git Push (0-Click 자동 반영)

`airflow/dags/hello_k8s_dag.py` 파일을 로컬에서 작성합니다:

```python
# airflow/dags/hello_k8s_dag.py
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'pihet',
    'start_date': datetime(2026, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}

def process_data_logic(**context):
    print("파이썬 데이터 처리 함수가 성공적으로 실행되었습니다!")
    return {"status": "success"}

with DAG(
    dag_id='hello_kubernetes_dag',
    default_args=default_args,
    schedule=None,
    catchup=False,
    tags=['study', 'k8s'],
) as dag:

    task_start = BashOperator(
        task_id='print_start',
        bash_command='echo "Airflow on K8s Pipeline Started!"',
    )

    task_python = PythonOperator(
        task_id='run_python_processing',
        python_callable=process_data_logic,
    )

    task_end = BashOperator(
        task_id='pipeline_finished',
        bash_command='echo "All Tasks Completed Successfully!"',
    )

    task_start >> task_python >> task_end
```

### 🚀 Git Push만 하면 끝! (수동 cp 필요 없음)
```bash
git add airflow/dags/hello_k8s_dag.py
git commit -m "feat: add hello_k8s_dag"
git push origin main
```
> 👉 `git push` 후 약 30초가 지나면 Airflow `git-sync`가 자동으로 깃허브에서 코드를 땡겨와 웹 UI에 즉시 반영합니다!

---

## 🎯 Step 6. DAG 실행 & KubernetesExecutor 일꾼 파드 관찰

1. Airflow 웹 UI([`http://localhost:8081`](http://localhost:8081))의 **`Dags`** 메뉴에서 **`hello_kubernetes_dag`** 클릭.
2. 좌측 상단 **토글 스위치를 `ON`**으로 켜고, 우측 상단 **`Trigger DAG` (▶ 재생 버튼)** 클릭.
3. 터미널 또는 OpenLens에서 `kubectl get pods -n airflow -w`를 보면:
   - 태스크가 실행될 때마다 **`hello-kubernetes-dag-print-start-xxxx`** 일꾼 파드가 동적으로 생성되고,
   - 작업 완료 후 파드가 자동으로 정리(`Completed`)되는 것을 확인할 수 있습니다!

---

## 🛠️ 자주 쓰는 실무 Airflow 명령어 치트시트 (Cheatsheet)

### 1. 파드 및 상태 진단
```bash
# Airflow 전체 파드 상태 조회
kubectl get pods -n airflow

# Git-Sync 동기화 로그 실시간 확인 (코드가 잘 들어오는지 감시)
kubectl logs -n airflow -l component=dag-processor -c git-sync -f

# 스케줄러 로그 확인
kubectl logs -n airflow -l component=scheduler -c scheduler --tail=50
```

### 2. Airflow CLI 디버깅 (스케줄러 파드 내부 실행)
```bash
# 등록된 전체 DAG 목록 확인
kubectl exec -n airflow deploy/airflow-scheduler -c scheduler -- airflow dags list

# DAG 문법 에러(Import Error) 확인 (대시보드에 안 뜰 때 1순위 확인!) ⭐
kubectl exec -n airflow deploy/airflow-scheduler -c scheduler -- airflow dags list-import-errors

# 특정 태스크 단독 테스트 실행 (스케줄러 없이 즉시 실행 테스트)
kubectl exec -n airflow deploy/airflow-scheduler -c scheduler -- airflow tasks test hello_kubernetes_dag print_start 2026-08-24
```

### 3. 웹 UI 포트포워딩
```bash
kubectl port-forward -n airflow svc/airflow-api-server 8081:8080
```
