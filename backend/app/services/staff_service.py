"""The umpires and commentators an organizer runs a competition with.

`match_officials` answers "may this umpire score match 7". This answers the
question before it: who is on the staff of a tournament at all. The two stay
separate on purpose — being on a competition's staff does not by itself hand
somebody a particular fixture.

Three rules this module exists to enforce:

* **A staff entry belongs to one tournament.** Every write is keyed by
  (tournament, user, role), so removing somebody from Organizer A's cup cannot
  reach their account or their standing on Organizer B's league. The same
  person on two competitions is two independent entries, not one shared one.
* **Adding may promote, never demote.** A ``general_user`` put on the staff is
  promoted to umpire/commentator, because that is the whole point of the
  action. Somebody who already holds a role — a player, a team owner, another
  organizer — keeps it: silently rewriting it would quietly take away access
  they already have, so that case is refused with a 409 that says so.
* **Nothing is trusted from the request.** The caller and their id arrive from
  the auth dependency, and whether they own the tournament was already decided
  by :class:`~app.services.scope_service.ScopeService` before the route called
  in here. This service is handed facts, it does not authorize.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.permissions import Roles
from app.repositories.audit_repository import AuditActions
from app.repositories.tournament_repository import TournamentRepository
from app.repositories.tournament_staff_repository import (
    STAFF_ROLES,
    StaffRecord,
    TournamentStaffRepository,
)
from app.repositories.user_repository import UserRecord, UserRepository
from app.schemas.org import StaffDTO


class StaffError(Exception):
    """Something the caller asked for cannot be done, with the reason to show
    them. Carries its own status code so the route stays a thin translation."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class StaffingEntry:
    """One "you are staff here" line for a person's own dashboard.

    Deliberately not a :class:`StaffDTO`: that answers "who is on this
    tournament", which needs the person's details; this answers "which
    tournaments am I on", which needs the competition's.
    """

    tournament_id: str
    tournament_name: str
    staff_role: str
    is_active: bool


class StaffService:
    def __init__(
        self,
        staff: TournamentStaffRepository,
        users: UserRepository,
        tournaments: Optional[TournamentRepository] = None,
        audit=None,
    ) -> None:
        self.staff = staff
        self.users = users
        self.tournaments = tournaments
        self.audit = audit  # optional AuditService; writing to it never fails a call

    # --------------------------------------------------------------- reading

    def list_for_tournament(
        self, tournament_id: str, staff_role: Optional[str] = None
    ) -> list[StaffDTO]:
        """Everybody on this competition's staff, deactivated entries included.

        An organizer who stood somebody down still needs to see them, or the
        only way back is to add them again from memory.
        """
        self._require_staff_role(staff_role, allow_none=True)
        self._require_tournament(tournament_id)
        return [self._dto(rec) for rec in self.staff.list_for_tournament(tournament_id, staff_role)]

    def staffing_for(self, user_id: str, staff_role: Optional[str] = None) -> list[StaffingEntry]:
        """The competitions this person is currently staff on.

        The caller is always the person themselves — the route reads them from
        the token rather than a query parameter, so no one can enumerate
        somebody else's assignments by passing another id.
        """
        self._require_staff_role(staff_role, allow_none=True)
        out: list[StaffingEntry] = []
        for rec in self.staff.list_for_user(str(user_id), staff_role):
            out.append(
                StaffingEntry(
                    tournament_id=rec.tournament_id,
                    tournament_name=self._tournament_name(rec.tournament_id),
                    staff_role=rec.staff_role,
                    is_active=rec.is_active,
                )
            )
        return out

    # --------------------------------------------------------------- writing

    def add(
        self,
        tournament_id: str,
        user_id: str,
        staff_role: str,
        added_by: Optional[str] = None,
    ) -> StaffDTO:
        """Put somebody on this competition's staff, promoting them if they hold
        no role yet.

        ``added_by`` is the authenticated organizer the route passed in, never a
        value from the body — otherwise the audit trail would record whoever the
        caller claimed to be.
        """
        self._require_staff_role(staff_role)
        self._require_tournament(tournament_id)

        user = self.users.get_by_id(str(user_id))
        if user is None:
            raise StaffError("No account with that id — check the user id and try again.", 404)
        if not user.is_active:
            raise StaffError(
                f"{self._who(user)}'s account is deactivated, so they can't be given "
                f"a job on a tournament.",
                409,
            )

        if user.role != staff_role:
            if user.role != Roles.GENERAL_USER:
                # The refusal that keeps this endpoint from being a back door
                # into role changes. Promoting the roleless is the feature;
                # rewriting an existing role is a demotion in disguise.
                raise StaffError(
                    f"{self._who(user)} already holds the "
                    f"'{Roles.label(user.role)}' role. Adding them as "
                    f"{self._article(staff_role)} would take that away, so an admin has to "
                    f"change their role first.",
                    409,
                )
            promoted = self.users.set_role(user.id, staff_role)
            user = promoted or user
            self._record(
                added_by,
                AuditActions.ROLE_ASSIGNED,
                "user",
                user.id,
                f"promoted to {Roles.label(staff_role)} on joining tournament {tournament_id}",
            )

        rec = self.staff.add(tournament_id, user.id, staff_role, added_by)
        self._record(
            added_by,
            AuditActions.STAFF_ADDED,
            "tournament",
            tournament_id,
            f"{self._who(user)} added as {Roles.label(staff_role)}",
        )
        return self._dto(rec, user)

    def remove(
        self,
        tournament_id: str,
        user_id: str,
        staff_role: str,
        actor_id: Optional[str] = None,
    ) -> None:
        """Take somebody off *this* competition's staff.

        Their account, their role and their entries on every other tournament
        are deliberately untouched: an organizer decides who works their own
        competition, not who somebody is.
        """
        self._require_staff_role(staff_role)
        rec = self.staff.get(tournament_id, user_id, staff_role)
        if rec is None:
            raise StaffError(
                f"That person isn't {self._article(staff_role)} on this tournament.", 404
            )
        self.staff.remove(tournament_id, user_id, staff_role)
        self._record(
            actor_id,
            AuditActions.STAFF_REMOVED,
            "tournament",
            tournament_id,
            f"{self._who(self.users.get_by_id(str(user_id)))} removed as "
            f"{Roles.label(staff_role)} (account and other tournaments untouched)",
        )

    def set_active(
        self, tournament_id: str, user_id: str, staff_role: str, active: bool
    ) -> StaffDTO:
        """Stand somebody down for this competition, or bring them back.

        Softer than :meth:`remove`: the entry survives, so an umpire who is
        unavailable for a week does not have to be re-added afterwards.
        """
        self._require_staff_role(staff_role)
        rec = self.staff.set_active(tournament_id, user_id, staff_role, bool(active))
        if rec is None:
            raise StaffError(
                f"That person isn't {self._article(staff_role)} on this tournament.", 404
            )
        return self._dto(rec)

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _require_staff_role(staff_role: Optional[str], allow_none: bool = False) -> None:
        if staff_role is None and allow_none:
            return
        if staff_role not in STAFF_ROLES:
            raise StaffError(
                f"'{staff_role}' isn't a tournament staff role — expected "
                f"{' or '.join(repr(r) for r in STAFF_ROLES)}.",
                400,
            )

    def _require_tournament(self, tournament_id: str) -> None:
        """A tournament that does not exist is a 404, not an empty staff list —
        an organizer mistyping an id should hear about it."""
        if self.tournaments is None:
            return
        if self.tournaments.get(str(tournament_id)) is None:
            raise StaffError("No such tournament.", 404)

    def _tournament_name(self, tournament_id: str) -> str:
        if self.tournaments is None:
            return ""
        rec = self.tournaments.get(str(tournament_id))
        return rec.name if rec is not None else ""

    @staticmethod
    def _who(user: Optional[UserRecord]) -> str:
        """A name for a message. Falls back through what the account actually
        has, so the detail never reads "None already holds…"."""
        if user is None:
            return "That person"
        return user.full_name or user.username or f"User {user.id}"

    @staticmethod
    def _article(staff_role: str) -> str:
        return f"an {staff_role}" if staff_role == Roles.UMPIRE else f"a {staff_role}"

    def _dto(self, rec: StaffRecord, user: Optional[UserRecord] = None) -> StaffDTO:
        user = user or self.users.get_by_id(rec.user_id)
        return StaffDTO(
            user_id=rec.user_id,
            full_name=getattr(user, "full_name", "") or "",
            username=getattr(user, "username", "") or "",
            mobile_no=getattr(user, "mobile_no", "") or "",
            staff_role=rec.staff_role,
            is_active=rec.is_active,
            tournament_id=rec.tournament_id,
            added_by=rec.added_by,
        )

    def _record(
        self,
        actor_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: str,
        detail: str,
    ) -> None:
        """Note it in the audit trail if there is one. A staffing change that
        happened must not be reported as a failure because the note wasn't."""
        if self.audit is None:
            return
        self.audit.record(actor_id, action, resource_type, str(resource_id), detail)
