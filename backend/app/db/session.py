"""Lazy SQLAlchemy engine + session factory.

The engine is created on first use, not at import, so importing the app (e.g. in
tests that use the in-memory repo) never opens a database connection.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401 — ensure models register on Base.metadata

logger = logging.getLogger(__name__)

# backend/ — alembic/ lives here (this file is backend/app/db/session.py)
_BACKEND_DIR = Path(__file__).resolve().parents[2]

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None

# init_db() runs migrations exactly once, serialized. FastAPI serves sync
# endpoints from a threadpool, so without this several cold-start requests would
# call Alembic concurrently (which isn't re-entrant — it raised KeyError('script')).
_init_lock = threading.Lock()
_init_done = False


def _ensure_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        if not settings.database_url:
            raise RuntimeError("CRICNETRA_DATABASE_URL is not configured")
        _engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    _ensure_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def db_ping() -> str:
    """Lightweight readiness check. Returns "ok", "not_configured", or "error: ...".

    Never raises — callers (e.g. /health) decide what status to report.
    """
    if not settings.database_url:
        return "not_configured"
    try:
        from sqlalchemy import text

        engine = _ensure_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:  # pragma: no cover - exercised only when DB is down
        return f"error: {type(e).__name__}"


def init_db() -> None:
    """Bring the schema to the latest Alembic revision.

    Alembic is the source of truth for the schema (so columns on existing tables
    can be altered). If it can't run for any reason, we fall back to
    ``create_all`` so the app still boots in a dev environment.

    Runs exactly once per process, serialized by a lock (see _init_lock above).
    """
    global _init_done
    if _init_done:
        return
    with _init_lock:
        if _init_done:  # another thread finished while we waited
            return
        engine = _ensure_engine()
        try:
            from alembic import command
            from alembic.config import Config

            cfg = Config()
            cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
            cfg.set_main_option("sqlalchemy.url", settings.database_url or "")
            command.upgrade(cfg, "head")
        except Exception as e:  # pragma: no cover - defensive dev fallback
            logger.warning("Alembic upgrade failed (%s); falling back to create_all", e)
            Base.metadata.create_all(engine)
        _init_done = True
