"""SQL-backed resource ownership registry."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import ResourceOwnerRow


class SqlOwnershipRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def set_owner(self, resource_type, resource_id, owner_id) -> None:
        with self._sf() as s:
            row = (
                s.query(ResourceOwnerRow)
                .filter_by(resource_type=resource_type, resource_id=str(resource_id))
                .first()
            )
            if row is not None:
                row.owner_id = str(owner_id)
            else:
                s.add(
                    ResourceOwnerRow(
                        resource_type=resource_type, resource_id=str(resource_id), owner_id=str(owner_id)
                    )
                )
            s.commit()

    def get_owner(self, resource_type, resource_id) -> Optional[str]:
        with self._sf() as s:
            row = (
                s.query(ResourceOwnerRow)
                .filter_by(resource_type=resource_type, resource_id=str(resource_id))
                .first()
            )
            return row.owner_id if row else None

    def delete(self, resource_type, resource_id) -> None:
        with self._sf() as s:
            s.query(ResourceOwnerRow).filter_by(
                resource_type=resource_type, resource_id=str(resource_id)
            ).delete()
            s.commit()

    def count_by_owner(self, owner_id, resource_type) -> int:
        with self._sf() as s:
            return (
                s.query(func.count(ResourceOwnerRow.id))
                .filter_by(owner_id=str(owner_id), resource_type=resource_type)
                .scalar()
                or 0
            )

    def list_by_owner(self, owner_id, resource_type) -> list[str]:
        with self._sf() as s:
            rows = (
                s.query(ResourceOwnerRow.resource_id)
                .filter_by(owner_id=str(owner_id), resource_type=resource_type)
                .all()
            )
            return [r[0] for r in rows]
