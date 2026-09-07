"""Request bodies for scoring actions."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BallAction(str, Enum):
    runs = "runs"
    wide = "wide"
    no_ball = "no_ball"
    bye = "bye"
    leg_bye = "leg_bye"
    wicket = "wicket"


class BallRequest(BaseModel):
    """One delivery. `value` is interpreted per action:

    - runs    : runs off the bat
    - wide    : extra runs physically run (penalty added automatically)
    - no_ball : runs off the bat (penalty added automatically)
    - bye     : byes run
    - leg_bye : leg-byes run
    - wicket  : runs off the bat on the dismissal delivery (usually 0)
    """

    action: BallAction
    value: int = Field(default=0, ge=0)
    dismissal: Optional[str] = Field(
        default=None, description="DismissalType value, required when action=wicket"
    )
    batter_out: str = Field(default="striker", pattern="^(striker|non_striker)$")
    fielder: Optional[str] = None
    wagon_x: Optional[float] = Field(default=None, ge=-1, le=1)
    wagon_y: Optional[float] = Field(default=None, ge=-1, le=1)
    # optional pitch-map (bowling) marker: line x (-1..1) + length y (0..1) + speed
    pitch_x: Optional[float] = Field(default=None, ge=-1, le=1)
    pitch_y: Optional[float] = Field(default=None, ge=0, le=1)
    speed: Optional[float] = Field(default=None, ge=0, le=200)


class SetBowlerRequest(BaseModel):
    bowler: str = Field(..., min_length=1)
