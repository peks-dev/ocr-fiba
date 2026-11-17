from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# Endpoints that start an OCR run (and therefore spend provider credit).
RATE_LIMITED_PATHS = {"/v1/runs", "/v1/runs/upload"}


def is_run_creation(method: str, path: str) -> bool:
    return method.upper() == "POST" and path.rstrip("/") in RATE_LIMITED_PATHS


def client_key(auth_header: str, client_host: str | None) -> str:
    """Bucket key per bearer token (hashed, never stored in clear); falls back to client IP."""
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() == "bearer" and token:
        return "tok:" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return "ip:" + (client_host or "unknown")


def request_rate_limit_key(account_id: str | None, auth_header: str, client_host: str | None) -> str:
    """Prefer a per-account bucket so a session JWT and that account's ocr_live_ keys share a quota."""
    if account_id:
        return "acct:" + str(account_id)
    return client_key(auth_header, client_host)


class RateLimitBackendError(Exception):
    """The shared rate-limit store could not be reached or returned an invalid result.

    Run-creation endpoints must fail closed (HTTP 503) when this is raised so a
    backend outage cannot bypass the 3/min and 50/day caps.
    """


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    window: str | None
    retry_after: int
    remaining_minute: int | None = None
    remaining_day: int | None = None


class RateLimitStore(Protocol):
    def consume(self, key: str, per_minute: int, per_day: int) -> RateLimitDecision:
        """Record one attempt for ``key``. Raise RateLimitBackendError on store failure."""


class MemoryRateLimitStore:
    """In-memory sliding-window store, optionally persisted to a JSON file.

    Used as the local/dev fallback when Supabase is not configured. Intended for
    a single writer process: the file is overwritten with this process's map and
    is not safe across multiple Cloud Run instances.
    """

    def __init__(self, *, state_file: str | Path | None = None, clock=time.time) -> None:
        self.state_file = Path(state_file) if state_file else None
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._load()

    def consume(self, key: str, per_minute: int, per_day: int) -> RateLimitDecision:
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - 86400:
                hits.popleft()
            if per_minute > 0:
                recent = [t for t in hits if t > now - 60]
                if len(recent) >= per_minute:
                    return RateLimitDecision(
                        False,
                        "minute",
                        max(1, int(recent[0] + 60 - now) + 1),
                        remaining_minute=0,
                        remaining_day=max(0, per_day - len(hits)) if per_day > 0 else None,
                    )
            if per_day > 0 and len(hits) >= per_day:
                return RateLimitDecision(
                    False,
                    "day",
                    max(1, int(hits[0] + 86400 - now) + 1),
                    remaining_minute=max(0, per_minute - len([t for t in hits if t > now - 60])) if per_minute > 0 else None,
                    remaining_day=0,
                )
            hits.append(now)
            self._save(now)
            return RateLimitDecision(
                True,
                None,
                0,
                remaining_minute=max(0, per_minute - len([t for t in hits if t > now - 60])) if per_minute > 0 else None,
                remaining_day=max(0, per_day - len(hits)) if per_day > 0 else None,
            )

    def _load(self) -> None:
        if not self.state_file or not self.state_file.is_file():
            return
        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
            cutoff = self._clock() - 86400
            for key, stamps in payload.get("hits", {}).items():
                kept = sorted(float(t) for t in stamps if float(t) > cutoff)
                if kept:
                    self._hits[str(key)] = deque(kept)
        except (OSError, ValueError, TypeError, AttributeError):
            self._hits = {}

    def _save(self, now: float) -> None:
        if not self.state_file:
            return
        cutoff = now - 86400
        payload = {"hits": {k: [t for t in v if t > cutoff] for k, v in self._hits.items() if v}}
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass  # quota persistence is best-effort; in-memory limits still apply


class SupabaseRateLimitStore:
    """Shared store backed by the ``consume_rate_limit`` Postgres RPC.

    All Cloud Run instances go through the same advisory-locked function, so
    3/min and 50/day caps hold across scale-out. Requires SUPABASE_URL and
    SUPABASE_SERVICE_KEY. Failures raise RateLimitBackendError (fail closed).
    """

    def consume(self, key: str, per_minute: int, per_day: int) -> RateLimitDecision:
        try:
            from ocr_engine_api.supabase_client import get_supabase_client

            response = get_supabase_client().rpc(
                "consume_rate_limit",
                {"p_key": key, "p_per_minute": per_minute, "p_per_day": per_day},
            ).execute()
        except RateLimitBackendError:
            raise
        except Exception as exc:
            logger.warning("Supabase rate limit RPC failed; failing closed: %s", exc)
            raise RateLimitBackendError("rate limit store is unavailable") from exc
        return parse_consume_rate_limit_payload(response.data)


def parse_consume_rate_limit_payload(data: Any) -> RateLimitDecision:
    """Map a ``consume_rate_limit`` RPC payload to a decision, or fail closed."""
    row: Any = data
    if isinstance(data, list):
        if not data:
            raise RateLimitBackendError("rate limit store returned no rows")
        row = data[0]
    if not isinstance(row, dict) or "allowed" not in row:
        raise RateLimitBackendError("rate limit store returned an invalid payload")
    try:
        retry_after = int(row.get("retry_after_seconds") or 0)
        remaining_minute = row.get("remaining_minute")
        remaining_day = row.get("remaining_day")
        return RateLimitDecision(
            allowed=bool(row["allowed"]),
            window=row.get("limit_window") or None,
            retry_after=retry_after,
            remaining_minute=int(remaining_minute) if remaining_minute is not None else None,
            remaining_day=int(remaining_day) if remaining_day is not None else None,
        )
    except (TypeError, ValueError) as exc:
        raise RateLimitBackendError("rate limit store returned an invalid payload") from exc


def create_rate_limit_store(settings: Any) -> RateLimitStore:
    """Use the shared Supabase RPC when the service-role client is configured."""
    if getattr(settings, "has_supabase_service", False):
        return SupabaseRateLimitStore()
    return MemoryRateLimitStore(state_file=settings.rate_limit_state_file)


class RunRateLimiter:
    """Sliding-window limiter for run creation, keyed per token. A limit of 0 disables it.

    When a ``store`` is provided (or constructed via :func:`create_rate_limit_store`),
    counters live in that store. The default is an in-memory map optionally persisted
    as JSON so the daily cap survives local restarts. Production uses the Supabase
    RPC so quotas are exact across multiple Cloud Run instances.
    """

    def __init__(
        self,
        per_minute: int,
        per_day: int,
        *,
        state_file: str | Path | None = None,
        clock=time.time,
        store: RateLimitStore | None = None,
    ) -> None:
        self.per_minute = per_minute
        self.per_day = per_day
        self.state_file = Path(state_file) if state_file else None
        self._clock = clock
        self._store = store if store is not None else MemoryRateLimitStore(state_file=state_file, clock=clock)

    @property
    def enabled(self) -> bool:
        return self.per_minute > 0 or self.per_day > 0

    def check(self, key: str) -> tuple[bool, str | None, int]:
        """Record one attempt for ``key``. Returns (allowed, window, retry_after_seconds).

        May raise :class:`RateLimitBackendError` when the shared store is unavailable.
        """
        if not self.enabled:
            return True, None, 0
        decision = self._store.consume(key, self.per_minute, self.per_day)
        return decision.allowed, decision.window, decision.retry_after


def rate_limited_response(window: str, retry_after: int, limit: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after)},
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMITED",
                "message": f"Run limit reached ({limit} per {window}). Retry in {retry_after}s.",
                "retryable": True,
                "details": {"window": window, "limit": limit, "retry_after_seconds": retry_after},
            },
        },
    )


def rate_limit_unavailable_response() -> JSONResponse:
    """Fail closed when the shared rate-limit store cannot be reached."""
    return JSONResponse(
        status_code=503,
        headers={"Retry-After": "5"},
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMIT_UNAVAILABLE",
                "message": "Rate limiter is temporarily unavailable. Retry in a few seconds.",
                "retryable": True,
            },
        },
    )
