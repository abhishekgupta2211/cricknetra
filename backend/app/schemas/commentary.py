"""Commentary DTOs."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CommentaryCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=280)


class CommentaryDTO(BaseModel):
    id: str
    author_name: str
    text: str
    when: str = ""


class BallFeedDTO(BaseModel):
    """One auto-generated ball-by-ball line."""

    innings: str
    over_ball: str
    kind: str
    runs: int = 0
    bowler: str = ""
    striker: str = ""
    text: str
    idx: int = 0          # this delivery's index within its innings (for edit/delete)
    editable: bool = False  # true only for the live innings
    free_hit: bool = False  # was THIS delivery a free hit (an edit must respect it)


class HighlightDTO(BaseModel):
    """One auto-generated highlight moment (from the ball log — no video)."""

    innings: str
    over_ball: str = ""
    kind: str            # wicket | six | four | fifty | hundred | bowling | innings | result
    title: str
    text: str
    team: Optional[str] = None
    importance: int = 1
    ts: Optional[float] = None  # wall-clock time of the moment (for video sync)
