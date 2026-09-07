"""Database connectivity + event-sourced roundtrip check.

Usage (from repo root):
    PYTHONPATH=backend backend/.venv/Scripts/python.exe backend/scripts/db_check.py

Creates tables if missing, runs one persisted match through create → score →
reload, then cleans up. Prints a clear error (without leaking credentials) if the
database can't be reached.
"""

from __future__ import annotations

import sys

from app.core.config import settings


def main() -> int:
    if not settings.database_url:
        print("No CRICNETRA_DATABASE_URL set — the app would use the in-memory store.")
        return 1

    where = settings.database_url.rsplit("@", 1)[-1]  # host:port/db (no creds)
    print(f"Connecting to {where} ...")
    try:
        from app.db.session import get_sessionmaker, init_db
        from app.domain import presets
        from app.domain.engine import MatchEngine
        from app.domain.events import BallEvent
        from app.repositories.sql_match_repository import SqlMatchRepository

        init_db()  # CREATE TABLE IF NOT EXISTS
        repo = SqlMatchRepository(get_sessionmaker())

        sa = [f"A{i}" for i in range(11)]
        sb = [f"B{i}" for i in range(11)]
        m = MatchEngine(presets.t20(), "DBCheck A", "DBCheck B", sa, sb, bat_first="DBCheck A")
        mid = repo.add(m)
        m.current.set_bowler("B0")
        repo.save(mid, m)
        m.current.record(BallEvent.runs(4))
        repo.save(mid, m)

        runs = repo.get(mid).current.scorecard().runs  # type: ignore[union-attr]
        repo.delete(mid)
        print(f"OK — tables ready; created match {mid}, scored 4, reloaded runs={runs}; cleaned up.")
        return 0
    except Exception as e:  # noqa: BLE001 - report any connection/auth problem
        print(f"DB ERROR: {type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
