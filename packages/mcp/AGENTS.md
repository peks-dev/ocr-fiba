# mcp — AGENTS.md

> Domain-specific guidance for AI agents working on `packages/mcp/`.
> Cross-cutting rules live in [`/AGENTS.md`](../../../AGENTS.md). Read both before editing.

## Context

MCP (Model Context Protocol) server adapter. Wraps the FIBA OCR HTTP API as agent-friendly tools, resources, and prompts. The MCP server does **not** import the core engine — it is purely an HTTP client of the API. This keeps the OCR process isolated from the agent runtime.

Per-package docs: [`docs/mcp-server.md`](./docs/mcp-server.md) (configuration, transports, production notes).

## Stack

- Python ≥ 3.12
- `fastmcp` (provides the `@mcp.tool`, `@mcp.resource`, `@mcp.prompt` decorators and the stdio/HTTP transports)
- `requests` for HTTP calls to the API
- Zero dependency on the OCR core engine

## Structure

```text
packages/mcp/
├── pyproject.toml
└── src/ocr_engine_mcp/
    ├── __init__.py
    ├── server.py    # FastMCP app, tool/resource/prompt definitions
    ├── client.py    # OcrApiClient (HTTP client to the OCR API)
    └── tools.py     # Business logic for each tool (uses OcrApiClient)
```

## Patterns

### 1. Tools wrap `OcrApiClient`, not the core engine

Every MCP tool function in `server.py` delegates its work to a helper in `tools.py`. The helpers in `tools.py` call `OcrApiClient` methods. **Do not** import `ocr_engine_core` from this package.

Adding a new tool:

1. Add an `OcrApiClient` method in `client.py` (typed input → typed output, raises `OcrApiError`).
2. Add a tool function in `tools.py` that calls the client and handles errors via `handle_api_error`.
3. Register the tool in `server.py` with `@mcp.tool()` and a descriptive docstring.
4. Document the tool in `docs/mcp-server.md`.

### 2. Error mapping via `handle_api_error`

`tools.handle_api_error` translates `OcrApiError` (from the client) into the structured error shape the MCP server surfaces to agents. Never let `OcrApiError` propagate raw to the MCP runtime — agents should see a friendly message, not an HTTP status.

### 3. Resources expose run state

Resources (`@mcp.resource("run://{run_id}")`, `@mcp.resource("artifact://{run_id}/{name}")`) are read-only views of run state. They use the same `OcrApiClient` under the hood; resource handlers are thin and should not contain business logic.

### 4. Auth: static MCP token or per-client `ocr_live_` keys

HTTP transport requires a bearer token when `MCP_AUTH_TOKEN` is set. Clients may send:

- The static `MCP_AUTH_TOKEN` (legacy shared token). The MCP server then calls the API with `OCR_API_KEY`.
- A per-client `ocr_live_<64 hex>` key. The MCP verifier probes `GET /v1/runs?limit=1` on the API (short cache) and, if valid, forwards that same key on every subsequent API call so quota and identity stay per client.

Stdio and local HTTP without `MCP_AUTH_TOKEN` stay unauthenticated and use `OCR_API_KEY`. See `docs/mcp-server.md`.

### 5. Transport selection

- **stdio** (default; used by local agents like Warp): `python mcp_server.py` (the repo-root wrapper delegates to `ocr_engine_mcp.server`).
- **HTTP** (used by remote agents / hosting): `MCP_TRANSPORT=http MCP_HOST=... MCP_PORT=... python -m adapters.mcp.server`.

## Tools and resources (current)

| Tool | Purpose |
|---|---|
| `submit_scoresheet_from_path` | Submit a local image path → returns `run_id` |
| `submit_scoresheet_base64` | Submit an in-memory base64 image → returns `run_id` |
| `poll_run` | One-shot status of a run |
| `wait_for_run` | Block until the run completes/fails/times out |
| `list_runs` | Recent runs |
| `inspect_run` | Run summary + MCP resource URIs |
| `get_run_result` | Structured OCR result |
| `get_run_trace` | Full audit trace |
| `list_run_artifacts` | Visual + JSON artifacts produced by the run |

Resources:

- `run://{run_id}`
- `artifact://{run_id}/{artifact_name}`

## Rules specific to mcp

- **NEVER** import from `ocr_engine_core`, `ocr_engine_api`, or `ocr_engine_cli`. This package is an HTTP client only.
- **NEVER** make `OcrApiError` propagate raw. Use `handle_api_error`.
- **NEVER** call the OCR engine directly. Always go through the API.
- Tool docstrings are shown to agents. Keep them concrete: state what the tool does, what it returns, and any preconditions (e.g. "Requires OCR_API_KEY set; max upload 20 MB").
- All `OcrApiClient` methods must be typed and raise `OcrApiError(status_code, code, message, details)` on failure.

## Auto-invoke skills (per task)

| Task | Skill |
|---|---|
| Pre-completion security check (new tool or auth surface) | `audit-security-implementation` |
| Git operations | `git-commit-creation` |

## References

- `server.py` — FastMCP app, all tool/resource/prompt definitions
- `client.py` — `OcrApiClient` and `OcrApiError`
- `tools.py` — tool implementations and `handle_api_error`
- `docs/mcp-server.md` — configuration, transports, production notes
