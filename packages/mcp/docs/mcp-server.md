# MCP Server

Remote MCP adapter for the FIBA OCR Engine API.

The MCP server does not import or execute the OCR core. It calls the HTTP API and exposes agent-friendly tools, resources, and prompts.

## Configuration

```bash
export OCR_API_BASE_URL="http://127.0.0.1:8000"
export OCR_API_KEY=""  # set this to OCR_ENGINE_API_KEY when API auth is enabled
export OCR_API_TIMEOUT_SECONDS=300
```

When the OCR API has `OCR_ENGINE_API_KEY` configured, the MCP server sends it as:

```text
Authorization: Bearer <OCR_API_KEY>
```

For production-like API runs, configure the API with:

```bash
export OCR_ENV=production
export OCR_ENGINE_API_KEY="same-secret-used-by-mcp"
export OCR_RUNS_DIR="/srv/ocr-engine/runs"
export OCR_MAX_UPLOAD_MB=20
```

In production mode the API ignores client-provided `runs_dir` and uses `OCR_RUNS_DIR`.

## Run locally (stdio)

```bash
python mcp_server.py
```

The repo-root `mcp_server.py` is a thin wrapper that delegates to `ocr_engine_mcp.server` for stdio transport.

## Run as HTTP server

```bash
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8001 \
  uv run ocr-mcp
```

The streamable HTTP endpoint is `http://<host>:<port>/mcp`.

### Bearer auth on HTTP transport

Set `MCP_AUTH_TOKEN` to require `Authorization: Bearer <MCP_AUTH_TOKEN>` on every MCP HTTP request
(unset = no auth, fine for loopback-only use). Stdio transport ignores it.

## Run API + MCP as background services

`scripts/serve.sh {start|stop|restart|status|urls}` runs `ocr-api` (127.0.0.1:8000) and `ocr-mcp`
(127.0.0.1:8001/mcp) under a restart loop, in production mode, with one shared bearer token stored
in `.server-token` (generated on first start, chmod 600, gitignored). Logs and PIDs go to `.server/`.
`OCR_SERVE_TUNNEL=1` also starts Cloudflare quick tunnels (needs outbound port 7844).

## Tools and resources

- `run`: kick off a new OCR run against the API
- `result`: fetch a run result
- `artifacts`: list artifacts for a run
- Resources:
  - `run://{run_id}` — current state of a run
  - `artifact://{run_id}/{artifact_name}` — a specific artifact's URL

## Production notes

- Set `OCR_ENV=production` in the API so it ignores client `runs_dir` and enforces `OCR_RUNS_DIR`.
- Use a long-lived `OCR_ENGINE_API_KEY` and share it with the MCP server via `OCR_API_KEY`.
- Keep `OCR_RUNS_DIR` on a persistent volume so artifacts survive restarts.

## Public deployment (Google Cloud Run)

`scripts/deploy_cloudrun.sh` builds one image (`Dockerfile`) and deploys two services:
`ocr-api` (REST, runs stored on a GCS bucket mounted at `/mnt/data`) and `ocr-mcp`
(streamable HTTP at `/mcp`, stateless, calling `ocr-api`). Both require
`Authorization: Bearer <token>`; the token lives in Secret Manager (`ocr-client-token`) and
locally in `.cloud-token`. In production `submit_scoresheet_from_path` is not registered
(`MCP_ALLOW_PATH_INPUT`), so clients must use `submit_scoresheet_base64`.

### Continuous deployment (push to `main`)

`main` is the production branch: every push to `main` runs the Cloud Build trigger
`ocr-fiba-main-deploy` (region `us-central1`, GitHub connection `ocr-fiba-github`), which
executes `cloudbuild.yaml`:

1. builds the image and pushes it to Artifact Registry tagged `$SHORT_SHA` and `latest`;
2. deploys `ocr-api`, then `ocr-mcp`, with `gcloud run deploy --image` only, so env vars,
   Secret Manager references, the GCS volume, service accounts and limits stay as last set by
   `scripts/deploy_cloudrun.sh`;
3. smoke-tests the public URLs (`/health` → 200, API and MCP without token → 401). A failed
   check marks the build as failed; the new revision is already serving, so roll back with
   `gcloud run services update-traffic <service> --to-revisions <previous>=100`.

The build runs as `ocr-deployer@ocr-fiba-8d0920.iam.gserviceaccount.com` with only:
`roles/run.developer` and `roles/logging.logWriter` (project), `roles/artifactregistry.writer`
(on the `ocr-fiba` repository), `roles/iam.serviceAccountUser` (on the `ocr-api` and `ocr-mcp`
runtime service accounts) and `roles/storage.objectViewer` (on the `<project>_cloudbuild`
staging bucket, for manual `gcloud builds submit`). It reads no secrets.

`scripts/deploy_cloudrun.sh` remains the manual fallback and the place to change service
configuration (flags, env vars, secrets, limits): run it after editing those, since CD only
swaps the image. To run the pipeline by hand from a checkout:

```bash
gcloud builds submit --config cloudbuild.yaml --region us-central1 \
  --service-account projects/ocr-fiba-8d0920/serviceAccounts/ocr-deployer@ocr-fiba-8d0920.iam.gserviceaccount.com \
  --substitutions SHORT_SHA=$(git rev-parse --short HEAD) .
```
