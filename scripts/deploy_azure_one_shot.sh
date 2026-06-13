#!/usr/bin/env bash
set -euo pipefail

# End-to-end Azure deployment for MediLink.
# It deploys the backend first, then builds and deploys the frontend against the deployed backend URL.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_SCRIPT="$ROOT_DIR/scripts/deploy_backend_one_shot.sh"
FRONTEND_SCRIPT="$ROOT_DIR/scripts/deploy_frontend_one_shot.sh"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-medilink-policy-frc}"
BACKEND_WEBAPP_NAME="${BACKEND_WEBAPP_NAME:-app-medilink-api-fr-06111153}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd az

if [[ ! -x "$BACKEND_SCRIPT" || ! -x "$FRONTEND_SCRIPT" ]]; then
  echo "[ERROR] Deployment scripts must be executable:" >&2
  echo "  $BACKEND_SCRIPT" >&2
  echo "  $FRONTEND_SCRIPT" >&2
  exit 1
fi

BACKEND_API_URL="https://$(az webapp show --resource-group "$RESOURCE_GROUP" --name "$BACKEND_WEBAPP_NAME" --query defaultHostName -o tsv)"

if [[ -z "$BACKEND_API_URL" || "$BACKEND_API_URL" == "https://" ]]; then
  echo "[ERROR] Could not determine backend API URL" >&2
  exit 1
fi

echo "[INFO] Deploying backend..."
"$BACKEND_SCRIPT"

echo "[INFO] Deploying frontend against $BACKEND_API_URL"
BACKEND_API_URL="$BACKEND_API_URL" "$FRONTEND_SCRIPT"

echo "[SUCCESS] Full-stack Azure deployment completed."
echo "[SUCCESS] Backend: $BACKEND_API_URL"
