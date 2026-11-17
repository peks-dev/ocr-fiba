from __future__ import annotations

import hashlib
import json
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

import jwt
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ocr_engine_api.auth import forbidden_response, unauthorized_response
from ocr_engine_api.errors import error_response
from ocr_engine_api.settings import get_api_settings

_JWT_CACHE_TTL_SECONDS = 30.0
_JWT_CACHE_MAX_ENTRIES = 1024
_jwt_cache: dict[str, tuple[dict, float]] = {}
_jwt_cache_lock = threading.Lock()


def verify_supabase_jwt(token: str) -> dict:
    """Verify a Supabase session JWT and return normalized user claims.

    Supabase projects can issue either legacy/shared-secret HS256 tokens or
    modern asymmetric tokens (ES256/RS256). HS256 tokens are verified locally
    with SUPABASE_JWT_SECRET. Asymmetric tokens are verified by Supabase Auth's
    /user endpoint so we do not need to manage JWKS in this MVP.
    """
    settings = get_api_settings()
    if not settings.has_supabase:
        raise error_response(500, "SUPABASE_NOT_CONFIGURED", "Supabase is not configured")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise error_response(401, "UNAUTHORIZED", f"Invalid token: {exc}") from exc

    if header.get("alg") == "HS256":
        return _verify_hs256_token(token, settings.supabase_jwt_secret)

    return _verify_with_supabase_auth_server(
        token,
        supabase_url=settings.supabase_url,
        api_key=settings.supabase_publishable_key or settings.supabase_service_key,
    )


def _verify_hs256_token(token: str, jwt_secret: str) -> dict:
    try:
        return jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub"], "verify_exp": True},
        )
    except jwt.ExpiredSignatureError as exc:
        raise error_response(401, "TOKEN_EXPIRED", "Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise error_response(401, "UNAUTHORIZED", f"Invalid token: {exc}") from exc


def _jwt_cache_key(supabase_url: str, token: str) -> str:
    return hashlib.sha256(f"{supabase_url.rstrip('/')}:{token}".encode("utf-8")).hexdigest()


def _jwt_cache_get(cache_key: str) -> dict | None:
    now = time.monotonic()
    with _jwt_cache_lock:
        entry = _jwt_cache.get(cache_key)
        if entry is None:
            return None
        claims, expires_at = entry
        if now >= expires_at:
            del _jwt_cache[cache_key]
            return None
        return dict(claims)


def _jwt_cache_set(cache_key: str, claims: dict, ttl_seconds: float) -> None:
    if ttl_seconds <= 0:
        return
    now = time.monotonic()
    with _jwt_cache_lock:
        if len(_jwt_cache) >= _JWT_CACHE_MAX_ENTRIES:
            expired = [k for k, (_, exp) in _jwt_cache.items() if now >= exp]
            for k in expired:
                del _jwt_cache[k]
            if len(_jwt_cache) >= _JWT_CACHE_MAX_ENTRIES:
                oldest_key = min(_jwt_cache, key=lambda k: _jwt_cache[k][1])
                del _jwt_cache[oldest_key]
        _jwt_cache[cache_key] = (dict(claims), now + ttl_seconds)


def _unverified_exp_ttl(token: str) -> float:
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
        exp = claims.get("exp")
        if isinstance(exp, (int, float)):
            return min(_JWT_CACHE_TTL_SECONDS, max(0.0, float(exp) - time.time()))
    except Exception:
        pass
    return _JWT_CACHE_TTL_SECONDS


def _verify_with_supabase_auth_server(token: str, supabase_url: str, api_key: str) -> dict:
    if not api_key:
        raise error_response(
            500,
            "SUPABASE_NOT_CONFIGURED",
            "Supabase publishable key is required for asymmetric JWT verification",
        )

    cache_key = _jwt_cache_key(supabase_url, token)
    cached = _jwt_cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{supabase_url.rstrip('/')}/auth/v1/user"
    request = UrlRequest(
        url,
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {token}",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code in {401, 403}:
            detail = "Invalid Supabase session token"
            if "alg" in body.lower():
                detail = "Invalid Supabase API key for auth verification. Set SUPABASE_PUBLISHABLE_KEY to the project publishable/anon key, not the secret/service key."
            raise error_response(401, "UNAUTHORIZED", detail) from exc
        raise error_response(
            502,
            "AUTH_BACKEND_UNAVAILABLE",
            f"Supabase Auth verification failed: HTTP {exc.code}",
            retryable=True,
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise error_response(
            502,
            "AUTH_BACKEND_UNAVAILABLE",
            "Supabase Auth verification is unavailable",
            retryable=True,
        ) from exc
    except json.JSONDecodeError as exc:
        raise error_response(
            502,
            "AUTH_BACKEND_UNAVAILABLE",
            "Supabase Auth returned an invalid response",
            retryable=True,
        ) from exc

    user_id = payload.get("id")
    if not user_id:
        raise error_response(401, "UNAUTHORIZED", "Invalid Supabase user payload")

    # Normalize to the claims shape expected by /v1/me routes.
    normalized = {
        "sub": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "authenticated"),
        "user": payload,
    }
    _jwt_cache_set(cache_key, normalized, _unverified_exp_ttl(token))
    return normalized


def extract_bearer_token(request: Request) -> str | None:
    """Extract the Bearer token from the Authorization header."""
    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token
    return None


def is_jwt_request(request: Request) -> bool:
    """Return True when the Bearer token looks like a JWT (three dot-separated parts)."""
    token = extract_bearer_token(request)
    if not token:
        return False
    parts = token.split(".")
    return len(parts) == 3 and all(parts)


def validate_supabase_session(request: Request) -> JSONResponse | None:
    """Validate a Supabase session JWT and attach the account to the request.

    Returns None on success. Returns a JSONResponse on failure.
    """
    token = extract_bearer_token(request)
    if not token:
        return unauthorized_response()
    try:
        payload = verify_supabase_jwt(token)
    except HTTPException:
        return unauthorized_response()

    user_id = payload.get("sub")
    if not user_id:
        return unauthorized_response()

    from ocr_engine_api.api_keys import get_account_by_supabase_user_id

    try:
        account = get_account_by_supabase_user_id(str(user_id))
    except Exception:
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "error": {
                    "code": "AUTH_BACKEND_UNAVAILABLE",
                    "message": "Account lookup failed",
                    "retryable": True,
                },
            },
        )
    if not account:
        return forbidden_response("Account not found. Signup may not have completed.")
    if account.get("status") != "active":
        return forbidden_response("Account is not active")

    request.state.account_id = account["id"]
    request.state.account_role = account.get("role")
    return None


def require_supabase_user(request: Request) -> dict:
    """FastAPI dependency that verifies a Supabase JWT and returns the payload.

    Use on /v1/me/* endpoints that require an authenticated Supabase user.
    """
    token = extract_bearer_token(request)
    if not token:
        raise error_response(401, "UNAUTHORIZED", "Missing Authorization header")
    return verify_supabase_jwt(token)
