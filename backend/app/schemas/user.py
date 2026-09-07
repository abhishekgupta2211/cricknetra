"""User response schema (from the user-supplied ``user.py``).

``id`` is a string to match the rest of CricNetra's DTOs, and the password hash
is never serialized.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MemberRecords(BaseModel):
    """A member's activity tally (their "records")."""

    matches_scored: int = 0          # matches they created/scored
    matches_umpired: int = 0         # others' matches they officiated
    matches_commentated: int = 0     # matches they commentated
    tournaments_organized: int = 0
    teams_owned: int = 0


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    username: str
    mobile_no: str
    email: Optional[str] = None
    user_code: str
    role_code: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    # Filled in by the route from the role's policy so the client can match its UI.
    capabilities: list[str] = Field(default_factory=list)
    records: Optional[MemberRecords] = None
    has_photo: bool = False  # set by the route; true if the user uploaded a picture
    role_pending: bool = False           # awaiting admin approval of an elevated role
    requested_role: Optional[str] = None  # the role they're waiting to be granted


class RoleRequestDTO(BaseModel):
    """A pending elevated-role request, for the admin approval screen."""

    user_id: str
    full_name: str
    username: str
    requested_role: str
    when: str = ""


class PublicUserDTO(BaseModel):
    """A member as shown in the Network directory — safe fields only (no password)."""

    id: str
    full_name: str
    username: str
    role: str
    role_code: str
    user_code: str
    mobile_no: str
    is_verified: bool
    location: str | None = None
    records: Optional[MemberRecords] = None
    has_photo: bool = False
