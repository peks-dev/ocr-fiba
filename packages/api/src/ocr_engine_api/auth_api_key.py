from __future__ import annotations

import threading
import time

from fastapi import Request
from fastapi.responses import JSONResponse

from ocr_engine_api.api_keys import KEY_PREFIX, find_active_key_by_hash, hash_api_key, update_last_used_at

# In-memory cache: key_hash -> (account_id, status, cached_at)
_cache: dict[str, tuple[str, str, float]] = {}
_cache_lock = threading.Lock()

TTL_SECONDS = 60
MAX_CACHE_ENTRIES = 1024


def is_api_key_request(request: Request) -> bool:
    """Return True when the Bearer token is a per-client ``ocr_live_`` API key.

    The shared static token may start with ``ocr_pub_``; those must fall through
    to the OCR_ENGINE_API_KEY check rather than the Supabase api_keys lookup.
    """
    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    return scheme.lower() == "bearer" and token.startswith(KEY_PREFIX)


def _cache_get(key_hash: str) -> tuple[str, str] | None:
    """Return (account_id, status) from cache if present and not expired."""
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get(key_hash)
        if entry is None:
            return None
        account_id, status, cached_at = entry
        if now - cached_at > TTL_SECONDS:
            del _cache[key_hash]
            return None
        return account_id, status


def _cache_set(key_hash: str, account_id: str, status: str) -> None:
    """Store a validated key in the bounded cache."""
    now = time.monotonic()
    with _cache_lock:
        if len(_cache) >= MAX_CACHE_ENTRIES and key_hash not in _cache:
            expired = [k for k, (_, _, ts) in _cache.items() if now - ts > TTL_SECONDS]
            for k in expired:
                del _cache[k]
            if len(_cache) >= MAX_CACHE_ENTRIES:
                oldest_key = min(_cache, key=lambda k: _cache[k][2])
                del _cache[oldest_key]
        _cache[key_hash] = (account_id, status, now)


def invalidate_api_key_cache(*, key_hash: str | None = None, account_id: str | None = None) -> int:
    """Evict cached API keys by key_hash or account_id after revocation/deletion."""
    removed = 0
    with _cache_lock:
        if key_hash is not None and key_hash in _cache:
            del _cache[key_hash]
            removed += 1
        if account_id is not None:
            matching = [k for k, (acct, _, _) in _cache.items() if acct == account_id]
            for k in matching:
                del _cache[k]
                removed += 1
    return removed


def validate_api_key(request: Request) -> JSONResponse | None:
    """Validate an OCR API key from the request.

    Returns None on success (request should proceed).
    Returns a JSONResponse with 401 on failure.
    """
    auth_header = request.headers.get("authorization", "")
    _, _, token = auth_header.partition(" ")
    key_hash = hash_api_key(token)

    # Check cache first
    cached = _cache_get(key_hash)
    if cached is not None:
        account_id, status = cached
        if status != "active":
            return _unauthorized_response("API key has been revoked")
        request.state.account_id = account_id
        return None

    # Cache miss — query Supabase
    key_row = find_active_key_by_hash(key_hash)
    if key_row is None:
        return _unauthorized_response("Invalid or revoked API key")

    account_id = key_row["account_id"]
    status = key_row["status"]
    _cache_set(key_hash, account_id, status)

    if status != "active":
        return _unauthorized_response("API key has been revoked")

    # Fire-and-forget last_used_at update
    try:
        update_last_used_at(key_row["id"])
    except Exception:
        pass  # Non-critical; don't block the request

    request.state.account_id = account_id
    return None


def _unauthorized_response(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": message,
                "retryable": False,
            },
        },
    )
