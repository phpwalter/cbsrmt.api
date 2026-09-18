from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Fixed-window request accounting that emits the contract's rate-limit headers.

    This intentionally does not reject requests with 429 because the current OpenAPI
    contract does not define a 429 response. Enforcement can be added when the contract
    adds that response.
    """

    def __init__(self, app, limit: int, window_seconds: int) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self._state: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        client = request.client.host if request.client else "unknown"
        now = int(time.time())
        window = now // self.window_seconds
        key = f"{client}:{window}"

        with self._lock:
            count, _ = self._state[key]
            count += 1
            self._state[key] = (count, window)

        response = await call_next(request)
        remaining = max(self.limit - count, 0)
        reset_epoch = (window + 1) * self.window_seconds
        reset_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(reset_epoch))

        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = reset_iso
        return response
