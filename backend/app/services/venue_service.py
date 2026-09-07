"""Venue service — create / browse / search / delete grounds + academies."""

from __future__ import annotations

from typing import Optional

from app.repositories.user_repository import UserRecord
from app.repositories.venue_repository import VenueItem, VenueRepository
from app.schemas.venue import VenueCreate, VenueDTO

_KINDS = {"ground", "academy"}


class VenueError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _dto(i: VenueItem) -> VenueDTO:
    return VenueDTO(id=i.id, name=i.name, kind=i.kind, city=i.city, address=i.address,
                    contact=i.contact, note=i.note, when=i.when)


class VenueService:
    def __init__(self, repo: VenueRepository) -> None:
        self.repo = repo

    def create(self, user: UserRecord, req: VenueCreate) -> VenueDTO:
        if req.kind not in _KINDS:
            raise VenueError("kind must be ground or academy")
        name = (req.name or "").strip()
        if not name:
            raise VenueError("a name is required")
        item = self.repo.create(
            name, req.kind, (req.city or "").strip() or None,
            (req.address or "").strip() or None, (req.contact or "").strip() or None,
            (req.note or "").strip() or None, user.id if user else None,
        )
        return _dto(item)

    def list(self, kind: Optional[str] = None, location: Optional[str] = None,
             q: Optional[str] = None) -> list[VenueDTO]:
        if kind and kind not in _KINDS:
            kind = None
        return [_dto(i) for i in self.repo.list(kind=kind, location=location, q=q)]

    def get(self, venue_id: str) -> Optional[VenueDTO]:
        i = self.repo.get(venue_id)
        return _dto(i) if i else None

    def search(self, q: str, limit: int = 8) -> list[VenueDTO]:
        return [_dto(i) for i in self.repo.list(q=q, limit=limit)]

    def delete(self, venue_id: str) -> None:
        if not self.repo.delete(venue_id):
            raise VenueError("venue not found", 404)
