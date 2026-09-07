"""CricNetra application entrypoint.

Composition only. The JSON API (`/api/v1`) is the real interface.

Web surface:
  * ``/``, ``/contact``,
    ``/tips``, ``/tools``     — marketing site (Jinja, see ``app/public``)
  * ``/live-matches``,
    ``/tournaments``         — public directories of matches & cups
  * ``/m/{id}``, ``/t/{id}`` — public, server-rendered shareable pages
  * ``/app``                 — the dynamic HTML/CSS/JS scoring app (``frontend/index.html``)
  * ``/api/v1``              — the JSON API the app talks to (same-origin, no CORS needed)

The marketing/public pages all live in ``app/public`` and are registered (via
``public_router``) before the StaticFiles mount. CORS stays on for a future React
dev server on another port.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging_config import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.public.routes import public_router

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

# Configure logging before anything emits a record.
configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Cricket scoring with custom rules. JSON API under /api/v1; "
    "interactive docs at /docs. Marketing site at /, the scoring app at /app.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Added last → outermost: request id + access logging wrap every request
# (including CORS preflight and error responses).
app.add_middleware(RequestContextMiddleware)

# Consistent JSON error envelope with a request id; 500s never leak a traceback.
register_exception_handlers(app)

# JSON REST API (versioned) — must be registered before the catch-all SPA mount.
app.include_router(api_router, prefix="/api/v1")

# Marketing site + public directories + shareable pages (/, /contact, /tips,
# /tools, /live-matches, /tournaments, /m/{id}, /t/{id}) — before the mount.
app.include_router(public_router)


@app.get("/app", include_in_schema=False)
def webapp() -> FileResponse:
    """The dynamic single-page scoring app."""
    return FileResponse(_FRONTEND / "index.html")


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"status": "ok"}


# Auto-generated highlight clips (mp4s cut from an uploaded recording). Only the
# `clips` subtree is public — uploaded recordings live elsewhere under media_dir
# and are never served.
_MEDIA_CLIPS = Path(settings.media_dir) / "clips"
_MEDIA_CLIPS.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_MEDIA_CLIPS), html=False), name="media")

# Static assets (js, css, icons, manifest, service worker). html=False so this
# mount only serves real files — "/" and "/app" are handled by the routes above.
# Registered last so it only catches paths the API/pages didn't.
app.mount("/", StaticFiles(directory=str(_FRONTEND), html=False), name="static")
