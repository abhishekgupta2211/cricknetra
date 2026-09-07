"""Fielding-event DTOs — dropped catches, runs saved, misfields."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FieldingEventCreate(BaseModel):
    fielder: str = Field(..., min_length=1)
    kind: str = "drop"  # drop | save | misfield (validated in the service)
    runs: int = Field(default=0, ge=0)  # saved (save) or conceded (misfield)
    innings: int = Field(default=1, ge=1)
    bowler: Optional[str] = None  # for a drop: the bowler denied the wicket
    batter: Optional[str] = None  # for a drop: the batter let off
    note: Optional[str] = Field(default=None, max_length=200)
    over_ball: Optional[str] = None


class FieldingEventDTO(BaseModel):
    id: str
    match_id: str
    innings: int
    fielder: str
    kind: str
    runs: int
    bowler: Optional[str] = None
    batter: Optional[str] = None
    note: Optional[str] = None
    over_ball: Optional[str] = None
    when: str
