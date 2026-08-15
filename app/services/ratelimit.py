"""Small in-memory sliding-window rate limiter.

Used for the public collaboration endpoints (invitation accept/decline/landing)
and the presence heartbeat until the broader per-user AI/import rate limiting
land (#28/#81/#106). Limits are per-key (typically per client IP) over a
configurable window. The limiter is process-local, which is acceptable for the
default single-worker deployments and CI; multi-worker deployments should
back it with a shared store (out of scope here).
"""

from __future__ import annotations

import threading
import time

from flask import current_app

_ENTRIES: dict[str, list[float]] = {}
_LOCK = threading.Lock()


def _prune(key: str, window: int) -> None:
    cutoff = time.monotonic() - window
    timestamps = _ENTRIES.get(key)
    if not timestamps:
        return
    kept = [ts for ts in timestamps if ts > cutoff]
    if kept:
        _ENTRIES[key] = kept
    else:
        _ENTRIES.pop(key, None)


def hit(key: str, *, max_hits: int | None = None, window: int | None = None) -> bool:
    """Record a hit for ``key`` and return ``True`` when still within the limit.

    When the limit is exceeded the hit is still recorded, so repeated abuse
    keeps the key hot.
    """
    if max_hits is None:
        max_hits = current_app.config.get("RATE_LIMIT_MAX", 30)
    if window is None:
        window = current_app.config.get("RATE_LIMIT_WINDOW_SECONDS", 300)

    now = time.monotonic()
    with _LOCK:
        _prune(key, window)
        timestamps = _ENTRIES.setdefault(key, [])
        allowed = len(timestamps) < max_hits
        timestamps.append(now)
        return allowed


def client_key(extra: str = "") -> str:
    """Build a per-client limiter key from the request's remote address."""
    from flask import request

    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0]
    return f"{extra}:{ip}"


def reset() -> None:
    """Clear all limiter state (used by tests)."""
    with _LOCK:
        _ENTRIES.clear()
