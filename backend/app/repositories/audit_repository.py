"""An append-only record of who changed what.

Written on the actions that move authority or destroy data — a role being
granted, an organizer being created, a tournament being deleted. Deliberately
not a general activity feed: `activities` already covers "what happened in the
cricket", and mixing the two makes both harder to read.

Failing to write an audit line must never fail the action it describes, so the
service swallows its own errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Protocol


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuditActions:
    ROLE_ASSIGNED = "role.assigned"
    ORGANIZER_CREATED = "organizer.created"
    ORGANIZER_DEACTIVATED = "organizer.deactivated"
    TOURNAMENT_CREATED = "tournament.created"
    TOURNAMENT_UPDATED = "tournament.updated"
    TOURNAMENT_DELETED = "tournament.deleted"
    STAFF_ADDED = "staff.added"
    STAFF_REMOVED = "staff.removed"
    PLAYER_ADDED = "player.added"
    MATCH_DELETED = "match.deleted"
    ACCESS_DENIED = "access.denied"


@dataclass
class AuditRecord:
    id: str
    actor_id: Optional[str]
    action: str
    resource_type: str = ""
    resource_id: str = ""
    detail: str = ""
    when: datetime = field(default_factory=_now)


class AuditRepository(Protocol):
    def add(
        self,
        actor_id: Optional[str],
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        detail: str = "",
    ) -> AuditRecord: ...
    def list(
        self,
        limit: int = 100,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> list[AuditRecord]: ...


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self._rows: list[AuditRecord] = []
        self._next = 1

    def add(
        self,
        actor_id: Optional[str],
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        detail: str = "",
    ) -> AuditRecord:
        rec = AuditRecord(
            id=str(self._next),
            actor_id=str(actor_id) if actor_id is not None else None,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            detail=detail,
        )
        self._next += 1
        self._rows.append(rec)
        return rec

    def list(
        self,
        limit: int = 100,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> list[AuditRecord]:
        rows = self._rows
        if action:
            rows = [r for r in rows if r.action == action]
        if actor_id:
            rows = [r for r in rows if r.actor_id == str(actor_id)]
        if resource_type:
            rows = [r for r in rows if r.resource_type == resource_type]
        if resource_id:
            rows = [r for r in rows if r.resource_id == str(resource_id)]
        # Newest first — an audit trail is read from the most recent change back.
        return list(reversed(rows))[:limit]
