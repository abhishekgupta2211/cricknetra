"""Tournaments — create, fixtures, points table, and starting fixtures.

Reads are public. Creating a tournament needs ``tournament.create`` and records
the owner; every write *inside* a competition — settings, squads, fixtures,
deletion — goes through ``ScopeService``, so holding the capability opens the
door and ownership decides which competition.

The public detail carries ``is_manager``, computed the same way, so a client
can tell whether to offer the management controls without probing a write.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import (
    get_audit_service,
    get_current_active_user,
    get_optional_user,
    get_ownership_repo,
    get_scope_service,
    get_social_service,
    get_staff_repo,
    get_tournament_repo,
    get_tournament_service,
    require_capability,
    require_tournament_owner,
)
from app.core.permissions import Caps
from app.repositories.audit_repository import AuditActions
from app.repositories.ownership_repository import OwnershipRepository
from app.repositories.tournament_repository import TournamentRepository
from app.repositories.user_repository import UserRecord
from app.schemas.tournament import (
    FixtureDTO,
    SquadRegisterRequest,
    StartFixtureRequest,
    TeamSquadDTO,
    TournamentCreate,
    TournamentDetailDTO,
    TournamentDTO,
    TournamentSettings,
)
from app.services.roster_service import RosterNotFound
from app.services.scope_service import ScopeError, ScopeService
from app.services.tournament_service import (
    FixtureError,
    InvalidTournament,
    SquadConflict,
    TournamentNotFound,
    TournamentService,
)

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


def _as_viewer(
    detail: TournamentDetailDTO,
    user: Optional[UserRecord],
    scope: ScopeService,
) -> TournamentDetailDTO:
    """Stamp the viewer-aware ``is_manager`` flag onto a tournament detail.

    Decided by ``ScopeService`` from the authenticated caller — the same
    service ``require_tournament_owner`` asks, so the flag cannot drift from
    what the server will actually allow. An anonymous reader gets ``False``
    rather than a 401: the detail page is public, and "can I manage this" has
    an honest answer for a signed-out visitor.

    A deactivated account is excluded here too, because the guards run through
    ``get_current_active_user`` and would refuse it — telling a stood-down
    organizer they may manage a competition is the same drift in the other
    direction.
    """
    can_manage = (
        user is not None
        and getattr(user, "is_active", True)
        and scope.manages_tournament(user, detail.id)
    )
    detail.is_manager = bool(can_manage)
    return detail


@router.post("", response_model=TournamentDetailDTO, status_code=201)
def create_tournament(
    req: TournamentCreate,
    svc: TournamentService = Depends(get_tournament_service),
    user: UserRecord = Depends(require_capability(Caps.CREATE_TOURNAMENT)),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    social=Depends(get_social_service),
    scope: ScopeService = Depends(get_scope_service),
):
    try:
        detail = svc.create(req)
    except InvalidTournament as e:
        raise HTTPException(status_code=400, detail=str(e))
    owners.set_owner("tournament", detail.id, user.id)
    social.record(user, "tournament", f"created the {detail.name} {detail.format.replace('_', ' ')}", f"/t/{detail.id}")
    # Read back through ScopeService rather than assuming — the ownership row
    # written a line above is the fact the flag has to reflect.
    return _as_viewer(detail, user, scope)


@router.patch("/{tournament_id}/settings", response_model=TournamentDetailDTO)
def update_tournament_settings(
    tournament_id: str,
    req: TournamentSettings,
    svc: TournamentService = Depends(get_tournament_service),
    user: UserRecord = Depends(require_tournament_owner),
    scope: ScopeService = Depends(get_scope_service),
):
    """Toggle tournament-wide DLS rain rules (applies to every fixture started after).

    Owner-scoped: holding CREATE_TOURNAMENT says you may run competitions, not
    that you may change somebody else's rain rules.
    """
    try:
        detail = svc.set_dls(tournament_id, req.dls_enabled)
    except TournamentNotFound:
        raise HTTPException(status_code=404, detail="tournament not found")
    return _as_viewer(detail, user, scope)


@router.get("", response_model=list[TournamentDTO])
def list_tournaments(svc: TournamentService = Depends(get_tournament_service)):
    """The public board — anybody may browse what is being played."""
    return svc.list()


# Registered before "/{tournament_id}" so "mine" is not read as an id.
@router.get("/mine", response_model=list[TournamentDTO])
def my_tournaments(
    svc: TournamentService = Depends(get_tournament_service),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    user: UserRecord = Depends(get_current_active_user),
):
    """The competitions the caller owns — an organizer's own desk.

    A separate endpoint rather than a filter on the public list, because the
    owner is read from the token: there is no id in the request for a client
    to swap for somebody else's.
    """
    owned = set(owners.list_by_owner(str(user.id), "tournament"))
    return [t for t in svc.list() if str(t.id) in owned]


@router.get("/{tournament_id}", response_model=TournamentDetailDTO)
def get_tournament(
    tournament_id: str,
    svc: TournamentService = Depends(get_tournament_service),
    user: Optional[UserRecord] = Depends(get_optional_user),
    scope: ScopeService = Depends(get_scope_service),
):
    """A competition's board — public, so anybody may read it.

    The optional-user dependency is what makes ``is_manager`` possible without
    closing the page: a signed-in organizer is told whether this one is theirs,
    an anonymous visitor is told ``False``, and neither is refused. Before this
    the client had to find out by firing a management request and reading the
    403, which every non-owner's browser did on every visit.
    """
    try:
        detail = svc.get_detail(tournament_id)
    except TournamentNotFound:
        raise HTTPException(status_code=404, detail="tournament not found")
    return _as_viewer(detail, user, scope)


@router.delete("/{tournament_id}", status_code=204)
def delete_tournament(
    tournament_id: str,
    svc: TournamentService = Depends(get_tournament_service),
    user: UserRecord = Depends(require_tournament_owner),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    staff=Depends(get_staff_repo),
    audit=Depends(get_audit_service),
):
    """Remove a competition — its organizer, or the admin.

    Owner-scoped rather than admin-only: an organizer who created a cup by
    mistake has to be able to take it back down without opening a support
    ticket, and ``require_tournament_owner`` is already the guard that lets
    them do that to *theirs* and refuses somebody else's.

    Everything that hangs off the competition goes with it — the service drops
    the squads, the repository drops the fixtures, and the staff entries and
    the tournament's ownership row are cleared here — so nothing is left
    pointing at an id that no longer resolves. The one thing deliberately kept
    is the ownership row of each match started from a fixture: those scorecards
    outlive the competition, and their row is the only remaining fact that says
    whose they are once the fixtures are gone.
    """
    rec = svc.repo.get(tournament_id)
    try:
        svc.delete(tournament_id)
    except TournamentNotFound:
        raise HTTPException(status_code=404, detail="tournament not found")
    owners.delete("tournament", tournament_id)
    staff.remove_tournament(tournament_id)
    audit.record(
        user.id, AuditActions.TOURNAMENT_DELETED, "tournament", tournament_id,
        f"deleted {rec.name}" if rec is not None else "deleted",
    )


@router.post("/fixtures/{fixture_id}/start", response_model=FixtureDTO)
def start_fixture(
    fixture_id: str,
    req: StartFixtureRequest,
    svc: TournamentService = Depends(get_tournament_service),
    tournaments: TournamentRepository = Depends(get_tournament_repo),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    scope: ScopeService = Depends(get_scope_service),
    user: UserRecord = Depends(get_current_active_user),
):
    """Start the match for a fixture.

    Keyed by fixture rather than tournament, so the competition has to be
    looked up before its owner can be checked — otherwise any organizer could
    start another organizer's fixture just by knowing its id.
    """
    fixture = tournaments.get_fixture(fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="fixture not found")
    try:
        scope.require_tournament(user, fixture.tournament_id)
    except ScopeError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    try:
        dto = svc.start_fixture(fixture_id, req)
    except (FixtureError, RosterNotFound) as e:
        raise HTTPException(status_code=400, detail=str(e) or "could not start fixture")
    # Record the owner exactly as POST /matches does. Without this the match is
    # ownerless: the organizer's umpire-approval inbox (built from the matches
    # they own) stays empty, their scoring record reads zero, and deleting the
    # competition would orphan every scorecard in it.
    if dto.match_id:
        owners.set_owner("match", dto.match_id, user.id)
    return dto


# ----- per-tournament squads -----
@router.get("/{tournament_id}/squads", response_model=list[TeamSquadDTO])
def list_squads(tournament_id: str, svc: TournamentService = Depends(get_tournament_service)):
    try:
        return svc.team_squads(tournament_id)
    except TournamentNotFound:
        raise HTTPException(status_code=404, detail="tournament not found")


@router.post("/{tournament_id}/teams/{team_id}/squad", response_model=list[TeamSquadDTO])
def register_squad(
    tournament_id: str,
    team_id: str,
    req: SquadRegisterRequest,
    svc: TournamentService = Depends(get_tournament_service),
    _user: UserRecord = Depends(require_tournament_owner),
):
    try:
        return svc.register_player(tournament_id, team_id, req.player_id)
    except TournamentNotFound:
        raise HTTPException(status_code=404, detail="tournament not found")
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="player not found")
    except SquadConflict as e:
        raise HTTPException(status_code=409, detail=str(e))
    except InvalidTournament as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{tournament_id}/teams/{team_id}/squad/{player_id}", response_model=list[TeamSquadDTO])
def unregister_squad(
    tournament_id: str,
    team_id: str,
    player_id: str,
    svc: TournamentService = Depends(get_tournament_service),
    _user: UserRecord = Depends(require_tournament_owner),
):
    try:
        return svc.unregister_player(tournament_id, team_id, player_id)
    except TournamentNotFound:
        raise HTTPException(status_code=404, detail="tournament not found")
