---
name: api-key-auth
description: >
  Bearer API key and layered Supabase JWT authentication in ocr_engine_api.
  Trigger: Adding or editing authenticated routes, modifying api_key_auth middleware,
  working on ocr_live_ key lifecycle (/v1/me, /v1/admin), or debugging 401/403/502 auth errors.
version: 2.0.0
---

# API Key & Layered Auth

Contract for authenticating HTTP callers across `/v1/runs/*`, `/v1/me/*`, and `/v1/admin/*`.

## When to Use

- Adding a route under `/v1/runs/*`, `/v1/me/*`, or `/v1/admin/*`
- Modifying `api_key_auth` middleware, `auth_api_key.py`, `auth_supabase.py`, or `api_keys.py`
- Debugging `401 UNAUTHORIZED`, `403 FORBIDDEN`, or `502 AUTH_BACKEND_UNAVAILABLE`
- Working on key generation, hashing, caching, or cache invalidation

---

## Key Format & Storage

```text
ocr_live_<64 hex chars>     # generated via secrets.token_hex(32)
```

- Visual prefix stored in DB: `ocr_live_<first 8 hex>...`
- Stored hash: SHA-256 hex digest via `api_keys.hash_api_key(raw_key)` in `public.api_keys`
- Raw secret returned **once** on creation (`POST /v1/me/api-keys/bootstrap`, `POST /v1/me/api-keys`, `POST /v1/admin/accounts/{id}/api-keys`)
- Shared static fallback tokens (including `ocr_pub_`-prefixed dev/shared tokens) do **not** start with `ocr_live_` and fall through to `OCR_ENGINE_API_KEY` (`auth.is_authorized`)

---

## Layered Middleware Flow (`main.py`)

1. `OPTIONS` and `AUTH_EXEMPT_PATHS` (`/health`) bypass auth.
2. `/v1/me` (`/v1/me/*`) and `/v1/admin` (`/v1/admin/*`) bypass the run middleware and enforce route dependencies:
   - `/v1/me/*` → `Depends(require_supabase_user)` + active row check in `public.accounts`
   - `/v1/admin/*` → `Depends(require_admin_account)` (requires active `public.accounts` row with `role == "admin"`)
3. Remaining routes (`/v1/runs/*`) authenticate in priority order:
   - `has_supabase` & `Bearer ocr_live_*` → `validate_api_key()` (SHA-256 lookup against 60s / 1024-entry cache, then `public.api_keys` where `status == "active"`, sets `request.state.account_id`)
   - `has_supabase` & 3-part JWT → `validate_supabase_session()` (local HS256 via `SUPABASE_JWT_SECRET` or `/auth/v1/user` verification with 30s / 1024-entry cache + active `public.accounts` lookup, sets `request.state.account_id`)
   - Else → constant-time `secrets.compare_digest` against `OCR_ENGINE_API_KEY`

---

## Critical Rules

1. **NEVER** store raw `ocr_live_` keys in `public.api_keys`, logs, config files, or browser `localStorage`.
2. **NEVER** skip Bearer checks on `/v1/runs/*`, even in development (use `OCR_ENGINE_API_KEY` fallback locally).
3. **NEVER** forget cache invalidation: any endpoint deleting or revoking a key MUST call `invalidate_api_key_cache(account_id=...)` (or `key_hash=...`).
4. **NEVER** grant `admin` role from user-editable `raw_user_meta_data` (only `raw_app_meta_data` in `handle_new_user()`).
5. **ALWAYS** offload blocking Supabase/JWT network calls from async middleware via `asyncio.to_thread`.

---

## Cookbook: Debugging & Extending Auth

### If adding a new endpoint
- **Under `/v1/runs/*`:** Middleware already authenticates `ocr_live_`, session JWT, or static bearer and sets `request.state.account_id` when Supabase-backed.
- **Under `/v1/me/*`:** Add `user: dict = Depends(require_supabase_user)` and resolve `_get_account_id(user)`.
- **Under `/v1/admin/*`:** Add `_admin: dict = Depends(require_admin_account)`.
- **Public health/probe:** Add explicitly to `AUTH_EXEMPT_PATHS` in `auth.py`.

### If debugging a `401` / `403` / `502`
- **401 on `ocr_live_`:** Confirm token starts with `ocr_live_`, row exists with `status='active'` in `public.api_keys`, and `has_supabase` is true (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `SUPABASE_JWT_SECRET` all set).
- **401 on asymmetric JWT (`ES256`/`RS256`):** Check `SUPABASE_PUBLISHABLE_KEY` (or `SUPABASE_ANON_KEY`) — `service_role` keys must not be misused where Supabase `/auth/v1/user` expects the publishable/anon key.
- **403 `Account is not active`:** Check `public.accounts.status` for that `supabase_user_id`.
- **502 `AUTH_BACKEND_UNAVAILABLE`:** `/auth/v1/user` or `public.accounts` lookup timed out or returned 5xx.

---

## Verification Checklist

- [ ] No raw keys logged, stored, or returned outside creation endpoints.
- [ ] Cache invalidation triggered on key deletion/revocation.
- [ ] Middleware prefix checks cover exact path and `/path/` boundaries without swallowing sibling paths.
- [ ] Auth tests pass: `uv run pytest tests/test_auth.py tests/test_admin_api.py tests/test_phase3_api_mcp_hardening.py`.
