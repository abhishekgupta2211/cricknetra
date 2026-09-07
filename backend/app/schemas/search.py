"""Unified search results across the main entities."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.roster import PlayerDTO, TeamDTO
from app.schemas.tournament import TournamentDTO
from app.schemas.user import PublicUserDTO
from app.schemas.venue import VenueDTO


class SearchResults(BaseModel):
    query: str
    players: list[PlayerDTO] = Field(default_factory=list)
    teams: list[TeamDTO] = Field(default_factory=list)
    tournaments: list[TournamentDTO] = Field(default_factory=list)
    members: list[PublicUserDTO] = Field(default_factory=list)  # only when signed in
    venues: list[VenueDTO] = Field(default_factory=list)  # grounds + academies
