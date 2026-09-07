"""Tournament DTOs."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.domain.rules import MatchRules
from app.schemas.roster import PlayerDTO


class TournamentCreate(BaseModel):
    name: str = Field(..., min_length=1)
    format: str = Field(default="round_robin", pattern="^(round_robin|knockout|groups)$")
    team_ids: list[str] = Field(..., min_length=2)
    format_id: str = Field(default="t20", description="preset for the matches' rules")
    rules: Optional[MatchRules] = Field(default=None, description="custom rules override")
    # 'groups' format: pools + a seeded knockout playoff
    num_groups: int = Field(default=2, ge=2, le=16)
    advance_per_group: int = Field(default=2, ge=1, le=8)
    # configurable points (apply to league + groups standings)
    win_points: int = Field(default=2, ge=0, le=20)
    tie_points: int = Field(default=1, ge=0, le=20)
    nr_points: int = Field(default=1, ge=0, le=20)
    # rain rules for every match in the tournament (DLS revised targets)
    dls_enabled: bool = False


class TournamentSettings(BaseModel):
    """Admin-toggleable tournament settings (currently just the DLS switch)."""

    dls_enabled: bool


class TeamRef(BaseModel):
    id: str
    name: str


class FixtureDTO(BaseModel):
    id: str
    round: int
    position: int
    team_a: Optional[TeamRef]
    team_b: Optional[TeamRef]
    match_id: Optional[str]
    status: str  # scheduled | live | completed
    result: Optional[str] = None
    group: Optional[str] = None  # pool label, or None for a playoff/bracket fixture


class StandingRow(BaseModel):
    team_id: str
    name: str
    played: int = 0
    won: int = 0
    lost: int = 0
    tied: int = 0
    no_result: int = 0
    points: int = 0
    nrr: float = 0.0


class TournamentDTO(BaseModel):
    id: str
    name: str
    format: str
    status: str
    teams: list[TeamRef]


class GroupStanding(BaseModel):
    """One pool's points table in a 'groups' tournament."""

    group: str  # "A", "B", …
    standings: list[StandingRow] = []


class TournamentDetailDTO(TournamentDTO):
    fixtures: list[FixtureDTO]
    standings: list[StandingRow]  # flat league table (round_robin); empty for groups
    groups: list[GroupStanding] = []  # per-pool tables (groups format)
    champion: Optional[TeamRef] = None
    config: dict = Field(default_factory=dict)  # points + group settings echo
    is_manager: bool = Field(
        default=False,
        description="May the caller run this competition (its organizer, or an admin)?",
    )
    """Viewer-aware, and the answer to a question the client previously had to
    ask by attacking the API: nothing on the detail said who manages a
    competition, so the app probed a management endpoint and read the 403 as
    "not yours" — one refused request on every visit by everybody else.

    Always ``False`` unless a route sets it from the authenticated caller via
    ``ScopeService``. It is never read from the request, and it is a hint for
    the UI: the server still refuses the write, whatever the client was told.
    """


class StartFixtureRequest(BaseModel):
    squad_a_ids: list[str] = Field(..., min_length=2)
    squad_b_ids: list[str] = Field(..., min_length=2)
    bat_first: str = Field(default="a", pattern="^(a|b)$")


class TeamSquadDTO(BaseModel):
    """A team's registered squad for one tournament."""

    team_id: str
    team_name: str
    players: list[PlayerDTO] = Field(default_factory=list)


class SquadRegisterRequest(BaseModel):
    player_id: str


class PlayerTournamentDTO(BaseModel):
    """One competition a player is *registered* in, from the other side.

    Distinct from the tournament buckets in a player's history: those are
    derived from matches already played, so a player entered into a squad but
    not yet fielded appears in none of them. This is the registration itself,
    which exists from the moment the organizer picks them — with ``has_played``
    saying which of the two facts is true.
    """

    tournament_id: str
    tournament_name: str
    format: str
    status: str
    team_id: str
    team_name: str
    has_played: bool = False
    matches_played: int = 0
