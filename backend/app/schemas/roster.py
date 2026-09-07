"""Players, teams, and rosters — DTOs."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    batting_style: Optional[str] = None  # e.g. "Right-hand bat" / "Left-hand bat"
    bowling_style: Optional[str] = None  # e.g. "Right-arm fast", "Left-arm orthodox"


class PlayerUpdate(BaseModel):
    """Partial update — only fields that are sent (non-null) are changed."""

    name: Optional[str] = None
    phone: Optional[str] = None
    batting_style: Optional[str] = None
    bowling_style: Optional[str] = None


class PlayerDTO(BaseModel):
    id: str
    name: str
    code: str = ""  # stable roster code (e.g. "P00012") to tell same-named players apart
    phone: Optional[str] = None
    batting_style: Optional[str] = None
    bowling_style: Optional[str] = None
    has_photo: bool = False  # set by the route; drives photo-vs-initials in the UI
    claimed_by: Optional[str] = None  # user id that claimed this roster player (None = unclaimed)


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1)
    location: Optional[str] = None


class TeamMemberDTO(BaseModel):
    player_id: str
    name: str
    code: str = ""
    is_captain: bool = False
    has_photo: bool = False  # set by the route


class TeamDTO(BaseModel):
    id: str
    name: str
    location: Optional[str] = None
    members: list[TeamMemberDTO] = []
    has_photo: bool = False  # team logo; set by the route


class AddMemberRequest(BaseModel):
    """Add an existing player by id, or create one on the fly by name."""

    player_id: Optional[str] = None
    name: Optional[str] = None
    is_captain: bool = False
