# api — AGENTS.md

> Local guardrails for `packages/api/` (`ocr_engine_api`).
> Read [`/AGENTS.md`](../../AGENTS.md) and [`/docs/codebase/api-and-auth.md`](../../docs/codebase/api-and-auth.md) before modifying code here.

## Context & Stack

FastAPI HTTP adapter (`>= 3.12`, `fastapi >= 0.115`, `uvicorn >= 0.30`, `python-multipart`, `supabase >= 2.0`, `pyjwt >= 2.0`, Pydantic). Exposes `/health`, `/v1/runs/*`, and (when `settings.has_supabase`) `/v1/me/*` and `/v1/admin/*`, backed by `OcrToolbox`, filesystem `RunRepository`, `RunRateLimiter`, and Supabase Postgres.

## Local Verification

```bash
uv run pytest tests/test_api.py tests/test_auth.py tests/test_admin_api.py tests/test_run_repository.py tests/test_hardening.py tests/test_phase3_api_mcp_hardening.py
```

## Non-Negotiable Rules (`NEVER`)

- **NEVER** import `ocr_engine_mcp` or `ocr_engine_cli` inside `ocr_engine_api`.
- **NEVER** raise raw `HTTPException(status_code=..., detail="...")`; always use `errors.error_response` or `errors.engine_error_response`.
- **NEVER** return unsanitized filesystem paths in production (`responses.sanitize_for_public_response`) or raw provider errors.
- **NEVER** store or log raw `ocr_live_` keys (SHA-256 hash only; raw secret returned once on creation).
- **NEVER** weaken `api_key_auth` middleware to skip Bearer checks on `/v1/runs/*` (use `OCR_ENGINE_API_KEY` locally).
- **NEVER** bypass `invalidate_api_key_cache(...)` when deleting or revoking API keys.

## Pointers

- Architecture, endpoints, auth & Supabase schema: [`docs/codebase/api-and-auth.md`](../../docs/codebase/api-and-auth.md)
- Error envelope skill: [`skills/api-error-envelope/SKILL.md`](../../skills/api-error-envelope/SKILL.md)
- API key & layered auth skill: [`skills/api-key-auth/SKILL.md`](../../skills/api-key-auth/SKILL.md)
