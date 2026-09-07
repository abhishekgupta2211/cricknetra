"""Preset summary DTO. Full rule details are returned as the domain `MatchRules`."""

from __future__ import annotations

from pydantic import BaseModel


class PresetSummary(BaseModel):
    id: str
    name: str
    description: str
    players_per_side: int
    overs_per_innings: int
    balls_per_over: int
    ball_type: str
    last_man_stands: bool
