"""Head-to-head player comparison."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_stats_service
from app.schemas.stats import CompareDTO
from app.services.stats_service import StatsService

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/compare", response_model=CompareDTO)
def compare(
    player_a: str = Query(...),
    player_b: str = Query(...),
    svc: StatsService = Depends(get_stats_service),
):
    result = svc.compare(player_a, player_b)
    if result is None:
        raise HTTPException(status_code=404, detail="player not found")
    return result
