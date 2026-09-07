"""Unified search across players, teams, tournaments, and (when signed in) members."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_optional_user,
    get_photo_service,
    get_roster_service,
    get_tournament_service,
    get_user_repo,
    get_venue_service,
)
from app.repositories.user_repository import UserRecord, UserRepository
from app.schemas.search import SearchResults
from app.schemas.user import PublicUserDTO
from app.services.photo_service import PhotoService
from app.services.roster_service import RosterService
from app.services.tournament_service import TournamentService
from app.services.venue_service import VenueService

router = APIRouter(tags=["search"])

_LIMIT = 8


@router.get("/search", response_model=SearchResults)
def search(
    q: str = Query(min_length=1, max_length=80),
    roster: RosterService = Depends(get_roster_service),
    tournaments: TournamentService = Depends(get_tournament_service),
    repo: UserRepository = Depends(get_user_repo),
    photos: PhotoService = Depends(get_photo_service),
    venues: VenueService = Depends(get_venue_service),
    user: Optional[UserRecord] = Depends(get_optional_user),
):
    ql = q.strip().lower()
    players = [p for p in roster.list_players() if ql in p.name.lower()][:_LIMIT]
    teams = [
        t for t in roster.list_teams()
        if ql in t.name.lower() or (t.location and ql in t.location.lower())
    ][:_LIMIT]
    tours = [t for t in tournaments.list() if ql in t.name.lower()][:_LIMIT]
    found_venues = venues.search(q, limit=_LIMIT)

    members: list[PublicUserDTO] = []
    if user is not None:  # contact details only for signed-in members
        members = [
            PublicUserDTO(
                id=u.id, full_name=u.full_name, username=u.username, role=u.role,
                role_code=u.role_code, user_code=u.user_code, mobile_no=u.mobile_no,
                is_verified=u.is_verified,
            )
            for u in repo.list_users()
            if ql in u.full_name.lower() or ql in u.username.lower()
        ][:_LIMIT]

    # flag uploaded pictures so the UI shows photos, not just initials
    p_have = photos.present("player", [p.id for p in players])
    for p in players:
        p.has_photo = p.id in p_have
    t_have = photos.present("team", [t.id for t in teams])
    for t in teams:
        t.has_photo = t.id in t_have
    if members:
        u_have = photos.present("user", [u.id for u in members])
        for u in members:
            u.has_photo = u.id in u_have

    return SearchResults(
        query=q, players=players, teams=teams, tournaments=tours,
        members=members, venues=found_venues,
    )
