"""Highlights hub API: a gallery of every match's clips, plus the signed-in
user's manageable matches — so clips can be added from one place (the in-app
Highlights section) instead of only the per-match scoring screen."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_user, get_match_service, get_ownership_repo
from app.core.permissions import is_admin
from app.repositories.ownership_repository import OwnershipRepository
from app.repositories.user_repository import UserRecord
from app.schemas.match import MatchHighlightsDTO, MatchSummaryDTO
from app.services.match_service import MatchService

router = APIRouter(tags=["highlights"])


@router.get("/highlights", response_model=list[MatchHighlightsDTO])
def all_highlights(svc: MatchService = Depends(get_match_service)):
    """Every highlight clip across all matches, grouped by match (public read)."""
    return svc.highlight_groups()


@router.get("/highlights/my-matches", response_model=list[MatchSummaryDTO])
def my_manageable_matches(
    user: UserRecord = Depends(get_current_active_user),
    svc: MatchService = Depends(get_match_service),
    owners: OwnershipRepository = Depends(get_ownership_repo),
):
    """Matches the signed-in user may attach clips to — their own (admins: all)."""
    summaries = svc.list_summaries()
    if is_admin(user.role):
        return summaries
    owned = set(owners.list_by_owner(user.id, "match"))
    return [s for s in summaries if s.id in owned]
