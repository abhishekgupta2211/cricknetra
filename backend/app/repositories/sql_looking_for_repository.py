"""SQL-backed "Looking For" board repository."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import LookingForRow
from app.repositories.looking_for_repository import LookingForItem


def _item(r: LookingForRow) -> LookingForItem:
    return LookingForItem(str(r.id), r.author_id, r.author_name, r.kind, r.text,
                          r.location, r.role, r.status, r.created_at.isoformat())


class SqlLookingForRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def create(self, author_id, author_name, kind, text, location, role) -> LookingForItem:
        with self._sf() as s:
            row = LookingForRow(
                author_id=str(author_id), author_name=author_name, kind=kind, text=text,
                location=(location or None), role=(role or None), status="open",
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return _item(row)

    def list(self, kind=None, location=None, limit=100) -> list[LookingForItem]:
        with self._sf() as s:
            q = s.query(LookingForRow).filter_by(status="open")
            if kind:
                q = q.filter(LookingForRow.kind == kind)
            if location and location.strip():
                q = q.filter(LookingForRow.location.ilike(f"%{location.strip()}%"))
            rows = q.order_by(LookingForRow.id.desc()).limit(limit).all()
            return [_item(r) for r in rows]

    def get(self, post_id) -> Optional[LookingForItem]:
        try:
            pid = int(post_id)
        except (TypeError, ValueError):
            return None
        with self._sf() as s:
            r = s.get(LookingForRow, pid)
            return _item(r) if r else None

    def mine(self, author_id) -> list[LookingForItem]:
        with self._sf() as s:
            rows = (
                s.query(LookingForRow).filter_by(author_id=str(author_id))
                .order_by(LookingForRow.id.desc()).all()
            )
            return [_item(r) for r in rows]

    def set_status(self, post_id, author_id, status, is_admin=False) -> bool:
        try:
            pid = int(post_id)
        except (TypeError, ValueError):
            return False
        with self._sf() as s:
            r = s.get(LookingForRow, pid)
            if r is None or (not is_admin and r.author_id != str(author_id)):
                return False
            r.status = status
            s.commit()
            return True

    def delete(self, post_id, author_id, is_admin=False) -> bool:
        try:
            pid = int(post_id)
        except (TypeError, ValueError):
            return False
        with self._sf() as s:
            r = s.get(LookingForRow, pid)
            if r is None or (not is_admin and r.author_id != str(author_id)):
                return False
            s.delete(r)
            s.commit()
            return True
