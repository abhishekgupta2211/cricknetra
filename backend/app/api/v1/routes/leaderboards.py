"""Cross-player leaderboards — optionally scoped by place and time window."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_stats_service
from app.schemas.stats import Leaderboards
from app.services.stats_service import StatsService

router = APIRouter(prefix="/leaderboards", tags=["stats"])

_WINDOWS = {"all", "week", "month", "year"}


def _window_since(window: str) -> Optional[datetime]:
    """Lower-bound cutoff for a named window (None = all-time)."""
    now = datetime.now(timezone.utc)
    if window == "week":
        return now - timedelta(days=7)
    if window == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if window == "year":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


@router.get("", response_model=Leaderboards)
def leaderboards(
    window: str = Query(default="all", description="all | week | month | year"),
    location: Optional[str] = Query(default=None, description="filter to matches a team from here played in"),
    since: Optional[datetime] = Query(default=None, description="advanced: explicit lower-bound date (overrides window)"),
    min_innings: int = Query(default=1, ge=0, description="minimum innings for average/SR/econ boards"),
    limit: int = Query(default=10, ge=1, le=100),
    svc: StatsService = Depends(get_stats_service),
):
    window = window if window in _WINDOWS else "all"
    cutoff = since if since is not None else _window_since(window)
    result = svc.leaderboards(min_innings=min_innings, limit=limit, since=cutoff, location=location)
    result.window = "custom" if since is not None else window
    return result
