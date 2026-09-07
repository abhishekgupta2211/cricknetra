"""An organizer's umpires and commentators, per tournament.

`match_officials` answers "may this umpire score match 7". This answers the
question before it: who is on the staff of a competition at all. An umpire
Organizer A adds does not become available to Organizer B.

Every route here is scoped to the competition in the URL, and the scope is
decided from the database rather than from anything the caller sent:

* reading the staff list needs ``require_tournament_staffer`` — the owning
  organizer, somebody assigned to it, or the admin;
* changing it needs ``require_tournament_owner`` — the owning organizer or the
  admin, so an assigned umpire can see the team sheet without editing it;
* ``/tournaments/mine/staffing`` takes the person from the token, never from a
  query parameter, so nobody enumerates somebody else's assignments.

Changing the id in the URL is therefore not a way in: the guard looks up who
owns *that* tournament before the handler runs.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import (
    get_current_active_user,
    get_staff_service,
    get_tournament_service,
    require_tournament_owner,
    require_tournament_staffer,
)
from app.repositories.tournament_staff_repository import COMMENTATOR, UMPIRE
from app.repositories.user_repository import UserRecord
from app.schemas.org import StaffAdd, StaffDTO
from app.schemas.roster import PlayerDTO
from app.services.staff_service import StaffError, StaffService
from app.services.tournament_service import TournamentNotFound, TournamentService

router = APIRouter(prefix="/tournaments", tags=["tournament-staff"])


# These two shapes exist only as this router's replies — `StaffDTO` in
# app/schemas/org.py is the shared one. Keeping them here rather than widening
# StaffDTO stops "who is on this tournament" and "which tournaments am I on"
# from turning into one half-filled model that answers neither well.
class StaffingDTO(BaseModel):
    """One competition the caller is staff on, for their own dashboard."""

    tournament_id: str
    tournament_name: str = ""
    staff_role: str = ""
    is_active: bool = True


class StaffActiveUpdate(BaseModel):
    """Stand a staff member down for this tournament, or bring them back."""

    is_active: bool


class TournamentPlayerDTO(BaseModel):
    """One player registered in this competition, with the team they play for.

    ``GET /squads`` returns the same people grouped by team, which a "who is
    playing in this competition" screen then has to unpick and de-duplicate;
    this is that list already flattened.
    """

    team_id: str
    team_name: str
    player: PlayerDTO


def _http(err: StaffError) -> HTTPException:
    """One translation point, so every refusal reaches the client with the
    reason the service gave rather than a generic 400."""
    return HTTPException(status_code=err.status_code, detail=err.detail)


# --------------------------------------------------------------------------- #
# The caller's own assignments
# --------------------------------------------------------------------------- #
# Declared before the "/{tournament_id}/…" routes: a literal path should never
# depend on a competition happening not to be called "mine".
@router.get("/mine/staffing", response_model=list[StaffingDTO])
def my_staffing(
    staff_role: Optional[str] = Query(default=None, description="umpire | commentator"),
    user: UserRecord = Depends(get_current_active_user),
    svc: StaffService = Depends(get_staff_service),
):
    """The competitions *you* are an umpire or commentator on.

    The person is taken from the token. There is deliberately no ``user_id``
    parameter: one would turn a dashboard into a way of reading which
    tournaments anybody else works on.
    """
    try:
        entries = svc.staffing_for(user.id, staff_role)
    except StaffError as e:
        raise _http(e)
    return [
        StaffingDTO(
            tournament_id=e.tournament_id,
            tournament_name=e.tournament_name,
            staff_role=e.staff_role,
            is_active=e.is_active,
        )
        for e in entries
    ]


# --------------------------------------------------------------------------- #
# A tournament's staff
# --------------------------------------------------------------------------- #
@router.get("/{tournament_id}/staff", response_model=list[StaffDTO])
def list_staff(
    tournament_id: str,
    staff_role: Optional[str] = Query(default=None, description="umpire | commentator"),
    _user: UserRecord = Depends(require_tournament_staffer),
    svc: StaffService = Depends(get_staff_service),
):
    """Who works this competition — readable by its organizer, by the people
    assigned to it, and by the admin. Another organizer gets a 403."""
    try:
        return svc.list_for_tournament(tournament_id, staff_role)
    except StaffError as e:
        raise _http(e)


@router.post("/{tournament_id}/staff/umpires", response_model=StaffDTO, status_code=201)
def add_umpire(
    tournament_id: str,
    req: StaffAdd,
    user: UserRecord = Depends(require_tournament_owner),
    svc: StaffService = Depends(get_staff_service),
):
    """Add an umpire to this competition, promoting a roleless account on the
    way in. Somebody who already holds another role is refused (409) rather
    than quietly demoted."""
    try:
        return svc.add(tournament_id, req.user_id, UMPIRE, added_by=user.id)
    except StaffError as e:
        raise _http(e)


@router.post("/{tournament_id}/staff/commentators", response_model=StaffDTO, status_code=201)
def add_commentator(
    tournament_id: str,
    req: StaffAdd,
    user: UserRecord = Depends(require_tournament_owner),
    svc: StaffService = Depends(get_staff_service),
):
    """Add a commentator to this competition. Same promotion rule as umpires."""
    try:
        return svc.add(tournament_id, req.user_id, COMMENTATOR, added_by=user.id)
    except StaffError as e:
        raise _http(e)


@router.delete("/{tournament_id}/staff/{staff_role}/{user_id}", status_code=204)
def remove_staff(
    tournament_id: str,
    staff_role: str,
    user_id: str,
    user: UserRecord = Depends(require_tournament_owner),
    svc: StaffService = Depends(get_staff_service),
):
    """Take somebody off *this* competition's staff.

    Their account and their work on other organizers' tournaments are left
    alone — this is "not on my competition", not "no longer an umpire".
    """
    try:
        svc.remove(tournament_id, user_id, staff_role, actor_id=user.id)
    except StaffError as e:
        raise _http(e)


@router.patch("/{tournament_id}/staff/{staff_role}/{user_id}", response_model=StaffDTO)
def set_staff_active(
    tournament_id: str,
    staff_role: str,
    user_id: str,
    req: StaffActiveUpdate,
    _user: UserRecord = Depends(require_tournament_owner),
    svc: StaffService = Depends(get_staff_service),
):
    """Activate or deactivate a staff member within this competition only.

    A deactivated entry stops counting as staff everywhere the scope check
    asks, but survives so the organizer can bring them back.
    """
    try:
        return svc.set_active(tournament_id, user_id, staff_role, req.is_active)
    except StaffError as e:
        raise _http(e)


# --------------------------------------------------------------------------- #
# A tournament's players
# --------------------------------------------------------------------------- #
@router.get("/{tournament_id}/players", response_model=list[TournamentPlayerDTO])
def list_tournament_players(
    tournament_id: str,
    _user: UserRecord = Depends(require_tournament_staffer),
    svc: TournamentService = Depends(get_tournament_service),
):
    """Everybody registered across this competition's squads, in one call.

    Scoped like the rest of the working view: the owning organizer, the staff
    assigned to it, and the admin. The public, per-team view of the same
    registrations stays at ``GET /tournaments/{id}/squads``.
    """
    try:
        squads = svc.team_squads(tournament_id)
    except TournamentNotFound:
        raise HTTPException(status_code=404, detail="tournament not found")
    return [
        TournamentPlayerDTO(team_id=squad.team_id, team_name=squad.team_name, player=player)
        for squad in squads
        for player in squad.players
    ]
