"""SQL-backed pending role requests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import RoleRequestRow
from app.repositories.role_request_repository import RoleRequestItem


def _to_item(row: RoleRequestRow) -> RoleRequestItem:
    return RoleRequestItem(
        id=str(row.id), user_id=row.user_id, requested_role=row.requested_role,
        status=row.status, when=(row.created_at.isoformat() if row.created_at else ""),
    )


class SqlRoleRequestRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def add(self, user_id, requested_role) -> None:
        with self._sf() as s:
            s.add(RoleRequestRow(user_id=str(user_id), requested_role=requested_role, status="pending"))
            s.commit()

    def pending_for(self, user_id) -> Optional[RoleRequestItem]:
        with self._sf() as s:
            row = (
                s.query(RoleRequestRow)
                .filter_by(user_id=str(user_id), status="pending")
                .order_by(RoleRequestRow.id.desc())
                .first()
            )
            return _to_item(row) if row else None

    def list_pending(self) -> list[RoleRequestItem]:
        with self._sf() as s:
            rows = (
                s.query(RoleRequestRow)
                .filter_by(status="pending")
                .order_by(RoleRequestRow.id.desc())
                .all()
            )
            return [_to_item(r) for r in rows]

    def set_status(self, user_id, status) -> bool:
        with self._sf() as s:
            n = (
                s.query(RoleRequestRow)
                .filter_by(user_id=str(user_id), status="pending")
                .update({"status": status, "decided_at": datetime.now(timezone.utc)})
            )
            s.commit()
            return bool(n)
