---
name: api-error-envelope
description: >
  How to emit structured errors from any FastAPI route, dependency, or middleware in
  ocr_engine_api. Trigger: Adding or editing HTTP routes, translating OcrEngineError or
  RunRepositoryError, or introducing new API error codes.
version: 2.0.0
---

# API Error Envelope

Standard pattern for emitting deterministic, sanitized errors across `packages/api`.

## When to Use

- Adding or editing a FastAPI route, dependency, or middleware handler
- Translating `OcrEngineError` (`ocr_engine_core`) or `RunRepositoryError` into HTTP responses
- Introducing a new API error code

---

## Envelope Shape

All error payloads carry `success: false` and a structured `error` object:

```json
{
  "success": false,
  "error": {
    "code": "EMPTY_UPLOAD",
    "message": "Uploaded file is empty",
    "retryable": false,
    "details": { "window": "minute", "limit": 3, "retry_after_seconds": 42 }
  }
}
```

- **Middleware / `JSONResponse` handlers** (`auth.py`, `auth_api_key.py`, `rate_limit.py`, `unexpected_error_handler` in `main.py`): emit the JSON object directly at top level.
- **Route helpers** (`error_response`, `engine_error_response` in `errors.py`): raise FastAPI `HTTPException(status_code=..., detail={"success": False, "error": ...})`.

Fields:
- `code`: stable `UPPER_SNAKE_CASE` identifier (never localized).
- `message`: human-readable message free of secrets, tokens, or stack traces.
- `retryable`: `true` for transient conditions (`429`, `502`, `503`, stalled runs, retryable provider errors); `false` for client/validation errors.
- `details`: optional structured metadata (omitted when empty).

---

## Critical Rules

1. **NEVER** raise raw `HTTPException(status_code=..., detail="plain string")` in routes or dependencies; always use `error_response(...)` or `engine_error_response(...)`.
2. **NEVER** leak raw provider response bodies, stack traces, bearer tokens, or internal filesystem paths in `message` or `details`.
3. **NEVER** omit `retryable` — clients (`OcrApiClient` in MCP and `packages/web`) depend on the contract.
4. **ALWAYS** map `OcrEngineError` via `engine_error_response(exc)` (HTTP `422` using `exc.to_dict()`) or record `exc.to_dict()` inside `RunExecutor` failure status (`_run_repository_call` maps unexpected `OcrEngineError` during repository reads to HTTP `500`).

---

## Cookbook: Emitting Errors

### Explicit route or dependency error
```python
from ocr_engine_api.errors import error_response

raise error_response(
    400,
    "EMPTY_UPLOAD",
    "Uploaded file is empty",
    retryable=False,
)
```

### Mapping `RunRepositoryError` or `OcrEngineError`
```python
from ocr_engine_api.errors import engine_error_response, error_response
from ocr_engine_api.services.run_repository import RunRepositoryError
from ocr_engine_core.exceptions import OcrEngineError

try:
    ...
except RunRepositoryError as exc:
    raise error_response(exc.status_code, exc.code, exc.message) from exc
except OcrEngineError as exc:
    raise engine_error_response(exc) from exc
```

### Middleware `JSONResponse` error
- **When:** Rejecting requests inside `api_key_auth` or custom ASGI/HTTP middleware before routing (where raising `HTTPException` would bypass route serialization).
- **Then:** Return `JSONResponse(status_code=..., content={"success": False, "error": {"code": ..., "message": ..., "retryable": ...}})` (see `auth.unauthorized_response`, `rate_limit.rate_limited_response`).

---

## Verification Checklist

- [ ] No raw `HTTPException` calls in modified routes or dependencies.
- [ ] Error code is `UPPER_SNAKE_CASE` and `retryable` accurately reflects transience.
- [ ] No secrets, tokens, or stack traces appear in `message` or `details`.
- [ ] Envelope assertions pass: `uv run pytest tests/test_api.py tests/test_hardening.py`.
