import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs each HTTP request/response in JSON format."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                "Request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
            )
            raise

        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "Request processed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "client_ip": request.client.host if request.client else "unknown",
                "duration_ms": duration_ms,
            },
        )
        return response
