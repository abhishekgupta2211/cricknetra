"""Profile schemas (from the user-supplied ``profile.py``).

``profile_picture`` is optional (we don't have uploads yet); everything else is
required, matching the "complete your profile" step.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileCompleteRequest(BaseModel):
    address: str = Field(..., min_length=3, max_length=255)
    pincode: str = Field(..., min_length=6, max_length=10)
    city: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    region: str = Field(..., min_length=2, max_length=100)
    profile_picture: Optional[str] = Field(default=None, max_length=255)

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, value: str) -> str:
        value = value.strip()
        if not value.isdigit():
            raise ValueError("Pincode must contain digits only")
        return value


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    address: str
    pincode: str
    city: str
    district: str
    state: str
    region: str
    profile_picture: Optional[str] = None
    created_at: datetime
    updated_at: datetime
