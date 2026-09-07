"""Roles, capabilities and scope.

Three layers of authorization in CricNetra, and a request must pass all of them:

  1. **Capability** — what *kinds* of thing a role may do at all (this file).
  2. **Ownership** — you may always manage what you created (``resource_owners``).
  3. **Scope** — an organizer's writes are confined to their own tournaments and
     the staff they created; see ``app/services/scope_service.py``.

Holding a capability is never sufficient on its own for a resource that belongs
to somebody: two organizers both hold ``MANAGE_TOURNAMENT``, and neither may
touch the other's competition. Admin bypasses all three.
"""

from __future__ import annotations


class Roles:
    """The role a user account holds. One role per account."""

    ADMIN = "admin"
    ORGANIZER = "organizer"
    TEAM_OWNER = "team_owner"
    UMPIRE = "umpire"
    COMMENTATOR = "commentator"
    PLAYER = "player"
    GENERAL_USER = "general_user"

    ALL = (ADMIN, ORGANIZER, TEAM_OWNER, UMPIRE, COMMENTATOR, PLAYER, GENERAL_USER)

    #: Roles an admin may assign to an existing account.
    ASSIGNABLE = (GENERAL_USER, PLAYER, TEAM_OWNER, UMPIRE, COMMENTATOR, ORGANIZER, ADMIN)

    @staticmethod
    def label(role: str) -> str:
        return role.replace("_", " ")


class Caps:
    # --- scoring -----------------------------------------------------------
    CREATE_MATCH = "match.create"          # start scoring a match
    SCORE_MATCH = "match.score"            # score a match you own or were assigned
    COMMENTATE = "match.commentate"        # post live commentary

    # --- roster ------------------------------------------------------------
    CREATE_TEAM = "team.create"            # create & manage teams and players
    MANAGE_PLAYERS = "player.manage"       # add players to your tournaments

    # --- competitions ------------------------------------------------------
    CREATE_TOURNAMENT = "tournament.create"
    MANAGE_TOURNAMENT = "tournament.manage"   # settings, fixtures, squads — yours only
    DELETE_TOURNAMENT = "tournament.delete"   # yours only (admin deletes any)

    # --- staff an organizer runs -------------------------------------------
    MANAGE_UMPIRES = "umpire.manage"          # create/assign umpires in your tournaments
    MANAGE_COMMENTATORS = "commentator.manage"

    MANAGE_RULES = "rules.manage"          # save/delete custom rule templates

    # --- system ------------------------------------------------------------
    MANAGE_USERS = "user.manage"           # assign roles, deactivate accounts
    MANAGE_ORGANIZERS = "organizer.manage"  # create organizers, areas, organizations


ALL_CAPS = frozenset({
    Caps.CREATE_MATCH,
    Caps.SCORE_MATCH,
    Caps.COMMENTATE,
    Caps.CREATE_TEAM,
    Caps.MANAGE_PLAYERS,
    Caps.CREATE_TOURNAMENT,
    Caps.MANAGE_TOURNAMENT,
    Caps.DELETE_TOURNAMENT,
    Caps.MANAGE_UMPIRES,
    Caps.MANAGE_COMMENTATORS,
    Caps.MANAGE_RULES,
    Caps.MANAGE_USERS,
    Caps.MANAGE_ORGANIZERS,
})

#: What each role may do — *subject to* ownership and scope. An organizer holds
#: MANAGE_TOURNAMENT for their own competitions only; the capability opens the
#: door, the scope check decides which rooms.
ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    Roles.ADMIN: ALL_CAPS,
    Roles.ORGANIZER: frozenset({
        Caps.CREATE_MATCH,
        Caps.SCORE_MATCH,
        Caps.COMMENTATE,
        Caps.CREATE_TEAM,
        Caps.MANAGE_PLAYERS,
        Caps.CREATE_TOURNAMENT,
        Caps.MANAGE_TOURNAMENT,
        Caps.DELETE_TOURNAMENT,
        Caps.MANAGE_UMPIRES,
        Caps.MANAGE_COMMENTATORS,
        Caps.MANAGE_RULES,
    }),
    Roles.TEAM_OWNER: frozenset({Caps.CREATE_TEAM}),
    # An umpire scores only the matches an organizer assigned them, which the
    # per-match assignment grants — not this capability.
    Roles.UMPIRE: frozenset(),
    Roles.COMMENTATOR: frozenset({Caps.COMMENTATE}),
    Roles.PLAYER: frozenset(),
    Roles.GENERAL_USER: frozenset(),
}

#: Every account starts here. A role is something an admin grants, never
#: something a stranger selects for themselves at sign-up.
DEFAULT_SIGNUP_ROLE = Roles.GENERAL_USER

#: Roles whose holders act inside somebody else's competition, so their access
#: comes from an assignment rather than from the role itself.
ASSIGNMENT_SCOPED_ROLES = frozenset({Roles.UMPIRE, Roles.COMMENTATOR})


def is_admin(role: str) -> bool:
    return role == Roles.ADMIN


def has_capability(role: str, cap: str) -> bool:
    return cap in ROLE_CAPABILITIES.get(role, frozenset())


def capabilities_for(role: str) -> list[str]:
    """Sorted capabilities, handed to the client so the UI can hide what the
    server would refuse. The UI is a convenience; the server is the authority."""
    return sorted(ROLE_CAPABILITIES.get(role, frozenset()))
