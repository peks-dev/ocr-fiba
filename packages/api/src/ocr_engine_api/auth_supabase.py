from __future__ import annotations

import jwt
from fastapi import HTTPException, Request

from ocr_engine_api.settings import get_api_settings


def verify_supabase_jwt(token: str) -> dict:
    """Verify a Supabase session JWT and return its payload.

    Validates signature using the Supabase JWT secret, expiration, and
    standard claims. Raises HTTPException 401 on any failure.
    """
    settings = get_api_settings()
    if not settings.has_supabase:
        raise HTTPException(status_code=500, detail="Supabase is not configured")

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub"], "verify_exp": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

    return payload


def extract_bearer_token(request: Request) -> str | None:
    """Extract the Bearer token from the Authorization header."""
    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token
    return None


def require_supabase_user(request: Request) -> dict:
    """FastAPI dependency that verifies a Supabase JWT and returns the payload.

    Use on /v1/me/* endpoints that require an authenticated Supabase user.
    """
    token = extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    return verify_supabase_jwt(token)
