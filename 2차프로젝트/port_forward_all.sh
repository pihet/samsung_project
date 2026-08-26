#!/bin/bash
# port_forward_all.sh
# One-click Port Forwarding for Samsung Project 2 (Port 5433 for Postgres to avoid 1st project 5432 collision)

echo "================================================================================"
echo " Starting One-Click Kubernetes Port-Forwarding Suite for Project 2..."
echo "================================================================================"

# 1. Kill any existing port-forward processes to prevent address collision
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 1

# 2. Start Port-Forwarding in Background
echo "[1/7] Kafka Bootstrap     -> localhost:9092"
kubectl port-forward -n kafka svc/my-cluster-kafka-bootstrap 9092:9092 > /dev/null 2>&1 &

echo "[2/7] PostgreSQL (Proj 2) -> localhost:5433 (Port 5433 isolated, User/Pass: postgres/postgres)"
kubectl port-forward -n airflow svc/airflow-postgresql 5433:5432 > /dev/null 2>&1 &

echo "[3/7] React Frontend      -> http://localhost:3000"
kubectl port-forward -n default svc/react-frontend-service 3000:3000 > /dev/null 2>&1 &

echo "[4/7] FastAPI Serving     -> http://localhost:8000 (Swagger: http://localhost:8000/docs)"
kubectl port-forward -n default svc/fastapi-service 8000:8000 > /dev/null 2>&1 &

echo "[5/7] Airflow Web/API     -> http://localhost:8080 (User/Pass: admin / admin)"
kubectl port-forward -n airflow svc/airflow-api-server 8080:8080 > /dev/null 2>&1 &

echo "[6/7] Kafka UI            -> http://localhost:8088 (Mapped from 8080 to avoid collision)"
kubectl port-forward -n kafka svc/kafka-ui 8088:8080 > /dev/null 2>&1 &

echo "[7/7] MinIO Console & API -> http://localhost:9001 (API: 9000, User/Pass: minioadmin / minioadmin123)"
kubectl port-forward -n minio svc/minio-service 9000:9000 9001:9001 > /dev/null 2>&1 &

sleep 2
echo "================================================================================"
echo " All 7 Port-Forwards are active in the background!"
echo "--------------------------------------------------------------------------------"
echo " - Kafka Broker   : localhost:9092"
echo " - PostgreSQL DB  : localhost:5433 (User: postgres, Pass: postgres, DB: shipyard_db / postgres)"
echo " - React Frontend : http://localhost:3000"
echo " - FastAPI Docs   : http://localhost:8000/docs"
echo " - Airflow Web    : http://localhost:8080 (admin / admin)"
echo " - Kafka UI       : http://localhost:8088"
echo " - MinIO Console  : http://localhost:9001 (minioadmin / minioadmin123)"
echo "--------------------------------------------------------------------------------"
echo " * To stop all port-forwards, run: pkill -f 'kubectl port-forward'"
echo "================================================================================"
