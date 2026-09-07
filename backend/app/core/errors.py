"""Global exception handlers — consistent JSON errors with a request id.

All error responses share the shape ``{"detail": ..., "request_id": "..."}``.
The 500 handler logs the full traceback server-side but never leaks it to the
client.
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging_config import request_id_ctx

logger = logging.getLogger("cricnetra.error")


def _request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    return rid or request_id_ctx.get()


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """4xx/5xx raised as HTTPException — keep status, detail and headers."""
    rid = _request_id(request)
    headers = dict(getattr(exc, "headers", None) or {})
    headers["X-Request-ID"] = rid
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": rid},
        headers=headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 — the same ``detail`` list FastAPI returns, plus the request id."""
    rid = _request_id(request)
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors()), "request_id": rid},
        headers={"X-Request-ID": rid},
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Unhandled error — log the traceback, return a generic 500 (no leak)."""
    rid = _request_id(request)
    logger.exception(
        "Unhandled error on %s %s", request.method, request.url.path,
        extra={"request_id": rid, "path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": rid},
        headers={"X-Request-ID": rid},
    )


def register_exception_handlers(app) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, internal_error_handler)
