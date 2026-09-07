"""Application logging: a request-id-aware setup with console or JSON output.

`configure_logging()` is called once at startup (app/main.py). Every log record
carries the current request id (from a contextvar set by the request middleware),
so app logs can be correlated with the access log and error responses.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from typing import Optional

# Set per-request by RequestContextMiddleware; "-" outside a request.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return request_id_ctx.get()


class RequestIdFilter(logging.Filter):
    """Attach the current request id to every record as ``record.request_id``."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_ctx.get()
        return True


# Standard LogRecord attributes — anything else on the record is "extra" and is
# included in the JSON output.
_RESERVED = set(
    logging.makeLogRecord({}).__dict__.keys()
) | {"request_id", "message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """One compact JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable single line: time level [request_id] logger: message."""

    def __init__(self) -> None:
        super().__init__(
            "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )


_configured = False


def configure_logging(level: Optional[str] = None, fmt: Optional[str] = None) -> None:
    """Idempotently configure the root logger. Safe to call more than once."""
    global _configured
    from app.core.config import settings

    lvl = (level or settings.log_level or "INFO").upper()
    use_json = (fmt or settings.log_format or "console").lower() == "json"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if use_json else ConsoleFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()  # replace any prior handlers (incl. a second call)
    root.addHandler(handler)
    root.setLevel(lvl)

    # Uvicorn ships its own handlers; route them through ours instead so output
    # is uniform and request-id tagged. Its access log is redundant with our
    # middleware's, so silence it.
    for name in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False

    _configured = True
