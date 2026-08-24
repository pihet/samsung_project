```mermaid
flowchart TD
    subgraph DataIngestion ["1. 데이터 수집 & 스트리밍"]
        DB[("로컬 DB")] -->|"CDC / Log Ingestion"| Connect["Kafka Connect"]
        Connect -->|"JSON Stream"| Kafka["Kafka HA Cluster"]
    end

    subgraph ETL ["2. 대용량 분산 전처리"]
        Kafka -->|"병렬 처리"| Spark["Spark on K8s"]
        Spark -->|"정제된 Parquet 저장"| MinIO[("MinIO S3 스토리지 (로컬 NVMe SSD)")]
    end

    subgraph MLOpsTrain ["3. 모델 학습 (GPU 가속)"]
        Airflow["Airflow Orchestrator"] -->|"스케줄링 트리거"| TrainPod["학습 파드 (KubernetesPodOperator) - RTX 3060 Ti 8GB"]
        MinIO -->|"피처 데이터 로드"| TrainPod
        TrainPod -->|"학습 완료 모델 (.pkl / .pt) 업로드"| MinIO
    end

    subgraph Serving ["4. 실시간 모델 추론 & 웹"]
        MinIO -->|"최신 모델 로드"| FastAPI["FastAPI 추론 서버"]
        FastAPI <-->|"REST API"| React["React 프론트엔드"]
        MetalLB["MetalLB LoadBalancer"] -->|"내부 IP 라우팅"| React
    end

    style DataIngestion fill:#e6f7ff,stroke:#1890ff,stroke-width:2px
    style ETL fill:#fff7e6,stroke:#fa8c16,stroke-width:2px
    style MLOpsTrain fill:#f9f0ff,stroke:#722ed1,stroke-width:2px
    style Serving fill:#f6ffed,stroke:#52c41a,stroke-width:2px
