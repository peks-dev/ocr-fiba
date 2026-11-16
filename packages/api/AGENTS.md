# api — AGENTS.md

> Domain-specific guidance for AI agents working on `packages/api/`.
> Cross-cutting rules live in [`/AGENTS.md`](../../../AGENTS.md). Read both before editing.

## Context

FastAPI HTTP adapter for the FIBA OCR engine. Exposes runs (`POST /v1/runs`, `POST /v1/runs/upload`, `GET /v1/runs/{run_id}`, `GET /v1/runs/{run_id}/result`, `GET /v1/runs/{run_id}/artifacts`, `DELETE /v1/runs/{run_id}`) and the Supabase-backed `/v1/me/*` API key management. All OCR work is delegated to `ocr_engine_core`; this package is the HTTP shape of the product.

## Stack

- Python ≥ 3.12
- FastAPI ≥ 0.115, uvicorn ≥ 0.30
- `python-multipart` for upload endpoints
- `supabase` ≥ 2.0 (server client) and `pyjwt` ≥ 2.0 (legacy HS256 verification)
- `Pydantic` (transitive, used for request/response schemas)

## Structure

```text
packages/api/
├── pyproject.toml
└── src/ocr_engine_api/
    ├── __init__.py
    ├── main.py                # create_app(), run(), _load_project_env()
    ├── settings.py            # Pydantic settings + has_supabase flag
    ├── pipeline_options.py    # Parse/validate RunContext options
    ├── schemas.py             # Pydantic request/response models
    ├── responses.py           # sanitize_for_public_response
    ├── errors.py              # error_response, engine_error_response
    ├── api_keys.py            # generate/hash/list/find API keys
    ├── auth.py                # Static-bearer auth (local dev)
    ├── auth_api_key.py        # ocr_*-prefixed API key auth + 60s cache
    ├── auth_supabase.py       # Supabase JWT verification (HS256 + asymmetric)
    ├── supabase_client.py     # Server-side Supabase client factory
    ├── routes/
    │   ├── runs.py            # /v1/runs/*
    │   └── me.py              # /v1/me/*  (registered only when has_supabase)
    └── services/
        ├── run_executor.py    # Wraps FibaOcrPipeline.process with sanitization
        └── run_repository.py  # Filesystem-backed RunRepository (lists, reads, deletes runs)
```

## Patterns

### 1. Composition root: `create_app()`

`main.create_app()` is the only place where the FastAPI app is assembled. It:

- Loads `.env` via `_load_project_env()` (walks up from cwd and module path).
- Configures CORS only if `settings.cors_origins` is set.
- Registers `api_key_auth` middleware (always on, with exempt URLs).
- Mounts `routes/runs.router` unconditionally.
- Mounts `routes/me.router` only when `settings.has_supabase` is true.

When adding a new router, follow the same conditional pattern based on a `settings.*` flag.

### 2. Auth is layered

Three auth surfaces, in priority order:

1. **`api_key_auth` middleware** (always on): detects Bearer tokens starting with `ocr_live_` and validates them via `auth_api_key.validate_api_key`. Shared `ocr_pub_` tokens fall through to the static bearer check. Skips `/v1/me/*` and `OPTIONS`.
2. **Static bearer** (fallback when Supabase is not configured): `auth.is_authorized(settings.api_key)`.
3. **Supabase JWT** (only for `/v1/me/*`): `auth_supabase.require_supabase_user`.

When adding a new endpoint:

- If it lives under `/v1/runs/*`, the middleware already gates it (Bearer required).
- If it lives under `/v1/me/*`, use `Depends(require_supabase_user)`.
- For health/internal endpoints, add to the exempt list in `auth.py`.

### 3. Standard error envelope

Never return a raw `HTTPException` to clients. Use the helpers in `errors.py`:

```python
from ocr_engine_api.errors import error_response, engine_error_response

# explicit error
raise error_response(400, "EMPTY_UPLOAD", "Image is empty", retryable=False)

# error from the core engine
try:
    ...
except OcrEngineError as exc:
    raise engine_error_response(exc)   # → HTTP 422 with exc.to_dict()
```

Error envelopes are: `{ "error": { "code": str, "message": str, "retryable": bool, "details": {...}? } }`. Tests in `tests/test_api.py` assert this shape.

### 4. Response sanitization

`responses.sanitize_for_public_response` strips internal fields (e.g. absolute file paths, internal run ids, provider debug info) before sending a run to the client. Use it in every route that returns a run's result. The MCP and CLI use the same helper indirectly through the API.

### 5. Run repository is filesystem-backed

`services/run_repository.py` implements `RunRepository` over the `runs/` directory. It understands the canonical run layout (see core-engine `artifacts.py`). Adding a new query:

1. Add a method on `RunRepository` that reads from `runs/<run_id>/...`.
2. Raise `RunRepositoryError` with a typed `code` on failure (so routes can map it to an HTTP status).
3. Add a test under `tests/test_run_repository.py`.

### 6. `/v1/me/*` is Supabase-only

`me.py` is only registered when `settings.has_supabase` is true. Endpoints here expect a Supabase user (validated via JWT) and operate on the `accounts` and `api_keys` tables. Key lifecycle:

- `POST /v1/me/api-keys/bootstrap` → returns the raw key exactly once. If an active key already exists, it returns `409 API_KEY_ALREADY_EXISTS` rather than deleting it. Use `POST /v1/me/api-keys` for additional keys.
- `POST /v1/me/api-keys` → create a named key.
- `GET /v1/me/api-keys` → list (excludes the secret).
- `DELETE /v1/me/api-keys/{key_id}` → hard delete (we **do not** use revoked keys).

## Rules specific to api

- **NEVER** import from `ocr_engine_mcp` or `ocr_engine_cli` (they are downstream of the API).
- **NEVER** add a route that returns absolute file paths or raw provider errors. Always sanitize.
- **NEVER** store the raw API key in `api_keys` — only its SHA-256 hash. The raw key is returned to the user exactly once.
- **NEVER** weaken the auth middleware to skip the Bearer check for `/v1/runs/*`, even in development. Use `OCR_ENGINE_API_KEY` and the static-bearer fallback instead.
- Use `error_response` and `engine_error_response` — never `HTTPException(status_code=..., detail=...)` directly.
- New env vars go into `settings.py` with a default and a Pydantic validator.

## Auto-invoke skills (per task)

| Task | Skill |
|---|---|
| Pre-completion security check (new endpoint or input surface) | `audit-security-implementation` |
| Optimizing slow Python code | `python-codebase-optimization` |
| Git operations | `git-commit-creation` |

## References

- `create_app` — `src/ocr_engine_api/main.py`
- Error helpers — `src/ocr_engine_api/errors.py`
- API key auth — `src/ocr_engine_api/auth_api_key.py`
- Supabase auth — `src/ocr_engine_api/auth_supabase.py`
- Run repository — `src/ocr_engine_api/services/run_repository.py`
- First-party skills:
  - `packages/api/skills/api-error-envelope/SKILL.md`
  - `packages/api/skills/api-key-auth/SKILL.md`
