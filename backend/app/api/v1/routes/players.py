"""Player CRUD."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.api.deps import (
    get_award_repo,
    get_current_active_user,
    get_ownership_repo,
    get_photo_service,
    get_roster_service,
    get_stats_service,
    get_tournament_service,
    require_admin,
    require_capability,
)
from app.core.permissions import Caps, has_capability, is_admin
from app.repositories.ownership_repository import OwnershipRepository
from app.repositories.user_repository import UserRecord
from app.schemas.roster import PlayerCreate, PlayerDTO, PlayerUpdate
from app.schemas.tournament import PlayerTournamentDTO
from app.schemas.stats import (
    AwardDTO,
    PlayerHistoryDTO,
    PlayerInsightsDTO,
    PlayerSplitsDTO,
    PlayerStatsDTO,
)
from app.services.photo_service import PhotoError, PhotoService
from app.services.roster_service import RosterError, RosterNotFound, RosterService
from app.services.stats_service import StatsService
from app.services.tournament_service import TournamentService

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/{player_id}/stats", response_model=PlayerStatsDTO)
def player_stats(
    player_id: str,
    roster: RosterService = Depends(get_roster_service),
    stats: StatsService = Depends(get_stats_service),
):
    try:
        player = roster.get_player(player_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="player not found")
    batting, bowling, fielding, recent = stats.aggregate(player_id)
    return PlayerStatsDTO(
        player=player, batting=batting, bowling=bowling, fielding=fielding, recent=recent
    )


@router.get("/{player_id}/history", response_model=PlayerHistoryDTO)
def player_history(player_id: str, stats: StatsService = Depends(get_stats_service)):
    """A player's whole career: every match they played with their own line in
    it, plus their record broken down by tournament, by year and by side.

    Public, like the rest of a player's record — a career is meant to be shown.
    """
    history = stats.history(player_id)
    if history is None:
        raise HTTPException(status_code=404, detail="player not found")
    return history


@router.get("/{player_id}/tournaments", response_model=list[PlayerTournamentDTO])
def player_tournaments(
    player_id: str,
    roster: RosterService = Depends(get_roster_service),
    tournaments: TournamentService = Depends(get_tournament_service),
):
    """The competitions this player is registered in, and for whom.

    History answers "where have they played"; this answers "where are they
    entered", which is a different and earlier question. A player picked for a
    squad exists in that competition from the moment the organizer enters them,
    and until now nothing on the platform said so — a player waiting for their
    first game had to ask an organizer which cups they were even in.

    Public, like the rest of a player's record: a squad list is announced, not
    confidential, and every registration here is already readable through
    ``GET /tournaments/{id}/squads``.
    """
    try:
        roster.get_player(player_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="player not found")
    return tournaments.registrations_for_player(player_id)


@router.get("/{player_id}/awards", response_model=list[AwardDTO])
def player_awards(player_id: str, awards=Depends(get_award_repo)):
    """Match honours (MoM / best batter / best bowler) this player has won — public."""
    return awards.awards_for_player(player_id)


@router.get("/{player_id}/insights", response_model=PlayerInsightsDTO)
def player_insights(
    player_id: str,
    roster: RosterService = Depends(get_roster_service),
    stats: StatsService = Depends(get_stats_service),
):
    try:
        player = roster.get_player(player_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="player not found")
    batting, bowling = stats.insights(player_id)
    return PlayerInsightsDTO(player=player, batting=batting, bowling=bowling)


@router.get("/{player_id}/splits", response_model=PlayerSplitsDTO)
def player_splits(
    player_id: str,
    stats: StatsService = Depends(get_stats_service),
):
    """Career broken out by format (T20/ODI/…), by ball type, and vs pace/spin."""
    dto = stats.splits(player_id)
    if dto is None:
        raise HTTPException(status_code=404, detail="player not found")
    return dto


@router.post("", response_model=PlayerDTO, status_code=201)
def create_player(
    req: PlayerCreate,
    svc: RosterService = Depends(get_roster_service),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    user: UserRecord = Depends(require_capability(Caps.CREATE_TEAM)),
):
    dto = svc.create_player(req)
    # Record the creator, as matches, teams and tournaments already do. Without
    # it a player row belongs to nobody, and "may create players" had to stand
    # in for "may edit this one" — which let any organizer rewrite anybody.
    owners.set_owner("player", dto.id, user.id)
    return dto


def _require_player_manager(
    player_id: str,
    user: UserRecord = Depends(get_current_active_user),
    svc: RosterService = Depends(get_roster_service),
    owners: OwnershipRepository = Depends(get_ownership_repo),
) -> UserRecord:
    """Edit a player: the admin, whoever added them, or the person themselves.

    Holding CREATE_TEAM says you may add players to your own roster, not that
    you may rewrite somebody else's — including the phone number organizers use
    to reach them.
    """
    if is_admin(user.role):
        return user
    try:
        player = svc.get_player(player_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="player not found")
    if str(getattr(player, "claimed_by", "") or "") == str(user.id):
        return user
    owner = owners.get_owner("player", player_id)
    if owner is not None and str(owner) == str(user.id):
        return user
    # An unowned player predates ownership being recorded; only a roster
    # manager may touch those, never everybody.
    if owner is None and has_capability(user.role, Caps.CREATE_TEAM):
        return user
    raise HTTPException(
        status_code=403,
        detail="This player was added by somebody else.",
    )


@router.get("", response_model=list[PlayerDTO])
def list_players(
    q: Optional[str] = Query(default=None, max_length=80, description="name search"),
    limit: Optional[int] = Query(default=None, ge=1, le=500),
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
):
    """The roster. `q` filters by name and `limit` caps the result.

    Both were previously ignored, so a client asking for three players got the
    whole roster and quietly rendered all of it.
    """
    dtos = svc.list_players()
    if q:
        needle = q.strip().lower()
        dtos = [d for d in dtos if needle in d.name.lower()]
    if limit is not None:
        dtos = dtos[:limit]
    have = photos.present("player", [d.id for d in dtos])
    for d in dtos:
        d.has_photo = d.id in have
    return dtos


# ----- claim a roster player (the unverified-stub → account model) -----------
# Registered before /{player_id} so "claimable"/"mine" aren't read as a player id.
@router.get("/claimable", response_model=list[PlayerDTO])
def claimable_players(
    user: UserRecord = Depends(get_current_active_user),
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
):
    """Unclaimed roster players whose phone matches your mobile — likely you."""
    dtos = svc.claimable(user.mobile_no)
    have = photos.present("player", [d.id for d in dtos])
    for d in dtos:
        d.has_photo = d.id in have
    return dtos


@router.get("/mine", response_model=list[PlayerDTO])
def my_players(
    user: UserRecord = Depends(get_current_active_user),
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
):
    """Roster players you've claimed (your on-field identities)."""
    dtos = svc.my_players(user.id)
    have = photos.present("player", [d.id for d in dtos])
    for d in dtos:
        d.has_photo = d.id in have
    return dtos


@router.post("/{player_id}/claim", response_model=PlayerDTO)
def claim_player(
    player_id: str,
    user: UserRecord = Depends(get_current_active_user),
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
):
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Verify your mobile number before claiming a profile.")
    try:
        dto = svc.claim(player_id, user_id=user.id, mobile=user.mobile_no,
                        is_verified=user.is_verified, is_admin=is_admin(user.role))
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="player not found")
    except RosterError as e:
        raise HTTPException(status_code=409, detail=str(e))
    dto.has_photo = photos.has("player", player_id)
    return dto


@router.get("/{player_id}", response_model=PlayerDTO)
def get_player(
    player_id: str,
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
):
    try:
        dto = svc.get_player(player_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="player not found")
    dto.has_photo = photos.has("player", player_id)
    return dto


@router.patch("/{player_id}", response_model=PlayerDTO)
def update_player(
    player_id: str,
    req: PlayerUpdate,
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
    _user: UserRecord = Depends(_require_player_manager),
):
    try:
        dto = svc.update_player(player_id, req)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="player not found")
    dto.has_photo = photos.has("player", player_id)
    return dto


@router.delete("/{player_id}", status_code=204)
def delete_player(
    player_id: str,
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
    _user: UserRecord = Depends(require_admin),  # deleting is admin-only
):
    try:
        svc.delete_player(player_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="player not found")
    photos.delete("player", player_id)  # tidy up the picture too


# ----- player picture -------------------------------------------------------
@router.post("/{player_id}/photo", status_code=204)
async def upload_player_photo(
    player_id: str,
    file: UploadFile = File(...),
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
    _user: UserRecord = Depends(_require_player_manager),
):
    try:
        svc.get_player(player_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="player not found")
    data = await file.read()
    try:
        photos.save("player", player_id, file.content_type, data)
    except PhotoError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/{player_id}/photo", status_code=204)
def delete_player_photo(
    player_id: str,
    photos: PhotoService = Depends(get_photo_service),
    _user: UserRecord = Depends(_require_player_manager),
):
    photos.delete("player", player_id)


@router.get("/{player_id}/photo")
def get_player_photo(player_id: str, photos: PhotoService = Depends(get_photo_service)):
    photo = photos.get("player", player_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="no photo")
    return Response(content=photo.data, media_type=photo.content_type, headers={"Cache-Control": "no-cache"})
