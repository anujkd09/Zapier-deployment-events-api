"""Domain exceptions and a single, consistent error response shape.

Every error the API returns — whether a domain 404, a request-validation 422, an
unexpected 500, or a stray Starlette HTTPException — is serialized through one
envelope so clients can parse failures uniformly:

    {
      "error": {
        "code": 404,                 # numeric HTTP status (mirrors the status line)
        "message": "Deployment not found",
        "status": "NOT_FOUND",       # canonical UPPER_SNAKE string (Google-style)
        "details": [ {"field": "environment", "message": "..."} ]   # optional
      }
    }

The shape follows Google's API error convention: a numeric ``code`` plus a stable
string ``status`` clients can branch on (more granular than HTTP codes alone).
"""

import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.error")

# Starlette renamed this status constant (HTTP_422_UNPROCESSABLE_ENTITY ->
# HTTP_422_UNPROCESSABLE_CONTENT). Prefer the new name when available and fall
# back for older versions, so we never touch the deprecated attribute.
HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", None) or (
    status.HTTP_422_UNPROCESSABLE_ENTITY
)


# --------------------------------------------------------------------------- #
# Response models (these also show up in the OpenAPI schema).
# --------------------------------------------------------------------------- #
class ErrorDetail(BaseModel):
    """A single field-level problem (used mainly for validation errors)."""

    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    # Numeric HTTP status (e.g. 404), mirroring the response status line.
    code: int
    message: str
    # Canonical UPPER_SNAKE status string (e.g. "NOT_FOUND") for stable branching.
    status: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    """The one and only error envelope returned by the API."""

    error: ErrorBody


# --------------------------------------------------------------------------- #
# Domain exceptions (decoupled from HTTP/transport concerns).
# --------------------------------------------------------------------------- #
class APIError(Exception):
    """Base class for expected, client-facing errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    status_str: str = "INTERNAL"
    message: str = "Internal server error"

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class NotFoundError(APIError):
    status_code = status.HTTP_404_NOT_FOUND
    status_str = "NOT_FOUND"
    message = "Resource not found"


# --------------------------------------------------------------------------- #
# Serialization helper + handlers.
# --------------------------------------------------------------------------- #
def _envelope(
    code: int, message: str, status_str: str, details: list[dict] | None = None
) -> dict:
    body: dict = {"code": code, "message": message, "status": status_str}
    if details:
        body["details"] = details
    return {"error": body}


def _error_response(
    request: Request,
    status_code: int,
    message: str,
    status_str: str,
    details: list[dict] | None = None,
) -> JSONResponse:
    """Build an error response, propagating the request's correlation id.

    The success path attaches ``X-Request-ID`` in middleware, but unhandled (500)
    responses are produced outside that middleware, so we set the header here to
    guarantee every error response carries the correlation id.
    """
    response = JSONResponse(
        status_code=status_code,
        content=_envelope(status_code, message, status_str, details),
    )
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Translate a domain exception into the standard envelope."""
    return _error_response(request, exc.status_code, exc.message, exc.status_str)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert FastAPI/Pydantic validation errors into the standard envelope."""
    details = []
    for err in exc.errors():
        # Drop the leading location segment ("body"/"query"/"path") for readability.
        loc = [
            str(part)
            for part in err.get("loc", [])
            if part not in ("body", "query", "path")
        ]
        details.append(
            {"field": ".".join(loc) or None, "message": err.get("msg", "invalid")}
        )
    return _error_response(
        request,
        HTTP_422,
        "Request validation failed",
        "INVALID_ARGUMENT",
        details,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Wrap framework HTTPExceptions (404 routing, 405, etc.) in the envelope."""
    status_str = {
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    }.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    return _error_response(request, exc.status_code, message, status_str)


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Last-resort handler: log the stack trace, return a safe generic message.

    We never leak internal details (exception text, stack) to the client.
    """
    logger.exception(
        "Unhandled exception on %s %s", request.method, request.url.path
    )
    return _error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Internal server error",
        "INTERNAL",
    )


def register_exception_handlers(app) -> None:
    """Attach all handlers to the FastAPI app."""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
