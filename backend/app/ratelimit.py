"""In-memory sliding-window rate limiter (per-IP, per-minute).
Prototype-grade: use Redis-backed limiting (e.g. slowapi + Redis) in production.
"""
import time
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, per_minute: int = 120, login_per_minute: int = 20):
        super().__init__(app)
        self.per_minute = per_minute
        self.login_per_minute = login_per_minute
        self.hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path == "/api/health":
            return await call_next(request)
        is_login = (path == "/api/auth/login")
        limit = self.login_per_minute if is_login else self.per_minute
        if limit <= 0:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        key = f"{ip}:{'login' if is_login else 'api'}"
        now = time.time()
        dq = self.hits[key]
        while dq and now - dq[0] > 60:
            dq.popleft()
        if len(dq) >= limit:
            return JSONResponse({"detail": "Rate limit exceeded. Try again in a minute."}, status_code=429)
        dq.append(now)
        return await call_next(request)
