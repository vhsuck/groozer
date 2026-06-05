

import time
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"


        limit = self.max_requests
        if "/api/auth/" in request.url.path:
            limit = 10

        now = time.time()
        window_start = now - self.window_seconds
        queue = self._requests[client_ip]


        while queue and queue[0] < window_start:
            queue.popleft()

        if len(queue) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Слишком много запросов. Пожалуйста, подождите немного.",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        queue.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(limit - len(queue))
        return response
