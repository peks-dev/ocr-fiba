#!/usr/bin/env bash
# Build and deploy the OCR API + MCP server to Google Cloud Run (idempotent; safe to re-run).
#
# Usage: scripts/deploy_cloudrun.sh [all|infra|build|api|mcp|urls]   (default: all)
#
# Env overrides:
#   GCP_PROJECT (ocr-fiba-8d0920)  GCP_REGION (us-central1)  RUNS_BUCKET (<project>-runs)
#   OCR_RATE_LIMIT_PER_MINUTE (3)  OCR_RATE_LIMIT_PER_DAY (50)  RUNS_RETENTION_DAYS (30)
#   OCR_DEFAULT_EXTRACTOR_PROVIDER (openrouter)  OCR_DEFAULT_EXTRACTOR_MODEL (google/gemini-3-flash-preview)
#   OPENROUTER_API_KEY   only read when the openrouter-api-key secret does not exist yet,
#                        or when ROTATE_OPENROUTER_KEY=1.
#   ROTATE_CLIENT_TOKEN=1  generate a new public client token (old one stops working).
#   OCR_CORS_ORIGINS        comma-separated browser origins (e.g. the Vercel URL).
#                           Empty by default; set after the first web deploy.
#
# Secrets (Secret Manager): openrouter-api-key, ocr-client-token, and optionally
# supabase-service-key + supabase-jwt-secret (injected only if both already exist;
# this script never creates those two). The client token value is also kept
# locally in .cloud-token (chmod 600, gitignored). Secret values are never printed.
#
# Supabase (ocr-api): SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are plain env.
# Override with SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY if needed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
GCLOUD="${GCLOUD:-$(command -v gcloud || echo "$HOME/google-cloud-sdk/bin/gcloud")}"

PROJECT="${GCP_PROJECT:-ocr-fiba-8d0920}"
REGION="${GCP_REGION:-us-central1}"
BUCKET="${RUNS_BUCKET:-$PROJECT-runs}"
REPO="ocr-fiba"
IMAGE="$REGION-docker.pkg.dev/$PROJECT/$REPO/ocr-fiba"
TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M%S)}"
API_SA="ocr-api@$PROJECT.iam.gserviceaccount.com"
MCP_SA="ocr-mcp@$PROJECT.iam.gserviceaccount.com"
TOKEN_FILE="$ROOT/.cloud-token"
RETENTION_DAYS="${RUNS_RETENTION_DAYS:-30}"
PER_MIN="${OCR_RATE_LIMIT_PER_MINUTE:-3}"
PER_DAY="${OCR_RATE_LIMIT_PER_DAY:-50}"
EXTRACTOR_PROVIDER="${OCR_DEFAULT_EXTRACTOR_PROVIDER:-openrouter}"
EXTRACTOR_MODEL="${OCR_DEFAULT_EXTRACTOR_MODEL:-google/gemini-3-flash-preview}"
SUPABASE_URL_VALUE="${SUPABASE_URL:-https://cgcejoqsmouieijkkogw.supabase.co}"
SUPABASE_PUBLISHABLE_KEY_VALUE="${SUPABASE_PUBLISHABLE_KEY:-sb_publishable_Q-y9BVYWe-wyVj5eLl91lA_zwxAvGKp}"

g() { "$GCLOUD" --project "$PROJECT" --quiet "$@"; }

secret_exists() {
  g secrets describe "$1" >/dev/null 2>&1
}

grant_secret_access() {  # grant_secret_access SECRET SA
  g secrets add-iam-policy-binding "$1" --member "serviceAccount:$2" \
    --role roles/secretmanager.secretAccessor >/dev/null
}

supabase_secret_bindings() {
  if secret_exists supabase-service-key && secret_exists supabase-jwt-secret; then
    printf 'SUPABASE_SERVICE_KEY=supabase-service-key:latest,SUPABASE_JWT_SECRET=supabase-jwt-secret:latest'
  fi
}

ensure_secret() {  # ensure_secret NAME VALUE_FILE (value read from file, never echoed)
  local name="$1" file="$2"
  if ! g secrets describe "$name" >/dev/null 2>&1; then
    g secrets create "$name" --replication-policy=automatic --data-file="$file" >/dev/null
    echo "created secret $name"
  else
    g secrets versions add "$name" --data-file="$file" >/dev/null
    echo "added new version to secret $name"
  fi
}

infra() {
  g services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
    secretmanager.googleapis.com storage.googleapis.com iam.googleapis.com

  g artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 ||
    g artifacts repositories create "$REPO" --location "$REGION" --repository-format docker

  if ! g storage buckets describe "gs://$BUCKET" >/dev/null 2>&1; then
    g storage buckets create "gs://$BUCKET" --location "$REGION" --uniform-bucket-level-access \
      --public-access-prevention
  fi
  local lifecycle; lifecycle="$(mktemp)"
  printf '{"rule":[{"action":{"type":"Delete"},"condition":{"age":%s}}]}\n' "$RETENTION_DAYS" >"$lifecycle"
  g storage buckets update "gs://$BUCKET" --lifecycle-file="$lifecycle" >/dev/null
  rm -f "$lifecycle"

  for sa in ocr-api ocr-mcp; do
    g iam service-accounts describe "$sa@$PROJECT.iam.gserviceaccount.com" >/dev/null 2>&1 ||
      g iam service-accounts create "$sa" --display-name "$sa (Cloud Run)"
  done

  # Public client token: one bearer token for both the REST API and the MCP endpoint.
  if [[ ! -s "$TOKEN_FILE" || "${ROTATE_CLIENT_TOKEN:-0}" == "1" ]]; then
    (umask 077; python3 -c 'import secrets; print("ocr_pub_" + secrets.token_urlsafe(36), end="")' >"$TOKEN_FILE")
    ensure_secret ocr-client-token "$TOKEN_FILE"
  elif ! g secrets describe ocr-client-token >/dev/null 2>&1; then
    ensure_secret ocr-client-token "$TOKEN_FILE"
  fi
  chmod 600 "$TOKEN_FILE"

  if ! g secrets describe openrouter-api-key >/dev/null 2>&1 || [[ "${ROTATE_OPENROUTER_KEY:-0}" == "1" ]]; then
    : "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY must be set to create the openrouter-api-key secret}"
    local tmp; tmp="$(mktemp)"; chmod 600 "$tmp"
    printf '%s' "$OPENROUTER_API_KEY" >"$tmp"
    ensure_secret openrouter-api-key "$tmp"
    rm -f "$tmp"
  fi

  g secrets add-iam-policy-binding openrouter-api-key --member "serviceAccount:$API_SA" \
    --role roles/secretmanager.secretAccessor >/dev/null
  for sa in "$API_SA" "$MCP_SA"; do
    g secrets add-iam-policy-binding ocr-client-token --member "serviceAccount:$sa" \
      --role roles/secretmanager.secretAccessor >/dev/null
  done
  "$GCLOUD" --quiet storage buckets add-iam-policy-binding "gs://$BUCKET" \
    --member "serviceAccount:$API_SA" --role roles/storage.objectUser >/dev/null
  echo "infra ok: bucket gs://$BUCKET (delete after ${RETENTION_DAYS}d), secrets, service accounts"
}

build() {
  g builds submit --tag "$IMAGE:$TAG" .
  echo "$IMAGE:$TAG" >"$ROOT/.cloud-image"
}

current_image() {
  if [[ -s "$ROOT/.cloud-image" ]]; then cat "$ROOT/.cloud-image"; else echo "$IMAGE:latest"; fi
}

deploy_api() {
  local api_secrets="OCR_ENGINE_API_KEY=ocr-client-token:latest,OPENROUTER_API_KEY=openrouter-api-key:latest"
  local supabase_secrets
  supabase_secrets="$(supabase_secret_bindings)"
  if [[ -n "$supabase_secrets" ]]; then
    api_secrets="$api_secrets,$supabase_secrets"
    grant_secret_access supabase-service-key "$API_SA"
    grant_secret_access supabase-jwt-secret "$API_SA"
  else
    echo "skipping Supabase secrets: create supabase-service-key and supabase-jwt-secret first"
  fi
  # Bucket is mounted at /mnt/data: runs/ holds run folders, quota/ the persisted rate-limit state.
  # API: max 3 instances so cold-start traffic is not serialized behind a single instance.
  # Rate-limit counters are in-memory per process with a best-effort JSON file designed for a
  # single writer, so quotas can be slightly loose across instances. CPU stays allocated
  # (--no-cpu-throttling) because OCR runs execute in a background thread after the HTTP
  # response returns.
  g run deploy ocr-api --image "$(current_image)" --region "$REGION" \
    --service-account "$API_SA" --allow-unauthenticated \
    --execution-environment gen2 --no-cpu-throttling \
    --cpu 1 --memory 1Gi --concurrency 20 --min-instances 0 --max-instances 3 --timeout 600 \
    --add-volume "name=runs,type=cloud-storage,bucket=$BUCKET" \
    --add-volume-mount "volume=runs,mount-path=/mnt/data" \
    --set-env-vars "^|^OCR_SERVICE=api|OCR_ENV=production|OCR_RUNS_DIR=/mnt/data/runs|OCR_RATE_LIMIT_STATE_FILE=/mnt/data/quota/rate_limit.json|OCR_MAX_UPLOAD_MB=20|OCR_ALLOW_PATH_INPUT=false|OCR_RATE_LIMIT_PER_MINUTE=$PER_MIN|OCR_RATE_LIMIT_PER_DAY=$PER_DAY|OCR_DEFAULT_EXTRACTOR_PROVIDER=$EXTRACTOR_PROVIDER|OCR_DEFAULT_EXTRACTOR_MODEL=$EXTRACTOR_MODEL|OCR_CORS_ORIGINS=${OCR_CORS_ORIGINS:-}|SUPABASE_URL=$SUPABASE_URL_VALUE|SUPABASE_PUBLISHABLE_KEY=$SUPABASE_PUBLISHABLE_KEY_VALUE" \
    --set-secrets "$api_secrets"
}

deploy_mcp() {
  local api_url; api_url="$(service_url ocr-api)"
  g run deploy ocr-mcp --image "$(current_image)" --region "$REGION" \
    --service-account "$MCP_SA" --allow-unauthenticated \
    --cpu 1 --memory 512Mi --concurrency 20 --min-instances 0 --max-instances 2 --timeout 600 \
    --set-env-vars "OCR_SERVICE=mcp,OCR_ENV=production,MCP_TRANSPORT=http,MCP_HOST=0.0.0.0,MCP_ALLOW_PATH_INPUT=false,FASTMCP_STATELESS_HTTP=true,OCR_API_BASE_URL=$api_url,OCR_API_TIMEOUT_SECONDS=300" \
    --set-secrets "MCP_AUTH_TOKEN=ocr-client-token:latest,OCR_API_KEY=ocr-client-token:latest"
}

service_url() {  # deterministic https://<service>-<project-number>.<region>.run.app
  local number; number="$(g projects describe "$PROJECT" --format 'value(projectNumber)')"
  echo "https://$1-$number.$REGION.run.app"
}

urls() {
  echo "api: $(service_url ocr-api)"
  echo "mcp: $(service_url ocr-mcp)/mcp"
}

case "${1:-all}" in
  all) infra; build; deploy_api; deploy_mcp; urls ;;
  infra) infra ;;
  build) build ;;
  api) deploy_api ;;
  mcp) deploy_mcp ;;
  urls) urls ;;
  *) echo "usage: $0 [all|infra|build|api|mcp|urls]" >&2; exit 2 ;;
esac
