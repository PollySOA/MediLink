#!/usr/bin/env bash
set -euo pipefail

# One-shot deployment for frontend on Azure App Service (Linux, Node runtime).
# Safe by design: no secrets are stored here; it uses your active Azure CLI session.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${FRONTEND_DIR:-$ROOT_DIR/frontend}"
RESOURCE_GROUP="${RESOURCE_GROUP:?ERROR: RESOURCE_GROUP environment variable not set. Please export RESOURCE_GROUP=your-rg}"
WEBAPP_NAME="${WEBAPP_NAME:?ERROR: WEBAPP_NAME environment variable not set. Please export WEBAPP_NAME=your-webapp}"
BACKEND_API_URL="${BACKEND_API_URL:?ERROR: BACKEND_API_URL environment variable not set. Please export BACKEND_API_URL=https://your-backend.azurewebsites.net}"
SMOKE_CHECKS="${SMOKE_CHECKS:-5}"
STARTUP_CMD="pm2 serve /home/site/wwwroot --no-daemon --spa"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd az
require_cmd npm
require_cmd zip
require_cmd curl

if [[ ! -d "$FRONTEND_DIR" || ! -f "$FRONTEND_DIR/package.json" ]]; then
  echo "[ERROR] FRONTEND_DIR is invalid: $FRONTEND_DIR" >&2
  exit 1
fi

echo "[INFO] Validating Azure CLI session..."
az account show >/dev/null

echo "[INFO] Building frontend in $FRONTEND_DIR"
pushd "$FRONTEND_DIR" >/dev/null
echo "[INFO] Using VITE_API_URL=$BACKEND_API_URL"
VITE_API_URL="$BACKEND_API_URL" npm run build

if [[ ! -d dist ]]; then
  echo "[ERROR] Build did not generate dist/" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
ZIP_PATH="$TMP_DIR/frontend-dist.zip"

( cd dist && zip -qr "$ZIP_PATH" . )
popd >/dev/null

echo "[INFO] Deploying artifact to Azure Web App: $WEBAPP_NAME"
az webapp deploy \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --src-path "$ZIP_PATH" \
  --type zip \
  --restart true >/dev/null

echo "[INFO] Enforcing startup command for static SPA"
az webapp config set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --startup-file "$STARTUP_CMD" >/dev/null

echo "[INFO] Restarting app"
az webapp restart --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" >/dev/null

HOSTNAME="$(az webapp show --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" --query defaultHostName -o tsv)"
APP_URL="https://$HOSTNAME/"

echo "[INFO] Verifying startup command"
CURRENT_CMD="$(az webapp config show --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" --query appCommandLine -o tsv)"
if [[ "$CURRENT_CMD" != "$STARTUP_CMD" ]]; then
  echo "[ERROR] Startup command mismatch. Current: $CURRENT_CMD" >&2
  exit 1
fi

echo "[INFO] Running smoke checks against $APP_URL"
PASS_COUNT=0
for i in $(seq 1 "$SMOKE_CHECKS"); do
  BODY_FILE="$TMP_DIR/body_$i.html"
  HTTP_CODE="$(curl -sS --max-time 20 -o "$BODY_FILE" -w "%{http_code}" "$APP_URL")"

  if [[ "$HTTP_CODE" == "200" ]] && grep -Eq "MediLink|Interoperabilidad y Humanización Médica" "$BODY_FILE"; then
    echo "[OK] check $i: HTTP 200 + expected content"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "[WARN] check $i: HTTP $HTTP_CODE, content did not match expected login page"
    if grep -q "Application Error" "$BODY_FILE"; then
      echo "[WARN] check $i: detected 'Application Error'"
    fi
  fi

done

if [[ "$PASS_COUNT" -lt "$SMOKE_CHECKS" ]]; then
  echo "[ERROR] Smoke checks failed ($PASS_COUNT/$SMOKE_CHECKS passed)." >&2
  exit 1
fi

echo "[SUCCESS] Frontend deployed and validated successfully."
echo "[SUCCESS] URL: $APP_URL"
