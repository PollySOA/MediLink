#!/usr/bin/env bash
set -euo pipefail

# One-shot deployment for backend on Azure App Service (Linux, Python runtime).
# Safe by design: it does not store secrets and only verifies that the app settings already exist.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${BACKEND_DIR:-$ROOT_DIR/backend}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-medilink-policy-frc}"
WEBAPP_NAME="${WEBAPP_NAME:-app-medilink-api-fr-06111153}"
STARTUP_CMD="python -m uvicorn main:app --host 0.0.0.0 --port 8000"
SMOKE_USER="${SMOKE_USER:-dr.garcia}"
SMOKE_PASSWORD="${SMOKE_PASSWORD:-demo1234}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd az
require_cmd zip
require_cmd curl
require_cmd python

if [[ ! -d "$BACKEND_DIR" || ! -f "$BACKEND_DIR/main.py" || ! -f "$BACKEND_DIR/requirements.txt" ]]; then
  echo "[ERROR] BACKEND_DIR is invalid: $BACKEND_DIR" >&2
  exit 1
fi

echo "[INFO] Validating Azure CLI session..."
az account show >/dev/null

echo "[INFO] Verifying backend app settings are present"
SETTINGS_JSON="$(az webapp config appsettings list \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --query "[].{name:name,value:value}" -o json)"

set +e
MISSING_SETTINGS="$(python -c '
import json
import sys

required = [
    "APP_ENV",
    "JWT_SECRET",
    "IDONIA_PUBLIC_ID",
    "IDONIA_API_SECRET",
    "IDONIA_API_KEY",
    "IDONIA_BASE_URL",
    "IDONIA_UPLOAD_TEMPLATE",
    "IDONIA_STUDIES_TEMPLATE",
    "IDONIA_MAGIC_LINK_PATH",
    "IDONIA_MAGIC_LINK_QUERY_PARAM",
    "IDONIA_MAGIC_LINK_PUBLIC_BASE_URL",
    "IDONIA_MAGIC_LINK_REFERENCE_MODE",
    "IDONIA_NUM_PARTICIPANTE",
    "IDONIA_PATIENT_PASSWORD",
    "RECOG_API_URL",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
]

try:
  payload = json.loads(sys.argv[1])
except json.JSONDecodeError:
    print("[ERROR] Could not parse Azure app settings JSON", file=sys.stderr)
    sys.exit(2)

settings = {item.get("name"): str(item.get("value") or "").strip() for item in payload}
missing = [name for name in required if not settings.get(name)]
if missing:
    print("\n".join(missing))
    sys.exit(1)
' "$SETTINGS_JSON")"
PY_STATUS=$?
set -e

if [[ $PY_STATUS -eq 2 ]]; then
  echo "[ERROR] Could not validate Azure app settings JSON" >&2
  exit 1
fi

if [[ -n "$MISSING_SETTINGS" ]]; then
  echo "[ERROR] Backend app settings missing or empty:" >&2
  printf '%s\n' "$MISSING_SETTINGS" >&2
  exit 1
fi

echo "[INFO] Building backend artifact"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
ZIP_PATH="$TMP_DIR/backend.zip"

pushd "$BACKEND_DIR" >/dev/null
zip -qr "$ZIP_PATH" . \
  -x ".venv/*" \
  -x "__pycache__/*" \
  -x "*/__pycache__/*" \
  -x "*.pyc" \
  -x "*.pyo"
popd >/dev/null

echo "[INFO] Deploying backend artifact to Azure Web App: $WEBAPP_NAME"
az webapp deploy \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --src-path "$ZIP_PATH" \
  --type zip \
  --restart true >/dev/null

echo "[INFO] Enforcing backend startup command"
az webapp config set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --startup-file "$STARTUP_CMD" >/dev/null

echo "[INFO] Enabling build during deployment for Python dependencies"
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true ENABLE_ORYX_BUILD=true >/dev/null

echo "[INFO] Restarting backend app"
az webapp restart --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" >/dev/null

HOSTNAME="$(az webapp show --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" --query defaultHostName -o tsv)"
APP_URL="https://$HOSTNAME/"

echo "[INFO] Verifying backend startup command"
CURRENT_CMD="$(az webapp config show --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" --query appCommandLine -o tsv)"
if [[ "$CURRENT_CMD" != "$STARTUP_CMD" ]]; then
  echo "[ERROR] Startup command mismatch. Current: $CURRENT_CMD" >&2
  exit 1
fi

echo "[INFO] Smoke checking backend docs and auth"
DOCS_CODE="$(curl -sS --max-time 20 -o "$TMP_DIR/docs.html" -w "%{http_code}" "$APP_URL/docs")"
if [[ "$DOCS_CODE" != "200" ]]; then
  echo "[ERROR] Backend /docs returned HTTP $DOCS_CODE" >&2
  exit 1
fi

LOGIN_JSON="$(curl -sS --max-time 20 \
  -X POST "$APP_URL/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$SMOKE_USER\",\"password\":\"$SMOKE_PASSWORD\"}")"

SMOKE_TOKEN="$(python -c 'import json, sys; print(json.loads(sys.argv[1]).get("access_token", ""))' "$LOGIN_JSON")"

if [[ -z "$SMOKE_TOKEN" ]]; then
  echo "[ERROR] Backend login smoke test did not return an access token" >&2
  exit 1
fi

SEARCH_CODE="$(curl -sS --max-time 20 -o "$TMP_DIR/search.json" -w "%{http_code}" \
  "$APP_URL/api/patients/search?name=Carolina&page=1&page_size=5" \
  -H "Authorization: Bearer $SMOKE_TOKEN")"
if [[ "$SEARCH_CODE" != "200" ]]; then
  echo "[ERROR] Backend patient search returned HTTP $SEARCH_CODE" >&2
  exit 1
fi

echo "[SUCCESS] Backend deployed and validated successfully."
echo "$APP_URL"
