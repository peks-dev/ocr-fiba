from __future__ import annotations

import secrets

from fastapi.responses import JSONResponse


AUTH_EXEMPT_PATHS = {"/health"}


def is_auth_exempt(path: str) -> bool:
    return path in AUTH_EXEMPT_PATHS


def is_authorized(auth_header: str, expected_key: str | None) -> bool:
    if not expected_key:
        return True
    scheme, _, token = auth_header.partition(" ")
    return scheme.lower() == "bearer" and secrets.compare_digest(token, expected_key)


def unauthorized_response() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Missing or invalid API key",
                "retryable": False,
            },
        },
    )
