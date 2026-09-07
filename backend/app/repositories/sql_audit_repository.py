"""SQL-backed audit trail.

The one store here that is worthless unless it is durable: the trail exists to
answer "who granted that role" and "who deleted that competition" weeks later,
and an in-memory trail answers both questions with silence after the next
deploy. Same ``AuditRepository`` Protocol as the in-memory version, so the
service above it is unchanged.

Append-only by construction — there is no update and no delete on this class,
and none should be added. A trail that can be edited is not evidence.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AuditLogRow
from app.repositories.audit_repository import AuditRecord


def _to_record(row: AuditLogRow) -> AuditRecord:
    return AuditRecord(
        id=str(row.id),
        actor_id=row.actor_id,
        action=row.action,
        resource_type=row.resource_type or "",
        resource_id=row.resource_id or "",
        detail=row.detail or "",
        when=row.created_at,
    )


class SqlAuditRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def add(
        self,
        actor_id: Optional[str],
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        detail: str = "",
    ) -> AuditRecord:
        with self._sf() as s:
            row = AuditLogRow(
                actor_id=str(actor_id) if actor_id is not None else None,
                action=action,
                resource_type=resource_type or "",
                resource_id=str(resource_id or ""),
                detail=detail or "",
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return _to_record(row)

    def list(
        self,
        limit: int = 100,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> list[AuditRecord]:
        """The trail, newest first — an audit log is read from the most recent
        change backwards, and the limit is applied after the filters so a
        narrow query returns its own newest page rather than whatever survived
        a cut of the whole table.

        Ordered by ``id`` rather than ``created_at``: the timestamp is a server
        default with a coarser resolution than a burst of writes, and rows
        written in the same instant must still come back in the order they
        happened.
        """
        with self._sf() as s:
            q = s.query(AuditLogRow)
            if action:
                q = q.filter(AuditLogRow.action == action)
            if actor_id:
                q = q.filter(AuditLogRow.actor_id == str(actor_id))
            if resource_type:
                q = q.filter(AuditLogRow.resource_type == resource_type)
            if resource_id:
                q = q.filter(AuditLogRow.resource_id == str(resource_id))
            rows = q.order_by(AuditLogRow.id.desc()).limit(max(1, int(limit or 100))).all()
            return [_to_record(r) for r in rows]
