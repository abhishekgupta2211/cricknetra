"""Alembic environment — wired to the app's models and settings.

The DB URL comes from the app settings (CRICNETRA_DATABASE_URL) or an
ALEMBIC_DATABASE_URL override, so there's a single source of truth.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `app` importable when alembic runs from the backend/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db import models  # noqa: E402,F401 — registers every table on Base.metadata

config = context.config
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:  # pragma: no cover - logging config is best-effort
        pass

target_metadata = Base.metadata


def _db_url() -> str:
    return (
        config.get_main_option("sqlalchemy.url")
        or os.environ.get("ALEMBIC_DATABASE_URL")
        or settings.database_url
        or "sqlite:///./_alembic_tmp.db"
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(), target_metadata=target_metadata,
        literal_binds=True, compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _db_url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool, future=True)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
