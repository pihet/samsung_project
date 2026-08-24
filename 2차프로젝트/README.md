# 🏗️ 100% On-Premise End-to-End MLOps & Data Platform

> **클라우드(AWS/GCP) 비용 $0**, 폐쇄망 환경을 위한 **Kubernetes(K8s) + Kafka + Spark + Airflow + GPU 가속 + MinIO + FastAPI** 엔드투엔드 데이터 엔지니어링 & MLOps 아키텍처입니다.

---

## 🌐 시스템 전체 파이프라인 아키텍처 (Kubernetes Cluster)

```mermaid
flowchart TD
    User["👤 사용자 / 클라이언트"] -->|내부망 접속| MetalLB["🌐 MetalLB (L4 LoadBalancer)"]

    subgraph K8s ["☸️ On-Premise Kubernetes Cluster (K8s)"]

        Airflow["👑 Apache Airflow (전체 파이프라인 총괄 오케스트레이터)"]

        %% 1단: 데이터 파이프라인 계층
        subgraph L1 ["1️⃣ Data Pipeline Layer (데이터 수집 및 분산 전처리)"]
            direction LR
            SourceDB[(원천 DB / 로그)] --> IngestionPod["수집 파드\n(CDC / 배치 수집)"]
            IngestionPod --> Kafka["Kafka 클러스터\n(실시간 메시지 버퍼링)"]
            Kafka --> Spark["Spark on K8s\n(분산 정제 & 피처 가공)"]
        end

        %% 2단: 중앙 공유 스토리지 계층
        subgraph L2 ["2️⃣ Storage Layer (로컬 데이터 레이크 & 모델 저장소)"]
            direction LR
            MinIO_Data[("MinIO 피처셋\n(데이터 레이크)")]
            MinIO_Model[("MinIO 모델 저장소\n(버전별 아티팩트)")]
        end

        %% 3단: MLOps 및 서빙 계층
        subgraph L3 ["3️⃣ MLOps & Serving Layer (GPU 모델 학습 및 실시간 서빙)"]
            direction LR
            TrainPod["모델 학습 파드"]
            FastAPI["FastAPI 추론 서버\n(REST API)"]
            React["React 웹 대시보드\n(결과 시각화)"]
            FastAPI <--> React
        end

        %% 데이터 파이프라인 ➔ 스토리지 ➔ 학습/서빙 흐름
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
