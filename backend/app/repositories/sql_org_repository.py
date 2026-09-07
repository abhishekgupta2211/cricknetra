"""SQL-backed areas, organizations and organizer profiles.

The durable twin of :class:`~app.repositories.org_repository.InMemoryOrgRepository`,
satisfying the same ``OrgRepository`` Protocol so nothing above it changes. It
matters more than a cache would: ``ScopeService.require_active_organizer`` reads
a profile on every organizer write, so a registry that lives in one worker's
memory means the same account is an active organizer on one process and a
suspended one on the next.

Ids are ints in the database and strings everywhere above it (as the in-memory
store hands out "1", "2", …), so they are converted at this boundary and nowhere
else.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AreaRow, OrganizationRow, OrganizerProfileRow
from app.repositories.org_repository import AreaRecord, OrganizationRecord, OrganizerRecord


def _pint(value: Optional[str]) -> Optional[int]:
    """An id from the API is a string; the primary keys are ints. A value that
    is not a number is a miss, not a crash — ids arrive from URLs."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _area(row: AreaRow) -> AreaRecord:
    return AreaRecord(id=str(row.id), name=row.name, state=row.state, created_at=row.created_at)


def _organization(row: OrganizationRow) -> OrganizationRecord:
    return OrganizationRecord(
        id=str(row.id), name=row.name, area_id=row.area_id, created_at=row.created_at
    )


def _organizer(row: OrganizerProfileRow) -> OrganizerRecord:
    return OrganizerRecord(
        user_id=row.user_id,
        area_id=row.area_id,
        organization_id=row.organization_id,
        is_active=bool(row.is_active),
        created_by=row.created_by,
        created_at=row.created_at,
    )


class SqlOrgRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    # ----- areas -----
    def add_area(self, name: str, state: Optional[str] = None) -> AreaRecord:
        with self._sf() as s:
            row = AreaRow(name=name.strip(), state=(state or None))
            s.add(row)
            s.commit()
            s.refresh(row)
            return _area(row)

    def list_areas(self) -> list[AreaRecord]:
        with self._sf() as s:
            rows = s.query(AreaRow).order_by(func.lower(AreaRow.name)).all()
            return [_area(r) for r in rows]

    def get_area(self, area_id: str) -> Optional[AreaRecord]:
        aid = _pint(area_id)
        if aid is None:
            return None
        with self._sf() as s:
            row = s.get(AreaRow, aid)
            return _area(row) if row else None

    def delete_area(self, area_id: str) -> None:
        aid = _pint(area_id)
        if aid is None:
            return
        with self._sf() as s:
            s.query(AreaRow).filter_by(id=aid).delete()
            s.commit()

    # ----- organizations -----
    def add_organization(self, name: str, area_id: Optional[str] = None) -> OrganizationRecord:
        with self._sf() as s:
            row = OrganizationRow(
                name=name.strip(), area_id=(str(area_id) if area_id else None)
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return _organization(row)

    def list_organizations(self, area_id: Optional[str] = None) -> list[OrganizationRecord]:
        with self._sf() as s:
            q = s.query(OrganizationRow)
            if area_id is not None:
                q = q.filter_by(area_id=str(area_id))
            return [_organization(r) for r in q.order_by(func.lower(OrganizationRow.name)).all()]

    def get_organization(self, org_id: str) -> Optional[OrganizationRecord]:
        oid = _pint(org_id)
        if oid is None:
            return None
        with self._sf() as s:
            row = s.get(OrganizationRow, oid)
            return _organization(row) if row else None

    def delete_organization(self, org_id: str) -> None:
        oid = _pint(org_id)
        if oid is None:
            return
        with self._sf() as s:
            s.query(OrganizationRow).filter_by(id=oid).delete()
            s.commit()

    # ----- organizers -----
    def upsert_organizer(
        self,
        user_id: str,
        area_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> OrganizerRecord:
        """Create the profile, or move an existing one and reactivate it.

        Mirrors the in-memory behaviour exactly, including the part that reads
        oddly on its own: an update only overwrites the area/organization when a
        new one was supplied, so a PATCH that changes nothing does not blank the
        posting. The unique index on ``user_id`` is what makes "one profile per
        account" true under concurrency rather than only in one worker.
        """
        uid = str(user_id)
        with self._sf() as s:
            row = s.query(OrganizerProfileRow).filter_by(user_id=uid).first()
            if row is not None:
                if area_id:
                    row.area_id = str(area_id)
                if organization_id:
                    row.organization_id = str(organization_id)
                row.is_active = True
                s.commit()
                s.refresh(row)
                return _organizer(row)
            row = OrganizerProfileRow(
                user_id=uid,
                area_id=str(area_id) if area_id else None,
                organization_id=str(organization_id) if organization_id else None,
                created_by=str(created_by) if created_by else None,
                is_active=True,
            )
            s.add(row)
            try:
                s.commit()
            except IntegrityError:
                # Raced with another appointment of the same account; the row
                # that won is the one profile, so return it rather than fail an
                # action that has effectively already happened.
                s.rollback()
                row = s.query(OrganizerProfileRow).filter_by(user_id=uid).first()
                if row is None:  # pragma: no cover - the constraint says this cannot happen
                    raise
                return _organizer(row)
            s.refresh(row)
            return _organizer(row)

    def get_organizer(self, user_id: str) -> Optional[OrganizerRecord]:
        with self._sf() as s:
            row = s.query(OrganizerProfileRow).filter_by(user_id=str(user_id)).first()
            return _organizer(row) if row else None

    def list_organizers(self, area_id: Optional[str] = None) -> list[OrganizerRecord]:
        with self._sf() as s:
            q = s.query(OrganizerProfileRow)
            if area_id is not None:
                q = q.filter_by(area_id=str(area_id))
            rows = [_organizer(r) for r in q.all()]
        # Ordered in Python by the numeric user id, as the in-memory store does:
        # the column is a string, so the database would sort "10" before "9".
        return sorted(rows, key=lambda o: int(o.user_id) if o.user_id.isdigit() else 0)

    def set_organizer_active(self, user_id: str, active: bool) -> Optional[OrganizerRecord]:
        with self._sf() as s:
            row = s.query(OrganizerProfileRow).filter_by(user_id=str(user_id)).first()
            if row is None:
                return None
            row.is_active = bool(active)
            s.commit()
            s.refresh(row)
            return _organizer(row)

    def delete_organizer(self, user_id: str) -> None:
        with self._sf() as s:
            s.query(OrganizerProfileRow).filter_by(user_id=str(user_id)).delete()
            s.commit()
