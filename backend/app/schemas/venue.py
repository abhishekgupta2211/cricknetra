"""Venue DTOs — grounds + coaching academies."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class VenueCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    kind: str = "ground"  # ground | academy (validated in the service)
    city: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=300)


class VenueDTO(BaseModel):
    id: str
    name: str
    kind: str
    city: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    note: Optional[str] = None
    when: str
