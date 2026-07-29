import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("grammarcheck")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start

        correlation_id = getattr(request.state, "correlation_id", "-")
        logger.info(
            "%s %s → %s [%.0fms] cid=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed * 1000,
            correlation_id,
        )
        return response
