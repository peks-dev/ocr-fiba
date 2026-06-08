---
name: api-error-envelope
description: How to return a structured error from any FastAPI route in the FIBA OCR engine. Use in any route, dependency, or middleware that needs to fail with a stable, machine-readable error shape — including translating OcrEngineError from the core into HTTP 422.
version: 1.0.0
---

# API Error Envelope

Standard pattern for emitting errors from the FIBA OCR API. Every error returned to a client (browser, MCP tool, CLI smoke test) MUST go through this envelope. Tests in `tests/test_api.py` assert this shape.

## When to use

- Any route, dependency, or middleware that needs to return an error.
- Translating an `OcrEngineError` (raised by `ocr_engine_core`) into an HTTP response.
- Adding a new error code to the API surface.

## Envelope shape

```json
{
  "error": {
    "code": "EMPTY_UPLOAD",
    "message": "Image is empty",
    "retryable": false,
    "details": { "max_bytes": 20971520 }
  }
}
```

- `code`: stable, machine-readable identifier. Uppercase snake_case. Reuse existing codes where possible.
- `message`: human-readable, never includes secrets or absolute paths.
- `retryable`: hint for the caller. Set `true` for transient errors (timeouts, 5xx, rate limits); `false` for client mistakes.
- `details`: optional structured context. Never include absolute file paths, internal run ids, or provider responses.

## How to emit

Never use `HTTPException(status_code=..., detail=...)` directly. Use the helpers in `ocr_engine_api.errors`:

```python
from ocr_engine_api.errors import error_response, engine_error_response

# 1. Explicit error from a route or dependency
raise error_response(
    status_code=400,
    code="EMPTY_UPLOAD",
    message="Image is empty",
    retryable=False,
    details={"max_bytes": settings.max_upload_mb * 1024 * 1024},
)

# 2. Translating an OcrEngineError from the core engine
try:
    pipeline.process(...)
except OcrEngineError as exc:
    raise engine_error_response(exc)   # → HTTP 422 with exc.to_dict()
```

`engine_error_response` is the **only** allowed bridge from core-engine errors to HTTP responses. Do not call `error_response` with a hand-written code to mimic a core error — always go through `engine_error_response`.

## Adding a new error code

1. Add a constant in the route file (or in `errors.py` if it spans multiple routes).
2. Use a stable `UPPER_SNAKE_CASE` identifier. Never localize the code.
3. Set `retryable` correctly — clients use it to decide whether to retry.
4. Add a test in `tests/test_api.py` (or the relevant test module) that asserts the envelope shape and the HTTP status.

## Constraints (do not violate)

- Do not return a raw `HTTPException` from any route.
- Do not include absolute file paths, raw provider error bodies, or stack traces in `details`.
- Do not use the same `code` for two semantically different conditions.
- Do not omit `retryable` — it's part of the contract.
- Do not return HTML or plaintext for errors; always the JSON envelope.

## References

- `errors.py` — `error_response`, `engine_error_response`
- `routes/runs.py` — examples of explicit errors (e.g. `EMPTY_UPLOAD`)
- `routes/me.py` — examples of auth errors
- `tests/test_api.py` — envelope shape assertions
- Core engine error hierarchy — `packages/core-engine/src/ocr_engine_core/exceptions.py`
