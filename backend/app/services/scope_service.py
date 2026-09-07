"""Who may act on which resource.

Capabilities say what kind of thing a role may do; this says *whose* things.
Two organizers both hold ``MANAGE_TOURNAMENT`` and neither may touch the
other's competition, so every write to an owned resource has to come through
here rather than stopping at the capability check.

The rules, in one place:

* **Admin** — everything.
* **Organizer** — the tournaments they own, and everything belonging to those:
  fixtures, squads, staff, and the matches started from them.
* **Umpire / commentator** — only what they were assigned, and only the actions
  their assignment implies.
* **Everyone else** — read what is public, write nothing that belongs to
  somebody else.

Ownership is always read from the database. Nothing here trusts an id, a role
or an organizer reference that arrived in a request body.
"""

from __future__ import annotations

from typing import Optional

from app.core.permissions import Caps, Roles, has_capability, is_admin
from app.repositories.tournament_staff_repository import COMMENTATOR, UMPIRE
from app.repositories.user_repository import UserRecord


class ScopeError(Exception):
    """The caller is authenticated but may not touch this resource."""

    def __init__(self, detail: str = "You don't have access to this resource.") -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = 403


class ScopeService:
    def __init__(self, owners, tournaments, staff, officials=None, orgs=None) -> None:
        self.owners = owners
        self.tournaments = tournaments
        self.staff = staff
        self.officials = officials
        self.orgs = orgs

    # ------------------------------------------------------------ ownership

    def owner_of(self, resource_type: str, resource_id: str) -> Optional[str]:
        return self.owners.get_owner(resource_type, str(resource_id))

    def owns(self, user: UserRecord, resource_type: str, resource_id: str) -> bool:
        owner = self.owner_of(resource_type, resource_id)
        return owner is not None and str(owner) == str(user.id)

    # ---------------------------------------------------------- tournaments

    def manages_tournament(self, user: UserRecord, tournament_id: str) -> bool:
        """True for the admin and for the organizer who owns this competition."""
        if is_admin(user.role):
            return True
        return self.owns(user, "tournament", tournament_id)

    def require_tournament(
        self, user: UserRecord, tournament_id: str, cap: Optional[str] = None
    ) -> None:
        """Guard a write inside somebody's competition.

        An unowned tournament (created before ownership was recorded) can only
        be managed by a capability holder — never left open to everybody.
        """
        if is_admin(user.role):
            return
        owner = self.owner_of("tournament", tournament_id)
        if owner is not None:
            if str(owner) == str(user.id):
                return
            # Belongs to a different organizer. Holding the capability is not
            # enough — this is the check that stops one organizer reaching into
            # another's competition by changing the id in the URL.
            raise ScopeError("This tournament belongs to another organizer.")
        if cap is not None and has_capability(user.role, cap):
            return
        raise ScopeError("This tournament belongs to another organizer.")

    # --------------------------------------------------------------- matches

    def tournament_of_match(self, match_id: str) -> Optional[str]:
        """The competition a match was started from, if any."""
        finder = getattr(self.tournaments, "tournament_id_for_match", None)
        if callable(finder):
            return finder(str(match_id))
        return None

    def can_score(self, user: UserRecord, match_id: str) -> bool:
        """Score this match: the admin, whoever started it, the organizer whose
        competition it belongs to, or an umpire approved for *this* match.

        Deliberately not "anybody holding SCORE_MATCH": every organizer holds
        it, and that would let one score another's fixtures.
        """
        if is_admin(user.role):
            return True
        if self.owns(user, "match", match_id):
            return True
        tid = self.tournament_of_match(match_id)
        if tid is not None and self.owns(user, "tournament", tid):
            return True
        if self.officials is not None and self.officials.is_approved(match_id, user.id):
            return True
        return False

    def require_score(self, user: UserRecord, match_id: str) -> None:
        if not self.can_score(user, match_id):
            raise ScopeError("You're not approved to officiate this match.")

    def can_manage_match(self, user: UserRecord, match_id: str) -> bool:
        """Edit or delete a match — narrower than scoring: an assigned umpire
        may score, but only the owner or the organizer may delete."""
        if is_admin(user.role):
            return True
        if self.owns(user, "match", match_id):
            return True
        tid = self.tournament_of_match(match_id)
        return tid is not None and self.owns(user, "tournament", tid)

    def require_manage_match(self, user: UserRecord, match_id: str) -> None:
        if not self.can_manage_match(user, match_id):
            raise ScopeError("You don't have permission to modify this match.")

    # ----------------------------------------------------------------- staff

    def is_staff(self, user: UserRecord, tournament_id: str, staff_role: str) -> bool:
        rec = self.staff.get(str(tournament_id), str(user.id), staff_role)
        return rec is not None and rec.is_active

    def can_view_tournament_workspace(self, user: UserRecord, tournament_id: str) -> bool:
        """May this person open the working view of a competition — the one with
        fixtures and staff on it, as opposed to the public scorecard."""
        if self.manages_tournament(user, tournament_id):
            return True
        return self.is_staff(user, tournament_id, UMPIRE) or self.is_staff(
            user, tournament_id, COMMENTATOR
        )

    def require_workspace(self, user: UserRecord, tournament_id: str) -> None:
        if not self.can_view_tournament_workspace(user, tournament_id):
            raise ScopeError("You're not part of this tournament.")

    def tournaments_for_staff(self, user: UserRecord, staff_role: Optional[str] = None) -> list[str]:
        """The competitions this person was assigned to, newest first."""
        return [r.tournament_id for r in self.staff.list_for_user(user.id, staff_role)]

    def can_commentate(self, user: UserRecord, match_id: str) -> bool:
        """Post commentary: the admin, the match owner, the organizer whose
        competition it is, or a commentator assigned to that competition.

        A commentator with no assignment keeps the blanket capability, which is
        how open/friendly matches have always worked.
        """
        if self.can_manage_match(user, match_id):
            return True
        tid = self.tournament_of_match(match_id)
        if tid is not None:
            if self.is_staff(user, tid, COMMENTATOR):
                return True
            # A tournament match is the organizer's to staff, so a passing
            # commentator does not get to talk over it.
            return False
        return has_capability(user.role, Caps.COMMENTATE)

    # ------------------------------------------------------------- organizer

    def organizer_of(self, user: UserRecord):
        """The organizer profile for this account, if it has one."""
        if self.orgs is None:
            return None
        return self.orgs.get_organizer(str(user.id))

    def require_active_organizer(self, user: UserRecord) -> None:
        """An organizer whose profile was deactivated keeps the role string but
        loses the ability to act, without having to be demoted."""
        if is_admin(user.role):
            return
        if user.role != Roles.ORGANIZER:
            raise ScopeError("Only an organizer can do this.")
        profile = self.organizer_of(user)
        if profile is not None and not profile.is_active:
            raise ScopeError("Your organizer account is deactivated.")
