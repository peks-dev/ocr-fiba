[← Back to README](../README.md) | [← Codebase Guide](CODEBASE-GUIDE.md)

# Deployment and Operations

**Production runs `ocr-api` and `ocr-mcp` from one container image on Google Cloud Run, hosts `packages/web` on Vercel, and backs identity/quotas with Supabase.**

---

## 1. Local production-like supervisor (`scripts/serve.sh`)

Run both `ocr-api` (`127.0.0.1:8000`) and `ocr-mcp` (`127.0.0.1:8001/mcp`) locally in `OCR_ENV=production` with restart supervision:

```bash
scripts/serve.sh start     # generates .server-token (chmod 600, gitignored) on first run
scripts/serve.sh status
scripts/serve.sh stop
```

- Set `OCR_SERVE_TUNNEL=1` to also expose Cloudflare quick tunnels (`scripts/serve.sh urls`).
- Logs and PIDs are stored in `.server/` (gitignored); provider API keys come from the shell environment or `.env`.

---

## 2. Google Cloud Run (`Dockerfile` + `scripts/deploy_cloudrun.sh`)

One multi-stage image (`Dockerfile`, Python `3.12` + `uv sync --frozen --no-dev`) serves both services based on `OCR_SERVICE`:
- `OCR_SERVICE=api` → runs `ocr-api` on `PORT` (default `8080` in container).
- `OCR_SERVICE=mcp` → runs `ocr-mcp` with `MCP_TRANSPORT=http`, `MCP_HOST=0.0.0.0`.

### Provisioning & manual deploy (`scripts/deploy_cloudrun.sh`)

```bash
OPENROUTER_API_KEY=... scripts/deploy_cloudrun.sh all
# Subcommands: all | infra | build | api | mcp | urls
```

What `deploy_cloudrun.sh` provisions and configures (idempotent):

1. **Infra (`infra`):** Enables Cloud Run, Cloud Build, Artifact Registry (`ocr-fiba`), Secret Manager, GCS (`gs://<project>-runs` with `RUNS_RETENTION_DAYS=30` lifecycle deletion), and creates `ocr-api@` + `ocr-mcp@` service accounts.
2. **Secrets (Secret Manager):**
   - `openrouter-api-key` (from `OPENROUTER_API_KEY`; rotate with `ROTATE_OPENROUTER_KEY=1`).
   - `ocr-client-token` (`ocr_pub_...` shared fallback bearer token, saved locally to `.cloud-token` `chmod 600`; rotate with `ROTATE_CLIENT_TOKEN=1`).
   - Optional `supabase-service-key` + `supabase-jwt-secret`: never created by the script, automatically attached to `ocr-api` if **both** already exist in Secret Manager.
3. **`ocr-api` service (`api`):**
   - Deployed with `--execution-environment gen2`, `--no-cpu-throttling` (background `ThreadPoolExecutor` runs continue after HTTP `200` returns), `cpu=1`, `memory=1Gi`, `concurrency=20`, `min=0`, `max=3`, `timeout=600`.
   - Mounts `gs://<project>-runs` at `/mnt/data` (`OCR_RUNS_DIR=/mnt/data/runs`, fallback `OCR_RATE_LIMIT_STATE_FILE=/mnt/data/quota/rate_limit.json`).
   - Sets production defaults (`OCR_ENV=production`, `OCR_ALLOW_PATH_INPUT=false`, `OCR_MAX_UPLOAD_MB=20`, `OCR_RATE_LIMIT_PER_MINUTE=3`, `OCR_RATE_LIMIT_PER_DAY=50`, `OCR_STALE_RUN_SECONDS=900`, `OCR_DEFAULT_EXTRACTOR_PROVIDER=openrouter`, `OCR_DEFAULT_EXTRACTOR_MODEL=google/gemini-4-carbon`, `OCR_DEFAULT_EXTRACTOR_REASONING={"effort":"low","exclude":true}`, `OCR_CORS_ORIGINS`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`).
4. **`ocr-mcp` service (`mcp`):**
   - Deployed with `cpu=1`, `memory=512Mi`, `max=2`, `timeout=600`, `OCR_SERVICE=mcp`, `OCR_ENV=production`, `MCP_TRANSPORT=http`, `MCP_ALLOW_PATH_INPUT=false`, `FASTMCP_STATELESS_HTTP=true`, `OCR_API_BASE_URL=<ocr-api url>`, `OCR_API_TIMEOUT_SECONDS=300`, and secrets `MCP_AUTH_TOKEN` + `OCR_API_KEY` mapped to `ocr-client-token:latest`.

### Continuous deployment (`cloudbuild.yaml`)

- Triggered on every push to `main` (trigger `ocr-fiba-main-deploy`, region `us-central1`, running as `ocr-deployer@ocr-fiba-8d0920.iam.gserviceaccount.com` without secret read permissions).
- Pipeline steps: `build` (`$SHORT_SHA` and `latest`) → `push` → `deploy-api` → `deploy-mcp` (`gcloud run deploy --image` only, preserving env vars, secrets, GCS mounts, and limits managed by `deploy_cloudrun.sh`) → `smoke-test` (`200 /health`, `401 /v1/runs/smoke-test`, `401 /mcp`).
- Manual equivalent:

```bash
gcloud builds submit --config cloudbuild.yaml --region us-central1 \
  --service-account projects/ocr-fiba-8d0920/serviceAccounts/ocr-deployer@ocr-fiba-8d0920.iam.gserviceaccount.com \
  --substitutions SHORT_SHA=$(git rev-parse --short HEAD) .
```

- **Important:** Because `cloudbuild.yaml` only swaps the container image, re-run `scripts/deploy_cloudrun.sh api` (or `mcp`) whenever you change env vars, Secret Manager bindings, or CORS origins.

---

## 3. Web App on Vercel (`packages/web`)

1. Configure Vercel **Root Directory** to `packages/web` (leave the default `npm run build` / Next.js preset; no `vercel.json` is needed).
2. Set environment variables in Vercel:

| Variable | Scope | Required | Notes |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Browser + Server | Yes | Supabase project URL. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Browser + Server | Yes* | Legacy anon key (*or set `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`). |
| `NEXT_PUBLIC_OCR_API_URL` | Browser + Server | Yes | Public `ocr-api` Cloud Run URL. |
| `SUPABASE_SERVICE_KEY` | Server only | Yes | Service-role key for `/admin` & invite acceptance. Never prefix with `NEXT_PUBLIC_`. |
| `NEXT_PUBLIC_SITE_URL` | Browser + Server | Optional | Canonical origin for invite `redirectTo` links. |
| `AIRTABLE_TOKEN`, `AIRTABLE_BASE_ID`, `AIRTABLE_LEAGUE_TABLE` | Server only | Optional | Required only for the referee league view (`/api/league/submissions`). |

3. **Post-deploy CORS follow-up:** Copy the deployed Vercel origin (e.g. `https://<project>.vercel.app`) and update `ocr-api` CORS:

```bash
OCR_CORS_ORIGINS="https://<project>.vercel.app" scripts/deploy_cloudrun.sh api
```

Never add `OCR_ENGINE_API_KEY` or `ocr_live_` keys to Vercel. Browser users authenticate with their Supabase session JWT.

---

## 4. Supabase setup & operations scripts (`supabase/`, `scripts/`)

- **Migrations (`supabase/migrations/`):** Contains 9 SQL migrations (`accounts`, `api_keys`, `handle_new_user()`, `admin_invitations`, `private.rate_limit_events`, `consume_rate_limit`). Before applying against an already-initialized remote database, verify the timestamp discrepancy notes in `20261116033000_restrict_admin_role_to_app_metadata.sql` (`20260620085016` vs `20260620090000`) and `20261116181000_fix_consume_rate_limit_greatest.sql` (`20261116180236` vs `20261116180000`).
- **Provisioning & smoke scripts (`scripts/`):**
  - `scripts/create_admin_user.py` — creates/promotes a Supabase Auth user to `role='admin'` (`app_metadata.role='admin'`).
  - `scripts/issue_api_key.py` — creates/updates a tester account and writes a new `ocr_live_` key strictly to `--output` (`chmod 600`, never printed to stdout/stderr).
  - `scripts/smoke_async_api.py --image <path>` — end-to-end async HTTP smoke check (`upload → poll → result`).
  - `scripts/smoke_async_mcp.py --image <path>` — end-to-end async MCP smoke check.

---

[← Adapters & Web](codebase/adapters-and-web.md) | [Codebase Guide →](CODEBASE-GUIDE.md)
