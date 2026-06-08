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
  python -m adapters.mcp.server
```

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
