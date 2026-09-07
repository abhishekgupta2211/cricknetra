"""Umpires and commentators an organizer runs their competition with.

`match_officials` already answers "may this umpire score match 7". This answers
the question before it: who is on the organizer's staff for a tournament at all.
The two are deliberately separate — being on the staff of a tournament does not
by itself let you score a particular match in it.

A staff entry is scoped to one tournament. An umpire Organizer A adds does not
become available to Organizer B; B adds them to their own competition, and the
same person then holds two independent entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Protocol

UMPIRE = "umpire"
COMMENTATOR = "commentator"
STAFF_ROLES = (UMPIRE, COMMENTATOR)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class StaffRecord:
    id: str
    tournament_id: str
    user_id: str
    staff_role: str            # umpire | commentator
    is_active: bool = True
    added_by: Optional[str] = None   # the organizer who added them
    created_at: datetime = field(default_factory=_now)


class TournamentStaffRepository(Protocol):
    def add(
        self, tournament_id: str, user_id: str, staff_role: str, added_by: Optional[str]
    ) -> StaffRecord: ...
    def list_for_tournament(
        self, tournament_id: str, staff_role: Optional[str] = None
    ) -> list[StaffRecord]: ...
    def list_for_user(self, user_id: str, staff_role: Optional[str] = None) -> list[StaffRecord]: ...
    def get(self, tournament_id: str, user_id: str, staff_role: str) -> Optional[StaffRecord]: ...
    def set_active(
        self, tournament_id: str, user_id: str, staff_role: str, active: bool
    ) -> Optional[StaffRecord]: ...
    def remove(self, tournament_id: str, user_id: str, staff_role: str) -> None: ...
    def remove_tournament(self, tournament_id: str) -> None: ...


class InMemoryTournamentStaffRepository:
    def __init__(self) -> None:
        self._rows: dict[tuple[str, str, str], StaffRecord] = {}
        self._next = 1

    @staticmethod
    def _key(tournament_id: str, user_id: str, staff_role: str) -> tuple[str, str, str]:
        return (str(tournament_id), str(user_id), staff_role)

    def add(self, tournament_id, user_id, staff_role, added_by=None) -> StaffRecord:
        key = self._key(tournament_id, user_id, staff_role)
        existing = self._rows.get(key)
        if existing is not None:
            # Re-adding somebody who was removed reinstates them rather than
            # creating a second, conflicting entry.
            existing.is_active = True
            return existing
        rec = StaffRecord(
            id=str(self._next),
            tournament_id=str(tournament_id),
            user_id=str(user_id),
            staff_role=staff_role,
            added_by=str(added_by) if added_by else None,
        )
        self._next += 1
        self._rows[key] = rec
        return rec

    def list_for_tournament(self, tournament_id, staff_role=None) -> list[StaffRecord]:
        rows = [
            r for r in self._rows.values()
            if r.tournament_id == str(tournament_id)
            and (staff_role is None or r.staff_role == staff_role)
        ]
        return sorted(rows, key=lambda r: int(r.id))

    def list_for_user(self, user_id, staff_role=None) -> list[StaffRecord]:
        rows = [
            r for r in self._rows.values()
            if r.user_id == str(user_id)
            and r.is_active
            and (staff_role is None or r.staff_role == staff_role)
        ]
        return sorted(rows, key=lambda r: int(r.id))

    def get(self, tournament_id, user_id, staff_role) -> Optional[StaffRecord]:
        return self._rows.get(self._key(tournament_id, user_id, staff_role))

    def set_active(self, tournament_id, user_id, staff_role, active) -> Optional[StaffRecord]:
        rec = self._rows.get(self._key(tournament_id, user_id, staff_role))
        if rec is not None:
            rec.is_active = active
        return rec

    def remove(self, tournament_id, user_id, staff_role) -> None:
        self._rows.pop(self._key(tournament_id, user_id, staff_role), None)

    def remove_tournament(self, tournament_id) -> None:
        for key in [k for k in self._rows if k[0] == str(tournament_id)]:
            self._rows.pop(key, None)
