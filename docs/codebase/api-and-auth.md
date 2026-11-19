[← Codebase Guide](../CODEBASE-GUIDE.md) | [← Previous: Core Pipeline](core-pipeline.md) | [Next: Adapters & Web →](adapters-and-web.md)

# API, Auth, and Supabase

**`packages/api` (`ocr_engine_api`) is the FastAPI HTTP surface and security boundary around `ocr_engine_core`.** It owns request validation, layered authentication, run-creation quotas, async background execution, filesystem run persistence, response sanitization, and Supabase Postgres integration.

## Composition root: `create_app()`

`main.py` (`create_app()`) is the single assembly point for the FastAPI app:

1. Calls `_load_project_env()` (walks up from `cwd` and module path to load `.env` without overriding existing environment variables).
2. Loads and validates `ApiSettings` via `get_api_settings()` / `validate_api_settings()`.
3. Registers `CORSMiddleware` when `settings.cors_origins` (`OCR_CORS_ORIGINS`) is non-empty.
4. Always mounts `routes/runs.router` (`/v1/runs/*`) and `GET /health`.
5. Conditionally mounts `routes/me.router` (`/v1/me/*`) and `routes/admin.router` (`/v1/admin/*`) **only when `settings.has_supabase` is true**.
6. Initializes `RunRateLimiter` (`SupabaseRateLimitStore` if `settings.has_supabase_service`, else `MemoryRateLimitStore`).
7. Registers `api_key_auth` HTTP middleware and the catch-all `unexpected_error_handler` (`500 INTERNAL_SERVER_ERROR` with no internal exception details).

---

## HTTP endpoints

### Health and runs (`main.py`, `routes/runs.py`)

| Method & path | Auth | Purpose & behavior |
|---|---|---|
| `GET /health` | Exempt | Liveness check (`{"status": "ok"}`). |
| `POST /v1/runs` | Middleware | Starts an async run from server-side `image_path` (`CreateRunRequest`). Returns `403 PATH_INPUT_DISABLED` when `OCR_ALLOW_PATH_INPUT=false` (production default). Returns HTTP `200` with `{"success": True, ...status}` (`status="queued"`). |
| `POST /v1/runs/upload` | Middleware | Accepts multipart `file` (`.jpg`, `.jpeg`, `.png`, `.webp`) + optional `run_id`, `runs_dir`, `options_json`. Enforces chunked size bound (`OCR_MAX_UPLOAD_MB`, default `20` MB → `413 UPLOAD_TOO_LARGE` / `400 EMPTY_UPLOAD`) and JPEG/PNG/WebP magic bytes (`400 INVALID_IMAGE_CONTENT`). Returns HTTP `200` (`status="queued"`). |
| `GET /v1/runs` | Middleware | Lists runs sorted by mtime (`limit` `1..200`, default `50`). |
| `GET /v1/runs/{run_id}` | Middleware | Returns run summary + up to 20 artifact records and `artifacts_count`. |
| `DELETE /v1/runs/{run_id}` | Middleware | Deletes `runs/<run_id>/` recursively from disk. |
| `GET /v1/runs/{run_id}/trace` | Middleware | Returns `trace.json` (`404 RUN_FILE_NOT_FOUND` if missing). |
| `GET /v1/runs/{run_id}/result` | Middleware | Returns `result.json` when completed (`409 RUN_NOT_COMPLETED` while queued/running; `422 RUN_FAILED` if failed). |
| `GET /v1/runs/{run_id}/artifacts` | Middleware | Lists files under `runs/<run_id>/artifacts/` (`limit` `1..500`, default `200`). |
| `GET /v1/runs/{run_id}/artifacts/{name:path}` | Middleware | Streams one artifact file via `FileResponse` after path-traversal check (`400 INVALID_ARTIFACT_PATH`). |

### Self-service keys (`/v1/me/*`, Supabase-only, `routes/me.py`)

Requires `Depends(require_supabase_user)` and an active row in `public.accounts`:

- `POST /v1/me/api-keys/bootstrap` — creates the account's first `ocr_live_` key (`name="default"`), returning the raw secret once. Fails with `409 API_KEY_ALREADY_EXISTS` if an active key already exists.
- `GET /v1/me/api-keys` — lists account keys (metadata + `key_prefix` only; never raw secrets).
- `POST /v1/me/api-keys?name=...` — creates an additional named key; returns the raw secret once.
- `DELETE /v1/me/api-keys/{key_id}` — hard-deletes the key row and invalidates `auth_api_key` cache entries for that account.

### Admin key management (`/v1/admin/*`, Supabase-only, `routes/admin.py`)

Requires `Depends(require_admin_account)` (valid Supabase JWT + active `public.accounts` row with `role == "admin"`):

- `GET /v1/admin/accounts` — lists all accounts (for admin UI picker).
- `GET /v1/admin/accounts/{account_id}/api-keys` — lists keys for target account (metadata only).
- `POST /v1/admin/accounts/{account_id}/api-keys?name=...` — issues a key for an active account; returns raw secret once (`403 FORBIDDEN` if target account is inactive).
- `DELETE /v1/admin/accounts/{account_id}/api-keys/{key_id}` — hard-deletes the key and evicts cache for that `account_id`.

---

## Layered authentication and caches

```text
Incoming request
  ├─ OPTIONS or path in {"/health"}                       -> Allow
  ├─ /v1/me* or /v1/admin* (exact or prefix + "/")         -> Pass to route Depends()
  └─ /v1/runs* (via api_key_auth middleware)
       ├─ has_supabase && Bearer starts with "ocr_live_"   -> validate_api_key() [60s cache]
       ├─ has_supabase && 3-part JWT                       -> validate_supabase_session() [30s cache]
       └─ Else (static bearer fallback, incl. "ocr_pub_")  -> secrets.compare_digest(token, OCR_ENGINE_API_KEY)
```

Key implementation rules across auth modules:

- **Per-client API keys (`api_keys.py`, `auth_api_key.py`):** Format is `ocr_live_<64 hex chars>` (`secrets.token_hex(32)`). Visual prefix is `ocr_live_<first 8 hex>...`. Stored exclusively as SHA-256 hex digest (`hash_api_key`). `auth_api_key` uses a thread-locked 1024-entry cache with `TTL_SECONDS = 60`, offloaded in middleware via `asyncio.to_thread`, and fires a best-effort `update_last_used_at` on cache misses.
- **Supabase JWTs (`auth_supabase.py`):**
  - `HS256` tokens verify locally using `SUPABASE_JWT_SECRET`.
  - Asymmetric tokens (`ES256`, `RS256`) verify via `GET {SUPABASE_URL}/auth/v1/user` using `SUPABASE_PUBLISHABLE_KEY` (falling back to `SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, or `SUPABASE_SERVICE_KEY`), cached in a 1024-entry lock-protected cache for `min(30s, remaining_exp)`.
  - Middleware `validate_supabase_session` fetches `public.accounts`, enforces `status == "active"`, and populates `request.state.account_id` and `request.state.account_role`.
- **Supabase readiness flags (`settings.py`):**
  - `has_supabase`: requires `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, **and** `SUPABASE_JWT_SECRET`.
  - `has_supabase_service`: requires `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (sufficient to enable `SupabaseRateLimitStore`).

---

## Run-creation rate limiting (`rate_limit.py`)

Rate limits apply **only** to `POST /v1/runs` and `POST /v1/runs/upload` (`is_run_creation`):

- **Shared account bucket:** `request_rate_limit_key` keys by `acct:{account_id}` when authenticated via `ocr_live_` key or Supabase session JWT (so web session runs and API key runs share one quota), falling back to `tok:{sha256[:16]}` or `ip:{client_host}`.
- **Defaults:** Disabled (`0`) when `OCR_ENV=development`; `3` per minute and `50` per day when `OCR_ENV=production` (`OCR_RATE_LIMIT_PER_MINUTE`, `OCR_RATE_LIMIT_PER_DAY`).
- **Stores:**
  - `SupabaseRateLimitStore` (active whenever `has_supabase_service` is true): calls `consume_rate_limit` RPC (`pg_advisory_xact_lock` in Postgres) so limits hold across Cloud Run instances. **Fails closed** with HTTP `503 RATE_LIMIT_UNAVAILABLE` (`Retry-After: 5`) if the RPC fails.
  - `MemoryRateLimitStore`: local sliding-window fallback with optional `OCR_RATE_LIMIT_STATE_FILE` JSON persistence (single-process only).
- **Exceeded limit:** Returns HTTP `429 RATE_LIMITED` with `Retry-After` header and `details` (`window`, `limit`, `retry_after_seconds`).

---

## Run execution, storage, and sanitization

- **Async executor (`services/run_executor.py`):** Submits runs to a module-level `ThreadPoolExecutor(max_workers=2, thread_name_prefix="ocr-run")` calling `OcrToolbox(config).run_full_pipeline(..., use_run_layout=True)`. Step events (`step_start` / `step_complete`) update `status.json` progress; uncaught `OcrEngineError` records `exc.to_dict()` in `status.json` (`status="failed"`), while unexpected exceptions record a generic `INTERNAL_SERVER_ERROR`.
- **Filesystem repository (`services/run_repository.py`):**
  - Validates `run_id` against `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` (`400 INVALID_RUN_ID`).
  - `reserve_run_dir` atomically allocates `runs/<run_id>/` (`409 RUN_ALREADY_EXISTS` on collision).
  - `_write_status` writes via `NamedTemporaryFile` + `os.replace`.
  - `_reconcile_active_status` recovers crashed `queued`/`running` runs: returns `completed` if valid `result.json` already exists and status age `> 5s`, or returns `failed` (`RUN_STALLED`, `retryable=True`) if age exceeds `OCR_STALE_RUN_SECONDS` (default `900`; `0` disables).
  - Production `resolve_runs_dir` ignores caller `runs_dir` and enforces `settings.runs_dir` (`OCR_RUNS_DIR`).
- **Response sanitization (`responses.py`):**
  - `sanitize_for_public_response` strips `RUN_PATH_KEYS` (`runs_dir`, `run_dir`, `input_dir`, `artifacts_dir`, `raw_dir`, `trace_path`, `result_path`) and `ARTIFACT_PATH_KEYS` (`path`), and ensures `links` (`/v1/runs/{run_id}...`) is populated — **active only when `OCR_ENV=production`** (local dev retains paths for debugging).
- **Error envelopes (`errors.py` vs middleware `JSONResponse`):**
  - Middleware / rate-limiter / 500 handler return `JSONResponse` with top-level `{"success": false, "error": {"code", "message", "retryable", "details"?}}`.
  - Route helpers `error_response(...)` and `engine_error_response(exc)` raise FastAPI `HTTPException(status_code=..., detail={"success": false, "error": ...})` (serialized by FastAPI under `"detail"`). Always use these helpers instead of raw `HTTPException`.

---

## Supabase schema and migrations (`supabase/migrations/`)

Nine SQL migrations define the database layer:

| Object | Schema | Purpose & security model |
|---|---|---|
| `accounts` | `public` | Columns: `id`, `supabase_user_id` (unique FK → `auth.users`), `email`, `status` (`'active'`), `plan` (`'beta'`), `role` (`'admin' \| 'tester'`), `assigned_demo` (`'referee' \| 'player' \| 'club' \| null`), `invited_by`, `invited_at`, `accepted_at`, timestamps. RLS: users read own row; `service_role` full access. Constraint forces non-null `assigned_demo` for `tester`. |
| `api_keys` | `public` | Columns: `id`, `account_id` (FK → `accounts`), `key_hash` (unique SHA-256), `key_prefix`, `name`, `status`, `created_at`, `last_used_at`, `revoked_at`. RLS: `service_role` only. |
| `admin_invitations` | `public` | Tracks invites (`email`, `assigned_demo`, `status` `invited\|accepted\|cancelled\|failed`, `invited_by`, `invited_user_id`, `error_message`). RLS: `service_role` only. |
| `handle_new_user()` | `public` | `SECURITY DEFINER` trigger (`on_auth_user_created`, `set search_path = ''`, execute revoked from `public`/`anon`/`authenticated`). Grants `role='admin'` **only** from `raw_app_meta_data` (never user-editable `raw_user_meta_data`). |
| `rate_limit_events` | `private` | Stores `{id, bucket_key, consumed_at}` with explicit deny-all RLS and all grants revoked from `public`/`anon`/`authenticated`. |
| `consume_rate_limit` / `cleanup_rate_limit_events` | `private` + `public` wrapper | Advisory-locked sliding-window counter + 2-day retention cleanup. `public.consume_rate_limit` (`SECURITY INVOKER`) exposes RPC exclusively to `service_role`. |

> **Migration history note:** Remote database history records `20260620085016` and `20261116180236` for migrations stored in-repo as `20260620090000_add_admin_invite_demo_access.sql` and `20261116180000_add_rate_limit_counters.sql` (plus `20261116181000_fix_consume_rate_limit_greatest.sql`, which replaced `pg_catalog.greatest()` with `CASE` for empty `search_path`). Check remote migration timestamps before applying against an existing DB.

---

## API invariants and change checklist

### Invariants
- **NEVER** import `ocr_engine_cli` or `ocr_engine_mcp` inside `ocr_engine_api`.
- **NEVER** store raw `ocr_live_` keys in Postgres, logs, or responses; store SHA-256 hashes only and return raw secrets once on creation.
- **NEVER** weaken `api_key_auth` to bypass Bearer auth on `/v1/runs/*` (use `OCR_ENGINE_API_KEY` locally).
- **NEVER** return raw `HTTPException(status_code=..., detail="string")`; always use `error_response` / `engine_error_response`.
- **NEVER** promote `accounts.role` from `raw_user_meta_data`.

### API change checklist
- [ ] Auth boundary matches endpoint surface (`/v1/runs/*` middleware, `/v1/me/*` `require_supabase_user`, `/v1/admin/*` `require_admin_account`).
- [ ] Error shapes use `error_response` / `engine_error_response` and outputs pass through `sanitize_for_public_response`.
- [ ] New env vars added to `ApiSettings` + `validate_api_settings()` in `settings.py` and `.env.example`.
- [ ] Key deletion/revocation calls `invalidate_api_key_cache(...)`.
- [ ] Relevant tests pass: `uv run pytest tests/test_api.py tests/test_auth.py tests/test_admin_api.py tests/test_run_repository.py tests/test_hardening.py tests/test_phase3_api_mcp_hardening.py`.

---

[← Previous: Core Pipeline](core-pipeline.md) | [Next: Adapters & Web →](adapters-and-web.md)
