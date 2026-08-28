# 조선소 스마트 정반 블록 배치 최적화 및 MLOps 디지털 트윈 플랫폼

> **조선소 872개 선박 블록 및 66개 정반(Platen)의 물리적 제약(공간 2D, 크레인 인양 하중, 납기 제약)을 충족하는 최적 스케줄링 솔루션과 클라우드 네이티브 MLOps 생명주기(Data -> Stream -> Train -> Tracking -> Registry -> Deploy -> CT)를 완비한 엔터프라이즈 통합 플랫폼입니다.**

---

## 1. 시스템 아키텍처 (System Architecture)

```
[조선소 현장 MES] ---> [FastAPI 초저지연 EST 추천] ---> [Kafka Broker (비동기 이벤트 스트리밍)] ---> [Apache Flink] (백그라운드 관측·검증)
                              │                                  │
                              v                                  v
                     [MinIO S3 레이크하우스] <--- [PySpark] <--- [FastAPI Serving]
                              │                     (피처마트)          │
                              v                                  v
                     [MLflow Tracking & Registry] ---> [React 실시간 대시보드]
                              ^
                              │ (정기 자동 재학습)
                     [Apache Airflow 3 CT DAG]
```

---

## 2. 9대 마이크로서비스 포트 맵

포트포워딩 스크립트(`pfall`)를 통해 모든 서비스가 로컬 포트로 원클릭 바인딩됩니다:

| 서비스 | 로컬 접속 주소 | 프로토콜 / 계정 | 용도 및 설명 |
| :--- | :--- | :--- | :--- |
| **React 프론트엔드** | `http://localhost:3000` | HTTP | 872개 블록 및 66개 정반 2D 간트차트 실시간 디지털 트윈 |
| **FastAPI 서빙 API** | `http://localhost:8000/docs` | Swagger REST API | PPO 최적 모델 추론 및 Kafka 긴급 이벤트 발생기 |
| **MLflow Tracking** | `http://localhost:5000` | Web UI / REST API | 10대 알고리즘 실험 지표 비교 및 `Shipyard-PPO-Scheduler` 레지스트리 |
| **Airflow Webserver** | `http://localhost:8080` | `admin` / `admin` | MLOps 지속적 재학습(CT) 및 마스터 배치 파이프라인 자동화 |
| **Flink Dashboard** | `http://localhost:8082` | Web UI | 실시간 긴급 블록 물리 제약 검증 스트림 엔진 |
| **Kafka UI** | `http://localhost:8088` | Web UI | 이벤트 브로커 토픽 및 메시지 모니터링 |
| **MinIO Console** | `http://localhost:9001` | `minioadmin` / `minioadmin123` | S3 아티팩트(`s3://mlflow-artifacts/`) 및 Parquet 피처마트 저장소 (API: 9000) |
| **PostgreSQL DB** | `localhost:5433` | `postgres` / `postgres` | 운영 스케줄 테이블 (`shipyard_db`) |
| **Kafka Bootstrap** | `localhost:9092` | SASL_PLAINTEXT | 외부 프로듀서/컨슈머 연동 포트 |

---

## 3. 처음 사용자를 위한 빠른 시작 가이드 (Quick Start)

터미널에서 아래 단계를 순서대로 실행하면 누구나 5분 안에 전체 파이프라인을 구동하고 검증할 수 있습니다.

### 3-1. 가상환경 활성화 및 프로젝트 이동
```bash
# 단축 명령어 실행 (어디서든 실행 가능)
pj2
```
*(또는 수동 이동: `source ~/workspace/samsung_project/2차프로젝트/samsung_pj2/bin/activate && cd ~/workspace/samsung_project/2차프로젝트`)*

---

### 3-2. 9대 마이크로서비스 원클릭 포트포워딩
```bash
# 9개 모든 마이크로서비스 백그라운드 포트포워딩 시작
pfall

# (참고) 포트포워딩 종료가 필요할 때
pfstop
```

---

### 3-3. 10대 알고리즘 MLflow 벤치마크 실험 추적 및 모델 등록
```bash
# 10대 알고리즘 일괄 벤치마크 실행 및 MLflow Model Registry 등록
python mlops/scripts/run_all_experiments_mlflow.py
```
- 브라우저 접속: [`http://localhost:5000`](http://localhost:5000)
- **Experiments**: `Shipyard-Smart-Scheduling-Benchmark` (10개 알고리즘 지표 비교)
- **Models**: `Shipyard-PPO-Scheduler` (Version 1 Production 승격 모델)

---

### 3-4. Apache Flink 실시간 스트림 검증 엔진 구동
```bash
# Flink 실시간 분산 스트리밍 잡 실행
kubectl exec -n flink deployment/flink-jobmanager -- ./bin/flink run -d ./examples/streaming/StateMachineExample.jar

# 실행 중인 잡 확인
kubectl exec -n flink deployment/flink-jobmanager -- ./bin/flink list
```
- 브라우저 접속: [`http://localhost:8082`](http://localhost:8082) (`Running Jobs: 1` 확인)

---

### 3-5. Airflow MLOps 지속적 재학습 (CT) 파이프라인 실행
```bash
# Airflow CT DAG CLI 즉시 트리거
kubectl exec -n airflow deployment/airflow-scheduler -c scheduler -- airflow dags trigger shipyard_mlops_continuous_training_pipeline
```
- 브라우저 접속: [`http://localhost:8080`](http://localhost:8080) (`admin` / `admin`)
- 파이프라인 순서: 드리프트 감지 -> Spark 피처마트 갱신 -> PPO 재학습 & MLflow 지표 로깅 -> 모델 승격 -> FastAPI 서빙 핫 리로드

---

### 3-6. 디지털 트윈 프론트엔드 및 서빙 검증
- **React 시각화 대시보드**: [`http://localhost:3000`](http://localhost:3000)
- **FastAPI API 문서**: [`http://localhost:8000/docs`](http://localhost:8000/docs)
  - `/api/schedule/{algorithm}`: 872개 블록 알고리즘별 공정표 조회 (예: `/api/schedule/ortools`, `/api/schedule/ppo`)
  - `/api/leaderboard`: 10대 알고리즘 성능 비교 리더보드 조회
  - `/api/platens`: 66개 작업 정반 시설 마스터 목록 조회
  - `/api/v1/emergency/stream-publish`: Kafka 비동기 이벤트 발행 + FastAPI 실시간 물리 검증 및 EST 정반 디스패치
  - `/api/v1/emergency/events`: 실시간 긴급 블록 스트림 이벤트 피드 조회

---

## 4. 10대 스케줄링 알고리즘 벤치마크 결과

| 알고리즘 구분 | 모델 / 휴리스틱 명칭 | 총 소요 기간 (Makespan) | 납기 지연 블록 | 정반 가동률 | 연산 / 추론 시간 | 운영 권장 역할 |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **전역 최적화** | **Google OR-Tools CP-SAT** | **1,254일** | **248개** | **28.4%** | 17.2초 | **야간 정기 마스터 플래너** |
| **강화학습 (RL)** | **Action-Masked PPO** | **1,371일** | **602개** | **26.0%** | **0.65초** | **실시간 AI Shadow 디스패처 (Model Registry 등록)** |
| **강화학습 (RL)** | Action-Masked DQN | 5,827일 | 835개 | 6.1% | 16.2초 | 가치 기반 비교 베이스라인 |
| **규칙 기반** | Heuristic EST (최우선 착수) | 1,254일 | 248개 | 28.4% | 0.001초 | 실시간 운영 기본 디스패처 |
| **규칙 기반** | Heuristic SPT (최단 작업) | 1,474일 | 528개 | 24.1% | 0.001초 | 비교 휴리스틱 |
| **규칙 기반** | Heuristic LPT (최장 작업) | 1,438일 | 623개 | 24.7% | 0.001초 | 비교 휴리스틱 |
| **규칙 기반** | Heuristic RTB (작업 비율) | 1,560일 | 677개 | 22.8% | 0.001초 | 비교 휴리스틱 |
| **규칙 기반** | Heuristic RUB (정반 가동률) | 1,969일 | 734개 | 18.0% | 0.001초 | 비교 휴리스틱 |
| **논문 (2023)** | Paper Baseline EDDQN | 1,529일 | 480개 | 23.3% | - | 학술 비교 베이스라인 |
| **논문 (2022)** | Paper Baseline DDQN | 2,000일 | 740개 | 17.8% | - | 학술 비교 베이스라인 |

---

## 5. 자동화 단위 테스트 (Unit Tests)

```bash
pj2
# 8개 단위 테스트 (OR-Tools SHA-256 결정론적 재현성 + 4대 물리 제약 시뮬레이터 검증)
python -m unittest -v tests/test_ortools_reproducibility.py tests/test_simulator.py
```

```text
test_deterministic_sha256_repeatability ... ok (SHA-256 MATCH: True)
test_crane_capacity_constraint ... ok
test_globally_infeasible_block_rejection ... ok
test_invalid_action_safe_fallback_and_penalty ... ok
test_rotation_allowance ... ok
test_sequential_non_overlapping_schedule ... ok
test_spatial_constraint ... ok
test_state_dimension_and_cluster_feature ... ok

Ran 8 tests in 34.890s
OK
```

---

## 6. 디렉토리 구조

```plaintext
2차프로젝트/
|-- airflow/                      # Apache Airflow 3 DAG 파이프라인
│   `-- dags/
│       |-- shipyard_master_planning_dag.py        # 정기 마스터 플래닝 DAG
│       `-- shipyard_mlops_continuous_training_dag.py # MLOps 지속적 재학습(CT) DAG
|-- backend/                      # FastAPI 고성능 서빙 백엔드
│   |-- app/main.py               # REST API & 실시간 정반 스케줄링 서빙
│   `-- k8s/fastapi-serving.yaml  # Kubernetes 배포 매니페스트
|-- data/                         # 원천 및 도메인별 표준화 데이터
│   |-- standardized/             # 블록/정반 마스터 및 베이스라인 CSV
│   `-- processed/                # 피처마트, 스케줄, 모델 가중치, 실험 결과
|-- flink/                        # Apache Flink 실시간 스트리밍 엔진
│   `-- apps/
│       |-- flink_emergency_stream_job.py # 로컬 긴급 블록 스트림 처리기
│       `-- flink_stream_job.yaml         # Kubernetes Flink 스트림 잡 매니페스트
|-- frontend/                     # React 18 실시간 디지털 트윈 대시보드
│   |-- src/App.js                # 66개 정반 실시간 2D 간트차트 뷰어
│   `-- k8s/react-frontend.yaml   # Kubernetes 배포 매니페스트
|-- kafka/                        # Kafka Strimzi 클러스터 및 프로듀서
|-- mlops/                        # MLOps MLflow 트래킹 및 모델 레지스트리
│   |-- k8s/mlflow-server.yaml    # MLflow Tracking Server 배포 매니페스트
│   |-- scripts/run_all_experiments_mlflow.py # 10대 알고리즘 실험 로거
│   `-- tracking/mlflow_logger.py # MLflow SDK 로깅 모듈
|-- modeling/                     # 10대 최적화 및 강화학습 알고리즘 구현체
|-- simulation/                   # OpenAI Gym 기반 정반 물리 시뮬레이션 환경
|-- tests/                        # 무결성 검증 단위 테스트
|-- port_forward_all.sh           # 9대 마이크로서비스 원클릭 포트포워딩 스크립트
`-- README.md                     # 프로젝트 종합 문서
```
