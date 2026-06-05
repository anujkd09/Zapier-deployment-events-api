"""HTTP middleware: per-request correlation id + structured access logging."""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.access")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign/propagate a request id and log one structured line per request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Honor an inbound correlation id (from a gateway) or mint a fresh one.
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # The exception handler will produce the response; log the failure here
            # with timing/context, then re-raise so handlers can run.
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "latency_ms": latency_ms,
                },
            )
            raise

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response
