"""\"Looking For\" board DTOs."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LookingForCreate(BaseModel):
    kind: str  # player | team | match (validated in the service)
    text: str = Field(..., min_length=1, max_length=500)
    location: Optional[str] = None
    role: Optional[str] = None


class LookingForDTO(BaseModel):
    id: str
    author_id: str
    author_name: str
    kind: str
    text: str
    location: Optional[str] = None
    role: Optional[str] = None
    status: str
    when: str
    mine: bool = False  # set per-viewer: is the current user the author?
