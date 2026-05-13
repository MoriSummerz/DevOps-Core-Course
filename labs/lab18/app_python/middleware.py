import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from metrics import (
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
)

logger = logging.getLogger("app.access")


def _normalize_path(path: str) -> str:
    """Normalize path to keep label cardinality low."""
    if path in ("/", "/health", "/metrics"):
        return path
    return "/other"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs each HTTP request/response and tracks Prometheus metrics."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        method = request.method
        path = _normalize_path(request.url.path)

        http_requests_in_progress.inc()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration = time.time() - start_time
            http_requests_in_progress.dec()
            http_requests_total.labels(method=method, endpoint=path, status="500").inc()
            http_request_duration_seconds.labels(method=method, endpoint=path).observe(
                duration
            )
            logger.error(
                "Request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(exc),
                },
            )
            raise

        duration = time.time() - start_time
        http_requests_in_progress.dec()
        status = str(response.status_code)
        http_requests_total.labels(method=method, endpoint=path, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=path).observe(
            duration
        )

        logger.info(
            "Request processed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "client_ip": request.client.host if request.client else "unknown",
                "duration_ms": round(duration * 1000, 2),
            },
        )
        return response
