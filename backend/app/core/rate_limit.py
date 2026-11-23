"""Simple sliding-window rate limiter.

In-memory and per-process. This is adequate for a single API container.
When running several API replicas, put the same limits on the reverse proxy
(see deployment/nginx/nginx.conf, which also rate-limits /api/auth/*).
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def hit(self, key: str, rule: str) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        limit_s, window_s = rule.split("/")
        limit, window = int(limit_s), float(window_s)
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= limit:
                retry = int(window - (now - q[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please wait and try again.",
                    headers={"Retry-After": str(retry)},
                )
            q.append(now)


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    # X-Forwarded-For is set by our own Nginx; uvicorn runs with --proxy-headers
    # and trusted forwarded IPs so request.client.host is already the real client.
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request, bucket: str, rule: str, identifier: str = "") -> None:
    limiter.hit(f"{bucket}:{client_ip(request)}:{identifier.lower()}", rule)
    if identifier:  # also limit per identifier across IPs
        limiter.hit(f"{bucket}:id:{identifier.lower()}", rule)
