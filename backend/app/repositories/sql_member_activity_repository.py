"""SQL-backed member activity repository."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import MemberActivityRow


class SqlMemberActivityRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def record(self, user_id, kind, resource_id) -> None:
        with self._sf() as s:
            exists = (
                s.query(MemberActivityRow.id)
                .filter_by(user_id=str(user_id), kind=kind, resource_id=str(resource_id))
                .first()
            )
            if exists:
                return
            s.add(MemberActivityRow(user_id=str(user_id), kind=kind, resource_id=str(resource_id)))
            try:
                s.commit()
            except IntegrityError:  # raced with another insert — fine, it's recorded
                s.rollback()

    def count(self, user_id, kind) -> int:
        with self._sf() as s:
            return (
                s.query(func.count(MemberActivityRow.id))
                .filter_by(user_id=str(user_id), kind=kind)
                .scalar()
                or 0
            )
