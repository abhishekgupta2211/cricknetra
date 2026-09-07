"""Request context + access logging middleware.

Implemented as pure ASGI (not BaseHTTPMiddleware) so it never buffers response
bodies — important for the Server-Sent-Events match stream, which must flush
chunks as they happen.

For each HTTP request it:
  * assigns a request id (honouring an inbound ``X-Request-ID``, else a new one),
  * exposes it via a contextvar (so all log records carry it) and on
    ``request.state.request_id`` (so exception handlers can read it),
  * adds ``X-Request-ID`` to the response,
  * emits one structured access-log line with method, path, status and duration.
"""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging_config import request_id_ctx

access_logger = logging.getLogger("cricnetra.access")

_MAX_ID_LEN = 64  # don't trust an unbounded inbound header


def _inbound_request_id(scope: Scope) -> str:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id" and value:
            return value.decode("latin-1")[:_MAX_ID_LEN]
    return uuid4().hex


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _inbound_request_id(scope)
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_ctx.set(request_id)

        start = time.perf_counter()
        status_holder = {"code": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                headers = message.setdefault("headers", [])
                # An exception handler may have already set it; don't duplicate.
                if not any(k == b"x-request-id" for k, _ in headers):
                    headers.append((b"x-request-id", request_id.encode("latin-1")))
                self._log(scope, status_holder["code"], start)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # Unhandled: log the access line as 500 here (the response itself is
            # produced by the exception handler), then let it propagate.
            self._log(scope, 500, start, errored=True)
            raise
        finally:
            request_id_ctx.reset(token)

    @staticmethod
    def _log(scope: Scope, status: int, start: float, errored: bool = False) -> None:
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        client = scope.get("client")
        path = scope.get("path", "")
        if scope.get("query_string"):
            path = f"{path}?{scope['query_string'].decode('latin-1')}"
        level = logging.ERROR if status >= 500 else logging.INFO
        access_logger.log(
            level,
            "%s %s -> %s (%.1fms)",
            scope.get("method", "?"),
            path,
            status,
            duration_ms,
            extra={
                "http_method": scope.get("method"),
                "path": scope.get("path"),
                "status": status,
                "duration_ms": duration_ms,
                "client_ip": client[0] if client else None,
                "errored": errored,
            },
        )
