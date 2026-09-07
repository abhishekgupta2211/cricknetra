"""Format presets + full rule templates (for the future custom-rule builder)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_match_service
from app.domain.rules import MatchRules
from app.schemas.presets import PresetSummary
from app.services.match_service import MatchService

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("", response_model=list[PresetSummary])
def list_presets(svc: MatchService = Depends(get_match_service)):
    return svc.list_presets()


@router.get("/{format_id}", response_model=MatchRules)
def get_preset(format_id: str, svc: MatchService = Depends(get_match_service)):
    """Return the full editable rule template for a format (React rule-builder)."""
    try:
        return svc.get_preset_rules(format_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown format '{format_id}'")
