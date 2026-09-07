"""Grounds + coaching academies directory (in-memory + SQL impls).

One table with a `kind` (ground | academy) — they share shape (a named place with
a city + contact), so a single store serves both, filterable by kind.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VenueItem:
    id: str
    name: str
    kind: str  # ground | academy
    city: Optional[str]
    address: Optional[str]
    contact: Optional[str]
    note: Optional[str]
    created_by: Optional[str]
    when: str


class VenueRepository(Protocol):
    def create(self, name: str, kind: str, city: Optional[str], address: Optional[str],
               contact: Optional[str], note: Optional[str], created_by: Optional[str]) -> VenueItem: ...
    def get(self, venue_id: str) -> Optional[VenueItem]: ...
    def list(self, kind: Optional[str] = None, location: Optional[str] = None,
             q: Optional[str] = None, limit: int = 200) -> list[VenueItem]: ...
    def delete(self, venue_id: str) -> bool: ...


class InMemoryVenueRepository:
    def __init__(self) -> None:
        self._v: list[dict] = []
        self._seq = 0

    def _item(self, v: dict) -> VenueItem:
        return VenueItem(v["id"], v["name"], v["kind"], v["city"], v["address"],
                         v["contact"], v["note"], v["created_by"], v["when"])

    def create(self, name, kind, city, address, contact, note, created_by) -> VenueItem:
        self._seq += 1
        v = {
            "id": str(self._seq), "name": name, "kind": kind, "city": city or None,
            "address": address or None, "contact": contact or None, "note": note or None,
            "created_by": str(created_by) if created_by is not None else None, "when": _now(),
        }
        self._v.append(v)
        return self._item(v)

    def get(self, venue_id) -> Optional[VenueItem]:
        v = next((x for x in self._v if x["id"] == str(venue_id)), None)
        return self._item(v) if v else None

    def list(self, kind=None, location=None, q=None, limit=200) -> list[VenueItem]:
        loc = (location or "").strip().lower()
        ql = (q or "").strip().lower()
        out = []
        for v in sorted(self._v, key=lambda x: x["name"].lower()):
            if kind and v["kind"] != kind:
                continue
            if loc and loc not in (v["city"] or "").lower():
                continue
            if ql and ql not in v["name"].lower() and ql not in (v["city"] or "").lower():
                continue
            out.append(self._item(v))
            if len(out) >= limit:
                break
        return out

    def delete(self, venue_id) -> bool:
        before = len(self._v)
        self._v = [v for v in self._v if v["id"] != str(venue_id)]
        return len(self._v) < before
