#!/usr/bin/env bash
# Tears the Vansh App stack down in reverse order.
set -uo pipefail
cd "$(dirname "$0")"
echo "==> Deleting Ingress (vanshapp-ingress)..."
kubectl delete -f ingress.yaml --ignore-not-found
echo "==> Deleting frontend (vanshapp-frontend)..."
kubectl delete -f frontend.yaml --ignore-not-found
echo "==> Deleting backend (vanshapp-backend)..."
kubectl delete -f backend.yaml --ignore-not-found
echo "==> Deleting Secret (vanshapp-db-secret)..."
kubectl delete -f secret.yaml --ignore-not-found
echo "==> Deleting ConfigMap (vanshapp-config)..."
kubectl delete -f configmap.yaml --ignore-not-found
echo "==> Cleanup complete."
