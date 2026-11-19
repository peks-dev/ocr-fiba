# MCP Server

Remote `FastMCP` adapter for the FIBA OCR Engine HTTP API (`ocr_engine_mcp`).

The MCP server never imports or runs `ocr_engine_core` directly. Every tool, resource, and prompt delegates to `OcrApiClient` over HTTP against `OCR_API_BASE_URL`.

For architecture details, internal module roles, and deployment workflows, see:
- [Adapters and Web (`docs/codebase/adapters-and-web.md`)](../../../docs/codebase/adapters-and-web.md#2-mcp-server-packagesmcp-ocr_engine_mcp)
- [Deployment and Operations (`docs/DEPLOYMENT.md`)](../../../docs/DEPLOYMENT.md)

## Configuration

```bash
export OCR_API_BASE_URL="http://127.0.0.1:8000"
export OCR_API_KEY=""               # Matches OCR_ENGINE_API_KEY (or fallback when static MCP_AUTH_TOKEN is used)
export OCR_API_TIMEOUT_SECONDS=300
```

## Transports

### Local stdio (default)

```bash
python mcp_server.py
```

Uses `OCR_API_KEY` for upstream API calls (`MCP_AUTH_TOKEN` is ignored on stdio).

### Streamable HTTP

```bash
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8001 uv run ocr-mcp
```

Exposes `http://<host>:<port>/mcp`. Set `MCP_AUTH_TOKEN` to require bearer auth on incoming MCP HTTP requests:
- **Static `MCP_AUTH_TOKEN`:** Validated in constant time; server calls the API using `OCR_API_KEY`.
- **Per-client `ocr_live_<64 hex>` keys:** Verified via `GET /v1/runs?limit=1` against the API (60s in-memory cache) and forwarded directly upstream so per-account rate limits apply.

Set `MCP_ALLOW_PATH_INPUT=false` (default when `OCR_ENV=production`) to hide `submit_scoresheet_from_path` and enforce `submit_scoresheet_base64`.

## Surface Summary

- **Tools (10):** `submit_scoresheet_from_path` (dev/opt-in), `submit_scoresheet_base64`, `poll_run`, `wait_for_run`, `list_runs`, `inspect_run`, `get_run_result`, `get_run_trace`, `list_run_artifacts`, `get_artifact`.
- **Resources (4):** `run://{run_id}`, `result://{run_id}`, `trace://{run_id}`, `artifact://{run_id}/{artifact_name}`.
- **Prompts (3):** `review_extraction(run_id)`, `suggest_retry_strategy(run_id)`, `explain_validation_warnings(run_id)`.
