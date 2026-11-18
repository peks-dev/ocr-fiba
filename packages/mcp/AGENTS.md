# mcp — AGENTS.md

> Local guardrails for `packages/mcp/` (`ocr_engine_mcp`).
> Read [`/AGENTS.md`](../../AGENTS.md) and [`/docs/codebase/adapters-and-web.md`](../../docs/codebase/adapters-and-web.md) before modifying code here.

## Context & Stack

`FastMCP` (`fastmcp==3.2.4`) + `requests` adapter exposing 10 OCR tools, 4 JSON resources (`run://`, `result://`, `trace://`, `artifact://`), and 3 prompts over `stdio` or Streamable HTTP (`/mcp`). Pure HTTP client of `ocr-engine-api` via `OcrApiClient` with zero dependency on `ocr_engine_core`.

## Local Verification

```bash
uv run pytest tests/test_mcp_client.py tests/test_mcp_auth.py tests/test_phase3_api_mcp_hardening.py
```

## Non-Negotiable Rules (`NEVER`)

- **NEVER** import `ocr_engine_core`, `ocr_engine_api`, or `ocr_engine_cli`.
- **NEVER** access `runs/` directly from disk; all reads/writes go through `OcrApiClient`.
- **NEVER** let `OcrApiError` propagate unhandled out of tools or resources; use `tools.handle_api_error`.
- **NEVER** enable `submit_scoresheet_from_path` in production (`OCR_ENV=production` / `MCP_ALLOW_PATH_INPUT=false`).
- **NEVER** weaken `McpTokenVerifier` (`auth.py`) to accept arbitrary tokens when `MCP_AUTH_TOKEN` is set.

## Pointers

- Adapters & MCP design: [`docs/codebase/adapters-and-web.md`](../../docs/codebase/adapters-and-web.md)
- MCP server usage & config: [`packages/mcp/docs/mcp-server.md`](./docs/mcp-server.md)
- Cloud Run deployment: [`docs/DEPLOYMENT.md`](../../docs/DEPLOYMENT.md)
