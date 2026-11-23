"""Security middleware: CSRF double-submit check and security headers."""
import logging
import secrets
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.security import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER, REFRESH_COOKIE

logger = logging.getLogger("avtbvs.request")
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """Requests authenticated by cookie must echo the CSRF cookie in a header.

    Requests that carry an explicit Bearer token (API clients, Swagger) are not
    vulnerable to CSRF and are exempt. Login/register have no session yet.
    """

    EXEMPT_PATHS = {"/api/auth/login", "/api/auth/register", "/api/auth/token",
                    "/api/auth/forgot-password", "/api/auth/reset-password"}

    async def dispatch(self, request: Request, call_next):
        if request.method not in SAFE_METHODS and request.url.path not in self.EXEMPT_PATHS:
            has_cookie_session = ACCESS_COOKIE in request.cookies or REFRESH_COOKIE in request.cookies
            has_bearer = request.headers.get("authorization", "").lower().startswith("bearer ")
            if has_cookie_session and not has_bearer:
                cookie = request.cookies.get(CSRF_COOKIE, "")
                header = request.headers.get(CSRF_HEADER, "")
                if not cookie or not header or not secrets.compare_digest(cookie, header):
                    return JSONResponse({"detail": "CSRF validation failed. Please refresh the page."},
                                        status_code=403)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        # Privacy-aware access log: path + status only, never bodies or query strings.
        logger.info("%s %s %s %.0fms", request.method, request.url.path, response.status_code,
                    (time.perf_counter() - start) * 1000)
        return response
