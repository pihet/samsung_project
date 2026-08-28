#!/bin/bash
# port_forward_all.sh
# [조선소 스마트 정반 스케줄링 9대 통합 포트포워딩 원클릭 실행 스크립트]

echo "================================================================================"
echo " Starting One-Click Kubernetes Port-Forwarding Suite for Project 2 (MLOps)..."
echo "================================================================================"

# 기존 포트포워딩 프로세스 정리
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 1

# 1. Kafka Bootstrap 포트포워딩 (9092)
kubectl port-forward -n kafka svc/my-cluster-kafka-bootstrap 9092:9092 >/dev/null 2>&1 &
echo "[1/9] Kafka Bootstrap     -> localhost:9092"

# 2. PostgreSQL 운영 DB 포트포워딩 (5433 -> 5432)
kubectl port-forward -n default svc/postgres-service 5433:5432 >/dev/null 2>&1 &
echo "[2/9] PostgreSQL (Proj 2) -> localhost:5433 (Port 5433 isolated, User/Pass: postgres/postgres)"

# 3. React 프론트엔드 대시보드 포트포워딩 (3000)
kubectl port-forward -n default svc/react-frontend-service 3000:3000 >/dev/null 2>&1 &
echo "[3/9] React Frontend      -> http://localhost:3000"

# 4. FastAPI 서빙 백엔드 포트포워딩 (8000)
kubectl port-forward -n default svc/fastapi-service 8000:8000 >/dev/null 2>&1 &
echo "[4/9] FastAPI Serving     -> http://localhost:8000 (Swagger: http://localhost:8000/docs)"

# 5. Apache Airflow 웹서버 포트포워딩 (8080)
kubectl port-forward -n airflow svc/airflow-api-server 8080:8080 >/dev/null 2>&1 &
echo "[5/9] Airflow Web/API     -> http://localhost:8080 (User/Pass: admin / admin)"

# 6. Kafka-UI 포트포워딩 (8088 -> 8080)
kubectl port-forward -n kafka svc/kafka-ui-service 8088:8080 >/dev/null 2>&1 &
echo "[6/9] Kafka UI            -> http://localhost:8088 (Mapped from 8080 to avoid collision)"

# 7. MinIO 콘솔 및 S3 API 포트포워딩 (9001 -> 9001, 9000 -> 9000)
kubectl port-forward -n minio svc/minio-service 9001:9001 9000:9000 >/dev/null 2>&1 &
echo "[7/9] MinIO Console & API -> http://localhost:9001 (API: 9000, User/Pass: minioadmin / minioadmin123)"

# 8. Apache Flink 대시보드 포트포워딩 (8082 -> 8081)
kubectl port-forward -n flink svc/flink-jobmanager 8082:8081 >/dev/null 2>&1 &
echo "[8/9] Flink Dashboard     -> http://localhost:8082 (Mapped from 8081)"

# 9. MLflow Tracking & Model Registry 포트포워딩 (5000)
kubectl port-forward -n default svc/mlflow-service 5000:5000 >/dev/null 2>&1 &
echo "[9/9] MLflow Tracking UI  -> http://localhost:5000"

echo "================================================================================"
echo " All 9 Port-Forwards are active in the background!"
echo "--------------------------------------------------------------------------------"
echo " - React Frontend : http://localhost:3000"
echo " - FastAPI Docs   : http://localhost:8000/docs"
echo " - MLflow UI      : http://localhost:5000"
echo " - Flink UI       : http://localhost:8082"
echo " - Airflow Web    : http://localhost:8080 (admin / admin)"
echo " - Kafka UI       : http://localhost:8088"
echo " - MinIO Console  : http://localhost:9001 (minioadmin / minioadmin123)"
echo " - PostgreSQL DB  : localhost:5433 (User: postgres, Pass: postgres, DB: shipyard_db)"
echo " - Kafka Broker   : localhost:9092"
echo "--------------------------------------------------------------------------------"
echo " * To stop all port-forwards, run: pkill -f 'kubectl port-forward'"
echo "================================================================================"
