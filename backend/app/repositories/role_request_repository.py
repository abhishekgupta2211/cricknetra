"""Pending elevated-role requests, awaiting admin approval.

A user who signs up as umpire/commentator/team_owner/organizer is created as a
``general_user`` and a *pending* request is recorded here; an admin approves it
to grant the real role (see ``RoleService``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RoleRequestItem:
    id: str
    user_id: str
    requested_role: str
    status: str
    when: str


class RoleRequestRepository(Protocol):
    def add(self, user_id: str, requested_role: str) -> None: ...
    def pending_for(self, user_id: str) -> Optional[RoleRequestItem]: ...
    def list_pending(self) -> list[RoleRequestItem]: ...
    def set_status(self, user_id: str, status: str) -> bool: ...


class InMemoryRoleRequestRepository:
    def __init__(self) -> None:
        self._reqs: list[dict] = []
        self._seq = 0

    def add(self, user_id, requested_role) -> None:
        self._seq += 1
        self._reqs.append({
            "id": str(self._seq), "user_id": str(user_id),
            "requested_role": requested_role, "status": "pending", "when": _now(),
        })

    def pending_for(self, user_id) -> Optional[RoleRequestItem]:
        for r in reversed(self._reqs):
            if r["user_id"] == str(user_id) and r["status"] == "pending":
                return RoleRequestItem(**r)
        return None

    def list_pending(self) -> list[RoleRequestItem]:
        return [RoleRequestItem(**r) for r in reversed(self._reqs) if r["status"] == "pending"]

    def set_status(self, user_id, status) -> bool:
        changed = False
        for r in self._reqs:
            if r["user_id"] == str(user_id) and r["status"] == "pending":
                r["status"] = status
                changed = True
        return changed
