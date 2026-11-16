from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

import jwt
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ocr_engine_api.auth import forbidden_response, unauthorized_response
from ocr_engine_api.settings import get_api_settings


def verify_supabase_jwt(token: str) -> dict:
    """Verify a Supabase session JWT and return normalized user claims.

    Supabase projects can issue either legacy/shared-secret HS256 tokens or
    modern asymmetric tokens (ES256/RS256). HS256 tokens are verified locally
    with SUPABASE_JWT_SECRET. Asymmetric tokens are verified by Supabase Auth's
    /user endpoint so we do not need to manage JWKS in this MVP.
    """
    settings = get_api_settings()
    if not settings.has_supabase:
        raise HTTPException(status_code=500, detail="Supabase is not configured")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

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
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


def _verify_with_supabase_auth_server(token: str, supabase_url: str, api_key: str) -> dict:
    if not api_key:
        raise HTTPException(status_code=500, detail="Supabase publishable key is required for asymmetric JWT verification")

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
            raise HTTPException(status_code=401, detail=detail) from exc
        raise HTTPException(status_code=502, detail=f"Supabase Auth verification failed: HTTP {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="Supabase Auth verification is unavailable") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Supabase Auth returned an invalid response") from exc

    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid Supabase user payload")

    # Normalize to the claims shape expected by /v1/me routes.
    return {
        "sub": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "authenticated"),
        "user": payload,
    }


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
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    return verify_supabase_jwt(token)
