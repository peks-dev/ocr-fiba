from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from core.exceptions import OcrEngineError


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    if details:
        error["details"] = details
    return HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "error": error,
        },
    )


def engine_error_response(exc: OcrEngineError) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "success": False,
            "error": exc.to_dict(),
        },
    )
