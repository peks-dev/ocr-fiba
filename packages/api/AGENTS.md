# api — AGENTS.md

> Domain-specific guidance for AI agents working on `packages/api/`.
> Cross-cutting rules live in [`/AGENTS.md`](../../../AGENTS.md). Read both before editing.

## Context

FastAPI HTTP adapter for the FIBA OCR engine. Exposes runs (`POST /v1/runs`, `POST /v1/runs/upload`, `GET /v1/runs/{run_id}`, `GET /v1/runs/{run_id}/result`, `GET /v1/runs/{run_id}/artifacts`, `DELETE /v1/runs/{run_id}`) the Supabase-backed `/v1/me/*` API key management, and admin `/v1/admin/*` key management for other accounts. All OCR work is delegated to `ocr_engine_core`; this package is the HTTP shape of the product.

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
    ├── auth_api_key.py        # ocr_live_ API key auth + locked 1024-entry 60s cache + invalidation
    ├── auth_supabase.py       # Supabase JWT verification (HS256 + locked 1024-entry 30s asymmetric cache)
    ├── supabase_client.py     # Server-side Supabase client factory
    ├── routes/
    │   ├── runs.py            # /v1/runs/*
    │   ├── me.py              # /v1/me/*  (registered only when has_supabase)
    │   └── admin.py           # /v1/admin/* (registered only when has_supabase)
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
- Mounts `routes/me.router` and `routes/admin.router` only when `settings.has_supabase` is true.

When adding a new router, follow the same conditional pattern based on a `settings.*` flag.

### 2. Auth is layered

Four auth surfaces, in priority order:

1. **`api_key_auth` middleware** (always on): detects Bearer tokens starting with `ocr_live_` and validates them via `auth_api_key.validate_api_key` (offloaded with `asyncio.to_thread` alongside `validate_supabase_session` and `rate_limiter.check`). When Supabase is configured, three-part JWTs are validated with `auth_supabase.validate_supabase_session` and `request.state.account_id` is set so run quotas are keyed on the account (`acct:{id}`), shared with that account's `ocr_live_` keys. Shared `ocr_pub_` tokens fall through to the static bearer check. Uses exact/prefix boundary checks for `/v1/me` and `/v1/admin`, and skips `OPTIONS`.
2. **Static bearer** (fallback): `auth.is_authorized(settings.api_key)`.
3. **Supabase JWT on `/v1/me/*`**: `auth_supabase.require_supabase_user`.
4. **Admin JWT on `/v1/admin/*`**: `routes.admin.require_admin_account` (session JWT + `public.accounts.role == admin`).

When adding a new endpoint:

- If it lives under `/v1/runs/*`, the middleware already gates it (Bearer required: `ocr_live_`, session JWT, or static token).
- If it lives under `/v1/me/*`, use `Depends(require_supabase_user)`.
- If it lives under `/v1/admin/*`, use `Depends(require_admin_account)`.
- For health/internal endpoints, add to the exempt list in `auth.py`.
- `OCR_CORS_ORIGINS` is a comma-separated origin list. Leave it empty on Cloud Run until the Vercel production URL is known, then pass it to `scripts/deploy_cloudrun.sh`.

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

`services/run_repository.py` implements `RunRepository` over the `runs/` directory (`reserve_run_dir` atomically allocates new run folders -> `409 RUN_ALREADY_EXISTS`; `_write_status` writes atomically via temp file + `os.replace`; `_reconcile_active_status` recovers crashed runs with `result.json` or marks active runs past `OCR_STALE_RUN_SECONDS` as `RUN_STALLED`). Uploads on `POST /v1/runs/upload` enforce bounded chunked reads and JPEG/PNG/WebP magic-byte verification. It understands the canonical run layout (see core-engine `artifacts.py`). Adding a new query:

1. Add a method on `RunRepository` that reads from `runs/<run_id>/...`.
2. Raise `RunRepositoryError` with a typed `code` on failure (so routes can map it to an HTTP status).
3. Add a test under `tests/test_run_repository.py`.

### 6. `/v1/me/*` is Supabase-only

`me.py` is only registered when `settings.has_supabase` is true. Endpoints here expect a Supabase user (validated via JWT) and operate on the `accounts` and `api_keys` tables. Key lifecycle:

- `POST /v1/me/api-keys/bootstrap` → returns the raw key exactly once. If an active key already exists, it returns `409 API_KEY_ALREADY_EXISTS` rather than deleting it. Use `POST /v1/me/api-keys` for additional keys.
- `POST /v1/me/api-keys` → create a named key.
- `GET /v1/me/api-keys` → list (excludes the secret).
- `DELETE /v1/me/api-keys/{key_id}` → hard delete (we **do not** use revoked keys).

### 7. `/v1/admin/*` is admin-only

`admin.py` is only registered when `settings.has_supabase` is true. The caller must be an active account with `role == admin` in `public.accounts` (not user-editable metadata).

- `GET /v1/admin/accounts` → list accounts for the admin picker (includes invited testers).
- `GET /v1/admin/accounts/{account_id}/api-keys` → list keys for that account (no raw secrets).
- `POST /v1/admin/accounts/{account_id}/api-keys?name=` → issue a key; raw value returned once.
- `DELETE /v1/admin/accounts/{account_id}/api-keys/{key_id}` → hard delete (UI may label this Revoke).

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
