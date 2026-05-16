"""
Rate limiting middleware — simple in-memory token-bucket per IP and per wallet.
"""

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token-bucket rate limiter per client IP.
    Configurable via constructor:
    - rate: tokens added per second
    - capacity: max tokens (burst)
    - window: seconds to track
    """

    def __init__(self, app, rate: float = 1.0, capacity: int = 10, window: int = 60):
        super().__init__(app)
        self.rate = rate
        self.capacity = capacity
        self.window = window
        self._buckets: dict = defaultdict(lambda: {"tokens": capacity, "last": time.time()})

    def _allow(self, key: str) -> bool:
        now = time.time()
        bucket = self._buckets[key]
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(self.capacity, bucket["tokens"] + elapsed * self.rate)
        bucket["last"] = now

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False

    async def dispatch(self, request: Request, call_next):
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        key = client_ip.split(",")[0].strip()

        if not self._allow(key):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Slow down.",
                    "retry_after": int(1 / self.rate) + 1,
                    "devnet_warning": "EXPERIMENTAL DEVNET ONLY",
                },
            )

        return await call_next(request)
