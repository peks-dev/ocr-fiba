from __future__ import annotations

import hashlib
import os
import secrets
import time
from collections.abc import Callable

import requests
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token

from ocr_engine_mcp.client import OcrApiClient, OcrApiError

OCR_LIVE_PREFIX = "ocr_live_"
DEFAULT_CACHE_TTL_SECONDS = 60
DEFAULT_PROBE_TIMEOUT_SECONDS = 10


def probe_ocr_api_key(
    token: str,
    *,
    base_url: str | None = None,
    timeout_seconds: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    session: requests.Session | None = None,
) -> bool:
    """Return True when the OCR API accepts ``token`` as a bearer key.

    Uses GET /v1/runs?limit=1, which requires auth but does not create a run.
    2xx and 429 (authenticated but rate-limited) count as valid. 401/403 and
    transport or server errors fail closed (the token is not accepted).
    """
    client = OcrApiClient(
        base_url,
        api_key=token,
        timeout_seconds=int(timeout_seconds),
        session=session or requests.Session(),
    )
    try:
        client.list_runs(limit=1)
        return True
    except OcrApiError as exc:
        if exc.status_code == 429:
            return True
        if exc.status_code in {401, 403}:
            return False
        raise


class McpTokenVerifier(TokenVerifier):
    """Accept the static MCP_AUTH_TOKEN or a validated ``ocr_live_`` API key.

    ``ocr_live_`` keys are checked against the OCR API and cached briefly so
    MCP does not accept arbitrary bearer tokens. Invalid keys are rejected
    here (HTTP 401) rather than being forwarded to tools.
    """

    def __init__(
        self,
        *,
        static_token: str | None = None,
        probe: Callable[[str], bool] | None = None,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        super().__init__()
        self.static_token = static_token or ""
        self._probe = probe or probe_ocr_api_key
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[bool, float]] = {}

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None
        if self._matches_static(token):
            return AccessToken(
                token=token,
                client_id="ocr-mcp-static",
                scopes=[],
                claims={"source": "static"},
            )
        if not token.startswith(OCR_LIVE_PREFIX):
            return None
        if not self._is_valid_live_key(token):
            return None
        return AccessToken(
            token=token,
            client_id="ocr-live-client",
            scopes=[],
            claims={"source": "ocr_live"},
        )

    def _matches_static(self, token: str) -> bool:
        expected = self.static_token
        if not expected or len(token) != len(expected):
            return False
        return secrets.compare_digest(token, expected)

    def _is_valid_live_key(self, token: str) -> bool:
        now = time.monotonic()
        cache_key = hashlib.sha256(token.encode("utf-8")).hexdigest()
        cached = self._cache.get(cache_key)
        if cached is not None:
            valid, cached_at = cached
            if now - cached_at <= self.cache_ttl_seconds:
                return valid
            del self._cache[cache_key]
        try:
            valid = bool(self._probe(token))
        except Exception:
            return False
        self._cache[cache_key] = (valid, now)
        return valid


def api_key_for_request() -> str | None:
    """API key to send upstream: the caller's ``ocr_live_`` token, else OCR_API_KEY.

    When the caller authenticated with the static MCP_AUTH_TOKEN, the MCP
    service still talks to the API with OCR_API_KEY (they are usually the
    same shared fallback secret).
    """
    access = get_access_token()
    token = access.token if access and access.token else None
    static = os.getenv("MCP_AUTH_TOKEN", "").strip()
    if token and token.startswith(OCR_LIVE_PREFIX):
        return token
    if token and static and len(token) == len(static) and secrets.compare_digest(token, static):
        return os.getenv("OCR_API_KEY")
    if token:
        return token
    return os.getenv("OCR_API_KEY")


def auth_from_env() -> McpTokenVerifier | None:
    """Build the HTTP token verifier from the environment.

    When MCP_AUTH_TOKEN is unset, HTTP auth stays off (loopback / stdio).
    When it is set, clients may present that static token or a validated
    ocr_live_ key. Production deployments should set MCP_AUTH_TOKEN.
    """
    static = os.getenv("MCP_AUTH_TOKEN", "").strip() or None
    if not static:
        return None
    return McpTokenVerifier(static_token=static)
