"""Team CRUD + roster membership.

Reads are public. Creating a team needs ``team.create`` and records the owner;
deleting or editing a team's roster needs ownership (or admin).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.deps import (
    get_ownership_repo,
    get_photo_service,
    get_roster_service,
    get_social_service,
    get_stats_service,
    require_admin,
    require_capability,
    require_team_owner,
)
from app.core.permissions import Caps
from app.repositories.ownership_repository import OwnershipRepository
from app.repositories.user_repository import UserRecord
from app.schemas.roster import AddMemberRequest, TeamCreate, TeamDTO
from app.schemas.stats import TeamStatsDTO
from app.services.photo_service import PhotoError, PhotoService
from app.services.roster_service import RosterError, RosterNotFound, RosterService
from app.services.stats_service import StatsService

router = APIRouter(prefix="/teams", tags=["teams"])


def _with_photos(teams: list[TeamDTO], photos: PhotoService) -> list[TeamDTO]:
    """Flag which teams have a logo and which members have a photo (batched)."""
    team_have = photos.present("team", [t.id for t in teams])
    member_have = photos.present("player", [m.player_id for t in teams for m in t.members])
    for t in teams:
        t.has_photo = t.id in team_have
        for m in t.members:
            m.has_photo = m.player_id in member_have
    return teams


@router.post("", response_model=TeamDTO, status_code=201)
def create_team(
    req: TeamCreate,
    svc: RosterService = Depends(get_roster_service),
    user: UserRecord = Depends(require_capability(Caps.CREATE_TEAM)),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    social=Depends(get_social_service),
):
    team = svc.create_team(req)
    owners.set_owner("team", team.id, user.id)
    social.record(user, "team", f"created team {team.name}", f"#/team/{team.id}")
    return team


@router.get("", response_model=list[TeamDTO])
def list_teams(
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
):
    return _with_photos(svc.list_teams(), photos)


@router.get("/{team_id}", response_model=TeamDTO)
def get_team(
    team_id: str,
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
):
    try:
        team = svc.get_team(team_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="team not found")
    return _with_photos([team], photos)[0]


@router.delete("/{team_id}", status_code=204)
def delete_team(
    team_id: str,
    svc: RosterService = Depends(get_roster_service),
    _user: UserRecord = Depends(require_admin),  # deleting is admin-only
    owners: OwnershipRepository = Depends(get_ownership_repo),
    photos: PhotoService = Depends(get_photo_service),
):
    try:
        svc.delete_team(team_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="team not found")
    owners.delete("team", team_id)
    photos.delete("team", team_id)  # tidy up the logo too


@router.post("/{team_id}/members", response_model=TeamDTO)
def add_member(
    team_id: str,
    req: AddMemberRequest,
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
    _user: UserRecord = Depends(require_team_owner),
):
    try:
        team = svc.add_member(team_id, req)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="team not found")
    except RosterError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _with_photos([team], photos)[0]


@router.delete("/{team_id}/members/{player_id}", response_model=TeamDTO)
def remove_member(
    team_id: str,
    player_id: str,
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
    _user: UserRecord = Depends(require_team_owner),
):
    try:
        team = svc.remove_member(team_id, player_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="team not found")
    return _with_photos([team], photos)[0]


# ----- team logo ------------------------------------------------------------
@router.post("/{team_id}/photo", status_code=204)
async def upload_team_logo(
    team_id: str,
    file: UploadFile = File(...),
    svc: RosterService = Depends(get_roster_service),
    photos: PhotoService = Depends(get_photo_service),
    _user: UserRecord = Depends(require_team_owner),
):
    try:
        svc.get_team(team_id)
    except RosterNotFound:
        raise HTTPException(status_code=404, detail="team not found")
    data = await file.read()
    try:
        photos.save("team", team_id, file.content_type, data)
    except PhotoError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/{team_id}/photo", status_code=204)
def delete_team_logo(
    team_id: str,
    photos: PhotoService = Depends(get_photo_service),
    _user: UserRecord = Depends(require_team_owner),
):
    photos.delete("team", team_id)


@router.get("/{team_id}/photo")
def get_team_logo(team_id: str, photos: PhotoService = Depends(get_photo_service)):
    photo = photos.get("team", team_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="no logo")
    return Response(content=photo.data, media_type=photo.content_type, headers={"Cache-Control": "no-cache"})


@router.get("/{team_id}/stats", response_model=TeamStatsDTO)
def team_stats(team_id: str, stats: StatsService = Depends(get_stats_service)):
    result = stats.team_stats(team_id)
    if result is None:
        raise HTTPException(status_code=404, detail="team not found")
    return result
