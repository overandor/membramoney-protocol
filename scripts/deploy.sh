#!/bin/bash
# Membra Money Protocol — Deployment Script
# Usage: ./scripts/deploy.sh [devnet|staging|production]

set -euo pipefail

ENV="${1:-devnet}"

echo "Deploying Membra Money Protocol to ${ENV}..."

# Pre-flight checks
echo "[1/5] Running pre-flight checks..."
bash scripts/pre_flight_check.sh

# Build Docker images
echo "[2/5] Building Docker images..."
docker build -t membramoney/backend:latest ./backend
docker build -t membramoney/ui:latest ./ui

# Push to registry (example: ECR)
echo "[3/5] Pushing to container registry..."
# aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL
# docker push membramoney/backend:latest
# docker push membramoney/ui:latest

# Apply K8s manifests
echo "[4/5] Applying Kubernetes manifests..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/ui-deployment.yaml
kubectl apply -f k8s/ui-service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml

# Wait for rollout
echo "[5/5] Waiting for rollout..."
kubectl rollout status deployment/membramoney-backend -n membramoney
kubectl rollout status deployment/membramoney-ui -n membramoney

echo "Deployment to ${ENV} complete!"
