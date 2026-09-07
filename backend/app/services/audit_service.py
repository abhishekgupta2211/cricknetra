"""The audit trail — reading it, and writing to it without ever getting in the way.

Two halves with deliberately different temperaments:

* :meth:`AuditService.record` is *fire and forget*. A role grant that succeeded
  must not be reported to the caller as a failure because the trail was
  unwritable, so every error here is logged and swallowed. The repository
  contract says the same thing; this is where it is enforced.
* :meth:`AuditService.list` is a normal read, newest first, with the actor's
  name resolved so the admin screen shows "Test Admin" rather than a bare id.

Actor ids are always taken from the authenticated caller by the route, never
from a request body — nothing here would notice the difference, which is
precisely why the route must not offer the choice.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.repositories.audit_repository import AuditRecord, AuditRepository
from app.repositories.user_repository import UserRepository
from app.schemas.org import AuditDTO

logger = logging.getLogger(__name__)

#: An admin screen is read in pages; an unbounded limit would let one request
#: pull the whole trail.
MAX_LIMIT = 500


class AuditService:
    def __init__(self, repo: AuditRepository, users: Optional[UserRepository] = None) -> None:
        self.repo = repo
        self.users = users

    # ------------------------------------------------------------- writing

    def record(
        self,
        actor_id: Optional[str],
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        detail: str = "",
    ) -> Optional[AuditRecord]:
        """Write one line. Never raises: the caller's action already happened,
        and losing the note about it is not a reason to undo it."""
        try:
            return self.repo.add(
                actor_id=str(actor_id) if actor_id is not None else None,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
                detail=detail,
            )
        except Exception:  # pragma: no cover - defensive; the store is in-memory in tests
            logger.warning("audit write failed for action=%s resource=%s", action, resource_id,
                           exc_info=True)
            return None

    # ------------------------------------------------------------- reading

    def list(
        self,
        limit: int = 100,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> list[AuditDTO]:
        """The trail, newest first, with actor names resolved."""
        limit = max(1, min(int(limit or 100), MAX_LIMIT))
        rows = self.repo.list(
            limit=limit, action=action, actor_id=actor_id,
            resource_type=resource_type, resource_id=resource_id,
        )
        # One lookup per distinct actor rather than one per row — a page of the
        # trail is usually a handful of people doing many things.
        names: dict[str, str] = {}
        for row in rows:
            if row.actor_id and row.actor_id not in names:
                names[row.actor_id] = self._name_of(row.actor_id)
        return [self._dto(row, names.get(row.actor_id or "", "")) for row in rows]

    def _name_of(self, actor_id: str) -> str:
        if self.users is None:
            return ""
        user = self.users.get_by_id(actor_id)
        if user is None:
            # A deleted account still shows in the trail — the record of what
            # they did outlives the account that did it.
            return ""
        return user.full_name or user.username or ""

    @staticmethod
    def _dto(row: AuditRecord, actor_name: str) -> AuditDTO:
        return AuditDTO(
            id=row.id,
            actor_id=row.actor_id,
            actor_name=actor_name,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            detail=row.detail,
            when=row.when.isoformat() if row.when else None,
        )
