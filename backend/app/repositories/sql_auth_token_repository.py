"""SQL-backed short-lived auth tokens (verification codes + password resets)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AuthTokenRow
from app.repositories.auth_token_repository import AuthTokenItem


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_item(row: AuthTokenRow) -> AuthTokenItem:
    return AuthTokenItem(
        id=str(row.id), user_id=row.user_id, kind=row.kind,
        token_hash=row.token_hash, expires_at=row.expires_at, used_at=row.used_at,
    )


class SqlAuthTokenRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def add(self, user_id, kind, token_hash, expires_at) -> str:
        with self._sf() as s:
            row = AuthTokenRow(user_id=str(user_id), kind=kind, token_hash=token_hash, expires_at=expires_at)
            s.add(row)
            s.flush()
            tid = str(row.id)
            s.commit()
            return tid

    def find_valid(self, kind, token_hash, user_id=None) -> Optional[AuthTokenItem]:
        with self._sf() as s:
            q = s.query(AuthTokenRow).filter(
                AuthTokenRow.kind == kind,
                AuthTokenRow.token_hash == token_hash,
                AuthTokenRow.used_at.is_(None),
                AuthTokenRow.expires_at > _now(),
            )
            if user_id is not None:
                q = q.filter(AuthTokenRow.user_id == str(user_id))
            row = q.order_by(AuthTokenRow.id.desc()).first()
            return _to_item(row) if row else None

    def mark_used(self, token_id) -> None:
        with self._sf() as s:
            s.query(AuthTokenRow).filter(AuthTokenRow.id == int(token_id)).update({"used_at": _now()})
            s.commit()

    def invalidate(self, user_id, kind) -> None:
        with self._sf() as s:
            s.query(AuthTokenRow).filter(
                AuthTokenRow.user_id == str(user_id),
                AuthTokenRow.kind == kind,
                AuthTokenRow.used_at.is_(None),
            ).update({"used_at": _now()})
            s.commit()
