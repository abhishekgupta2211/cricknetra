"""Liveness, readiness + metadata.

* ``/health``       — readiness: pings the database; 503 when a dependency is down.
* ``/health/live``  — liveness: process is up (no dependency checks).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.session import db_ping

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> JSONResponse:
    """Readiness probe. status is "ok" when every dependency is healthy.

    The database check returns "not_configured" in the in-memory mode (still
    healthy). A real error degrades the service and returns HTTP 503 so an
    orchestrator/load-balancer stops routing to this instance.
    """
    database = db_ping()
    healthy = database in ("ok", "not_configured")
    body = {
        "status": "ok" if healthy else "degraded",
        "app": settings.app_name,
        "version": settings.version,
        "checks": {"database": database},
    }
    return JSONResponse(status_code=200 if healthy else 503, content=body)


@router.get("/health/live")
def liveness() -> dict:
    """Liveness probe — the process is running; no dependencies are checked."""
    return {"status": "ok"}
