"""SQL-backed grounds + academies directory."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import VenueRow
from app.repositories.venue_repository import VenueItem


def _item(r: VenueRow) -> VenueItem:
    return VenueItem(str(r.id), r.name, r.kind, r.city, r.address, r.contact, r.note,
                     r.created_by, r.created_at.isoformat())


class SqlVenueRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def create(self, name, kind, city, address, contact, note, created_by) -> VenueItem:
        with self._sf() as s:
            row = VenueRow(
                name=name, kind=kind, city=(city or None), address=(address or None),
                contact=(contact or None), note=(note or None),
                created_by=(str(created_by) if created_by is not None else None),
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return _item(row)

    def get(self, venue_id) -> Optional[VenueItem]:
        try:
            vid = int(venue_id)
        except (TypeError, ValueError):
            return None
        with self._sf() as s:
            r = s.get(VenueRow, vid)
            return _item(r) if r else None

    def list(self, kind=None, location=None, q=None, limit=200) -> list[VenueItem]:
        with self._sf() as s:
            query = s.query(VenueRow)
            if kind:
                query = query.filter(VenueRow.kind == kind)
            if location and location.strip():
                query = query.filter(VenueRow.city.ilike(f"%{location.strip()}%"))
            if q and q.strip():
                like = f"%{q.strip()}%"
                query = query.filter(or_(VenueRow.name.ilike(like), VenueRow.city.ilike(like)))
            rows = query.order_by(VenueRow.name).limit(limit).all()
            return [_item(r) for r in rows]

    def delete(self, venue_id) -> bool:
        try:
            vid = int(venue_id)
        except (TypeError, ValueError):
            return False
        with self._sf() as s:
            n = s.query(VenueRow).filter_by(id=vid).delete()
            s.commit()
            return bool(n)
