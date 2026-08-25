#  100% On-Premise End-to-End MLOps & Data Platform

> **클라우드(AWS/GCP) 비용 $0**, 폐쇄망 환경을 위한 **Kubernetes(K8s) + Kafka + Spark + Airflow + GPU 가속 + MinIO + FastAPI** 엔드투엔드 데이터 엔지니어링 & MLOps 아키텍처입니다.

---

##  시스템 전체 파이프라인 아키텍처 (Kubernetes Cluster)

```mermaid
flowchart TD
    User[" 사용자 / 클라이언트"] -->|내부망 접속| MetalLB[" MetalLB (L4 LoadBalancer)"]

    subgraph K8s [" On-Premise Kubernetes Cluster (K8s)"]

        Airflow[" Apache Airflow (전체 파이프라인 총괄 오케스트레이터)"]

        %% 1단: 데이터 파이프라인 계층
        subgraph L1 ["1⃣ Data Pipeline Layer (데이터 수집 및 분산 전처리)"]
            direction LR
            SourceDB[(원천 DB / 로그)] --> IngestionPod["수집 파드\n(CDC / 배치 수집)"]
            IngestionPod --> Kafka["Kafka HA 클러스터\n(실시간 메시지 버퍼링)"]
            Kafka --> Spark["Spark on K8s\n(분산 정제 & 피처 가공)"]
        end

        %% 2단: 중앙 공유 스토리지 계층
        subgraph L2 ["2⃣ Storage Layer (로컬 데이터 레이크 & 모델 저장소)"]
            direction LR
            MinIO_Data[("MinIO 피처셋\n(데이터 레이크)")]
            MinIO_Model[("MinIO 모델 저장소\n(버전별 아티팩트)")]
        end

        %% 3단: MLOps 및 서빙 계층
        subgraph L3 ["3⃣ MLOps & Serving Layer (GPU 모델 학습 및 실시간 서빙)"]
            direction LR
            TrainPod["모델 학습 파드\n RTX 3060 Ti 점유"]
            FastAPI["FastAPI 추론 서버\n(REST API)"]
            React["React 웹 대시보드\n(결과 시각화)"]
            FastAPI <--> React
        end

        %% 데이터 파이프라인  스토리지  학습/서빙 흐름
        Spark -->|정제 피처 적재| MinIO_Data
        MinIO_Data -->|피처 로드| TrainPod
        TrainPod -->|학습 모델 등록| MinIO_Model
        MinIO_Model -->|최신 가중치 로드| FastAPI

        %% Airflow 오케스트레이션 제어선
        Airflow -.->|① 수집 스케줄| IngestionPod
        Airflow -.->|② 분산 작업 제출| Spark
        Airflow -.->|③ GPU 학습 트리거| TrainPod
        Airflow -.->|④ 서빙 롤링 재시작| FastAPI
    end

    MetalLB -->|트래픽 분산| React
    MetalLB -->|추론 요청| FastAPI
```

---

##  컴포넌트별 핵심 기능 (Core Capabilities)

| 영역 | 사용 기술 | 담당 핵심 기능 |
| :--- | :--- | :--- |
| **인프라 & 네트워크** | `Kubernetes (K8s)`, `MetalLB` | 엔터프라이즈 온프레미스 K8s 클러스터 운영 및 내부망 L4 로드밸런싱 |
| **CI/CD** | `GitHub Self-Hosted Runner`, `Local Registry` | 폐쇄망 환경 내 빌드, 도커 이미지 패키징, 무중단 배포 자동화 |
| **데이터 인제스천** | `Airflow Ingestion Pod`, `Kafka HA` | 원천 데이터 배치/실시간 수집 및 안전한 분산 큐잉 |
| **분산 ETL / 피처 가공** | `Apache Spark on K8s` | 대규모 실시간/배치 데이터 분산 정제 및 머신러닝 피처 생성 |
| **파이프라인 오케스트레이션**| `Apache Airflow` | 수집  전처리  GPU 학습  서빙 배포 전 단계 의존성 및 스케줄링 총괄 |
| **스토리지 & 데이터 레이크** | `MinIO (NVMe Local Storage)` | AWS S3 호환 대용량 피처 데이터 및 학습 모델 아티팩트 영속 저장 |
| **머신러닝 GPU 학습** | `PyTorch / XGBoost`, `NVIDIA CUDA` | 온디맨드 로컬 GPU(RTX 3060 Ti) 점유 학습 및 자원 자동 반환 |
| **모델 서빙 & UI** | `FastAPI`, `React` | 0.05초 초고속 실시간 모델 추론 API 및 사용자 웹 인터페이스 제공 |
