#!/bin/bash
# port_forward_all.sh
# One-click Port Forwarding for Kafka, Airflow, React, FastAPI, Kafka-UI, and MinIO

echo "================================================================================"
echo " Starting One-Click Kubernetes Port-Forwarding Suite..."
echo "================================================================================"

# 1. Kill any existing port-forward processes to prevent address collision
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 1

# 2. Start Port-Forwarding in Background
echo "[1/6] Kafka Bootstrap     -> localhost:9092"
kubectl port-forward -n kafka svc/my-cluster-kafka-bootstrap 9092:9092 > /dev/null 2>&1 &

echo "[2/6] React Frontend      -> http://localhost:3000"
kubectl port-forward -n default svc/react-frontend-service 3000:3000 > /dev/null 2>&1 &

echo "[3/6] FastAPI Serving     -> http://localhost:8000 (Swagger: http://localhost:8000/docs)"
kubectl port-forward -n default svc/fastapi-service 8000:8000 > /dev/null 2>&1 &

echo "[4/6] Airflow Web/API     -> http://localhost:8080"
kubectl port-forward -n airflow svc/airflow-api-server 8080:8080 > /dev/null 2>&1 &

echo "[5/6] Kafka UI            -> http://localhost:8088 (Mapped from 8080 to avoid collision)"
kubectl port-forward -n kafka svc/kafka-ui 8088:8080 > /dev/null 2>&1 &

echo "[6/6] MinIO Console & API -> http://localhost:9001 (API: 9000)"
kubectl port-forward -n minio svc/minio-service 9000:9000 9001:9001 > /dev/null 2>&1 &

sleep 2
echo "================================================================================"
echo " All Port-Forwards are active in the background!"
echo "--------------------------------------------------------------------------------"
echo " - Kafka Broker   : localhost:9092"
echo " - React Frontend : http://localhost:3000"
echo " - FastAPI Docs   : http://localhost:8000/docs"
echo " - Airflow Web    : http://localhost:8080"
echo " - Kafka UI       : http://localhost:8088"
echo " - MinIO Console  : http://localhost:9001 (User/Pass: minioadmin / minioadmin123)"
echo "--------------------------------------------------------------------------------"
echo " * To stop all port-forwards, run: pkill -f 'kubectl port-forward'"
echo "================================================================================"
