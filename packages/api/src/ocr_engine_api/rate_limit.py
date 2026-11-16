from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import deque
from pathlib import Path

from fastapi.responses import JSONResponse


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


class RunRateLimiter:
    """Sliding-window limiter for run creation, keyed per token. A limit of 0 disables it.

    Counters live in memory and, when ``state_file`` is set, are persisted as JSON after each
    accepted run so the daily cap survives restarts / scale-to-zero (e.g. a file on the
    GCS-mounted runs dir on Cloud Run). Intended for a single writer process.
    """

    def __init__(
        self,
        per_minute: int,
        per_day: int,
        *,
        state_file: str | Path | None = None,
        clock=time.time,
    ) -> None:
        self.per_minute = per_minute
        self.per_day = per_day
        self.state_file = Path(state_file) if state_file else None
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._load()

    @property
    def enabled(self) -> bool:
        return self.per_minute > 0 or self.per_day > 0

    def check(self, key: str) -> tuple[bool, str | None, int]:
        """Record one attempt for ``key``. Returns (allowed, window, retry_after_seconds)."""
        if not self.enabled:
            return True, None, 0
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - 86400:
                hits.popleft()
            if self.per_minute > 0:
                recent = [t for t in hits if t > now - 60]
                if len(recent) >= self.per_minute:
                    return False, "minute", max(1, int(recent[0] + 60 - now) + 1)
            if self.per_day > 0 and len(hits) >= self.per_day:
                return False, "day", max(1, int(hits[0] + 86400 - now) + 1)
            hits.append(now)
            self._save(now)
            return True, None, 0

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
