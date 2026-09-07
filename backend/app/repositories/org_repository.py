"""Organizers, and the areas and organizations they run competitions for.

An **area** is a place ("Prayagraj"); an **organization** is a body that runs
cricket there ("XYZ Sports"). An **organizer profile** ties a user account to
one of each, and is what makes somebody an organizer in practice — the role
string alone says what kind of thing they may do, this says where.

Kept as its own registry rather than columns on ``users`` so that the auth
tables stay about authentication, and so an account can be demoted or promoted
without losing the record of what it once ran.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Protocol


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AreaRecord:
    id: str
    name: str
    state: Optional[str] = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class OrganizationRecord:
    id: str
    name: str
    area_id: Optional[str] = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class OrganizerRecord:
    """One user's standing as an organizer."""

    user_id: str
    area_id: Optional[str] = None
    organization_id: Optional[str] = None
    is_active: bool = True
    created_by: Optional[str] = None  # the admin who set them up
    created_at: datetime = field(default_factory=_now)


class OrgRepository(Protocol):
    # areas
    def add_area(self, name: str, state: Optional[str]) -> AreaRecord: ...
    def list_areas(self) -> list[AreaRecord]: ...
    def get_area(self, area_id: str) -> Optional[AreaRecord]: ...
    def delete_area(self, area_id: str) -> None: ...

    # organizations
    def add_organization(self, name: str, area_id: Optional[str]) -> OrganizationRecord: ...
    def list_organizations(self, area_id: Optional[str] = None) -> list[OrganizationRecord]: ...
    def get_organization(self, org_id: str) -> Optional[OrganizationRecord]: ...
    def delete_organization(self, org_id: str) -> None: ...

    # organizers
    def upsert_organizer(
        self,
        user_id: str,
        area_id: Optional[str],
        organization_id: Optional[str],
        created_by: Optional[str],
    ) -> OrganizerRecord: ...
    def get_organizer(self, user_id: str) -> Optional[OrganizerRecord]: ...
    def list_organizers(self, area_id: Optional[str] = None) -> list[OrganizerRecord]: ...
    def set_organizer_active(self, user_id: str, active: bool) -> Optional[OrganizerRecord]: ...
    def delete_organizer(self, user_id: str) -> None: ...


class InMemoryOrgRepository:
    def __init__(self) -> None:
        self._areas: dict[str, AreaRecord] = {}
        self._orgs: dict[str, OrganizationRecord] = {}
        self._organizers: dict[str, OrganizerRecord] = {}
        self._next_area = 1
        self._next_org = 1

    # ----- areas -----
    def add_area(self, name: str, state: Optional[str] = None) -> AreaRecord:
        aid = str(self._next_area)
        self._next_area += 1
        rec = AreaRecord(id=aid, name=name.strip(), state=(state or None))
        self._areas[aid] = rec
        return rec

    def list_areas(self) -> list[AreaRecord]:
        return sorted(self._areas.values(), key=lambda a: a.name.lower())

    def get_area(self, area_id: str) -> Optional[AreaRecord]:
        return self._areas.get(str(area_id))

    def delete_area(self, area_id: str) -> None:
        self._areas.pop(str(area_id), None)

    # ----- organizations -----
    def add_organization(self, name: str, area_id: Optional[str] = None) -> OrganizationRecord:
        oid = str(self._next_org)
        self._next_org += 1
        rec = OrganizationRecord(
            id=oid, name=name.strip(), area_id=(str(area_id) if area_id else None)
        )
        self._orgs[oid] = rec
        return rec

    def list_organizations(self, area_id: Optional[str] = None) -> list[OrganizationRecord]:
        rows = self._orgs.values()
        if area_id is not None:
            rows = [o for o in rows if o.area_id == str(area_id)]
        return sorted(rows, key=lambda o: o.name.lower())

    def get_organization(self, org_id: str) -> Optional[OrganizationRecord]:
        return self._orgs.get(str(org_id))

    def delete_organization(self, org_id: str) -> None:
        self._orgs.pop(str(org_id), None)

    # ----- organizers -----
    def upsert_organizer(
        self,
        user_id: str,
        area_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> OrganizerRecord:
        uid = str(user_id)
        existing = self._organizers.get(uid)
        if existing is not None:
            existing.area_id = str(area_id) if area_id else existing.area_id
            existing.organization_id = (
                str(organization_id) if organization_id else existing.organization_id
            )
            existing.is_active = True
            return existing
        rec = OrganizerRecord(
            user_id=uid,
            area_id=str(area_id) if area_id else None,
            organization_id=str(organization_id) if organization_id else None,
            created_by=str(created_by) if created_by else None,
        )
        self._organizers[uid] = rec
        return rec

    def get_organizer(self, user_id: str) -> Optional[OrganizerRecord]:
        return self._organizers.get(str(user_id))

    def list_organizers(self, area_id: Optional[str] = None) -> list[OrganizerRecord]:
        rows = list(self._organizers.values())
        if area_id is not None:
            rows = [o for o in rows if o.area_id == str(area_id)]
        return sorted(rows, key=lambda o: int(o.user_id) if o.user_id.isdigit() else 0)

    def set_organizer_active(self, user_id: str, active: bool) -> Optional[OrganizerRecord]:
        rec = self._organizers.get(str(user_id))
        if rec is not None:
            rec.is_active = active
        return rec

    def delete_organizer(self, user_id: str) -> None:
        self._organizers.pop(str(user_id), None)
