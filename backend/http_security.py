"""Rate limiting and security headers for the API gateway."""

from __future__ import annotations

import os
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def cors_origins() -> list[str]:
    raw = os.environ.get(
        "QBRIDGE_CORS_ORIGINS",
        "http://127.0.0.1:3000,http://localhost:3000,https://qbridge-os.vercel.app",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-XSS-Protection"] = "0"
        if request.url.scheme == "https" or os.environ.get("QBRIDGE_HSTS", "").strip() == "1":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory per-IP rate limit (use Cloudflare/WAF for real DDoS protection)."""

    def __init__(
        self,
        app,
        *,
        default_rpm: int = 120,
        auth_rpm: int = 15,
        compute_rpm: int = 30,
    ) -> None:
        super().__init__(app)
        self.default_rpm = default_rpm
        self.auth_rpm = auth_rpm
        self.compute_rpm = compute_rpm
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
        return request.client.host if request.client else "unknown"

    def _limit_for(self, path: str) -> int:
        if path.startswith("/api/v1/auth"):
            return self.auth_rpm
        if path.startswith("/api/v1/compute"):
            return self.compute_rpm
        return self.default_rpm

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        key = self._client_key(request)
        now = time.time()
        bucket = self._hits[key]
        bucket[:] = [t for t in bucket if now - t < 60.0]
        limit = self._limit_for(request.url.path)
        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait a minute and try again."},
                headers={"Retry-After": "60"},
            )
        bucket.append(now)
        return await call_next(request)
