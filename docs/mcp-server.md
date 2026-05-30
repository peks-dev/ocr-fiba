# MCP Server

Remote MCP adapter for the FIBA OCR Engine API.

The MCP server does not import or execute the OCR core. It calls the HTTP API and exposes agent-friendly tools, resources, and prompts.

## Configuration

```bash
export OCR_API_BASE_URL="http://127.0.0.1:8000"
export OCR_API_KEY=""  # set this to OCR_ENGINE_API_KEY when API auth is enabled
export OCR_API_TIMEOUT_SECONDS=120
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
```

In production mode the API ignores client-provided `runs_dir` and uses `OCR_RUNS_DIR`.

Production API responses also hide local filesystem paths and expose relative API links instead. MCP tools should rely on `run_id`, artifact names, and resource/API links rather than local paths.

## Run Locally With STDIO

```bash
python mcp_server.py
```

## Run Over HTTP

```bash
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8001 python -m adapters.mcp.server
```

Equivalent:

```bash
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8001 python mcp_server.py
```

ASGI deployment can import:

```text
adapters.mcp.server:app
```

## Tools

```text
process_scoresheet_from_path(image_path, run_id?, options?)
process_scoresheet_base64(image_base64, filename?, run_id?, options?)
list_runs(limit?)
inspect_run(run_id)
get_run_result(run_id)
get_run_trace(run_id)
list_run_artifacts(run_id, limit?)
get_artifact(run_id, artifact_name)
```

`process_scoresheet_from_path` requires the image path to be accessible to the OCR API service. For remote users, `process_scoresheet_base64` is the safer first interface because it uploads the image through the MCP tool call.

## Resources

```text
run://{run_id}
result://{run_id}
trace://{run_id}
artifact://{run_id}/{artifact_name}
```

## Prompts

```text
review_extraction(run_id)
suggest_retry_strategy(run_id)
explain_validation_warnings(run_id)
```

## Production Notes

- The API remains the source of truth for execution, auth, persistence, and artifacts.
- `runs_dir` is intentionally not exposed through MCP tools.
- Artifacts are returned as base64 for the MVP; production should prefer signed URLs or object storage references for large files.
