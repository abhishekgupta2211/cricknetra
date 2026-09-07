"""Stats DTOs — player career, fielding, form, leaderboards, team record."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.roster import PlayerDTO


class BattingStats(BaseModel):
    matches: int = 0
    innings: int = 0
    not_outs: int = 0
    runs: int = 0
    balls: int = 0
    highest: int = 0
    average: Optional[float] = None  # None when never dismissed
    strike_rate: float = 0.0
    fours: int = 0
    sixes: int = 0
    fifties: int = 0
    hundreds: int = 0


class BowlingStats(BaseModel):
    matches: int = 0
    innings: int = 0
    balls: int = 0
    overs: str = "0.0"
    maidens: int = 0
    runs: int = 0
    wickets: int = 0
    average: Optional[float] = None  # None when no wickets
    economy: float = 0.0
    strike_rate: Optional[float] = None
    best: str = "-"


class FieldingStats(BaseModel):
    catches: int = 0
    run_outs: int = 0
    stumpings: int = 0
    drops: int = 0  # dropped catches logged by the scorer
    runs_saved: int = 0  # runs saved by good fielding


class FormEntry(BaseModel):
    match_id: str
    teams: str  # e.g. "Aces v Blues"
    bat: Optional[str] = None  # e.g. "45 (30)" or None if did not bat
    bowl: Optional[str] = None  # e.g. "2/24 (4.0)" or None


class PlayerStatsDTO(BaseModel):
    player: PlayerDTO
    batting: BattingStats
    bowling: BowlingStats
    fielding: FieldingStats
    recent: list[FormEntry] = []


class LeaderboardEntry(BaseModel):
    player_id: str
    name: str
    value: float
    detail: Optional[str] = None  # context, e.g. "5 inns" or "avg 24.5"


class Leaderboards(BaseModel):
    min_innings: int
    # scope echo — which window/place these boards are filtered to, plus the set
    # of places the UI can offer as filters (distinct team locations on record).
    window: str = "all"  # all | week | month | year (| custom when a raw since is given)
    location: Optional[str] = None
    locations: list[str] = []
    most_runs: list[LeaderboardEntry] = []
    best_average: list[LeaderboardEntry] = []
    best_strike_rate: list[LeaderboardEntry] = []
    most_sixes: list[LeaderboardEntry] = []
    most_wickets: list[LeaderboardEntry] = []
    best_economy: list[LeaderboardEntry] = []
    best_bowling_average: list[LeaderboardEntry] = []
    most_fours: list[LeaderboardEntry] = []
    highest_score: list[LeaderboardEntry] = []
    most_catches: list[LeaderboardEntry] = []
    best_bowling: list[LeaderboardEntry] = []
    mvp: list[LeaderboardEntry] = []


class TeamStatsDTO(BaseModel):
    team_id: str
    name: str
    played: int = 0
    won: int = 0
    lost: int = 0
    tied: int = 0
    no_result: int = 0
    win_pct: float = 0.0
    runs_for: int = 0
    runs_against: int = 0


class BattingInsights(BaseModel):
    balls_faced: int = 0
    dot_balls: int = 0
    dot_pct: float = 0.0
    fours: int = 0
    sixes: int = 0
    boundary_pct: float = 0.0  # % of balls that went to the boundary
    boundary_runs: int = 0
    running_runs: int = 0
    boundary_runs_pct: float = 0.0  # % of runs scored in boundaries
    dismissals: dict = Field(default_factory=dict)  # how_out -> count
    # wagon-wheel shot analytics (from tracked shots only)
    six_pct: float = 0.0            # % of balls faced hit for six
    shots_tracked: int = 0
    off_side_pct: float = 0.0       # % of tracked shot RUNS on the off side
    leg_side_pct: float = 0.0
    top_zone: str = ""              # most productive fielding zone
    runs_by_zone: dict = Field(default_factory=dict)  # zone -> runs


class BowlingInsights(BaseModel):
    balls_bowled: int = 0
    dot_balls: int = 0
    dot_pct: float = 0.0
    wickets_by_type: dict = Field(default_factory=dict)
    # pitch-map length analytics (from tracked deliveries only)
    pitches_tracked: int = 0
    length_dist: dict = Field(default_factory=dict)     # length band -> balls
    econ_by_length: dict = Field(default_factory=dict)  # length band -> economy


class PlayerInsightsDTO(BaseModel):
    player: PlayerDTO
    batting: BattingInsights
    bowling: BowlingInsights


class CompareDTO(BaseModel):
    player_a: PlayerStatsDTO
    player_b: PlayerStatsDTO


class FormatSplit(BaseModel):
    """One bucket of a player's career — by match format or by ball type."""

    key: str  # stable id, e.g. "t20" / "leather"
    label: str  # human label, e.g. "T20" / "Leather"
    matches: int = 0
    batting: BattingStats
    bowling: BowlingStats


class BattingVsType(BaseModel):
    """A batter's record against one kind of bowling (pace or spin)."""

    label: str  # "vs Pace" / "vs Spin"
    balls: int = 0
    runs: int = 0
    dot_balls: int = 0
    dot_pct: float = 0.0
    fours: int = 0
    sixes: int = 0
    strike_rate: float = 0.0
    dismissals: int = 0
    average: Optional[float] = None  # None when never dismissed by this type


class PlayerSplitsDTO(BaseModel):
    """Per-format / per-ball-type stat splits for a player's profile."""

    player: PlayerDTO
    by_format: list[FormatSplit] = []  # T20 / ODI / T10 / Box / Multi-day
    by_ball: list[FormatSplit] = []  # Leather / Tennis / Other
    vs_pace: BattingVsType
    vs_spin: BattingVsType
    # True once at least one ball was faced against a *classified* bowler, so the
    # UI can hide the matchup card when no opponent styles are recorded.
    has_matchup: bool = False


class AwardDTO(BaseModel):
    """A match award a player has won (MoM / best batter / best bowler)."""

    model_config = ConfigDict(from_attributes=True)
    match_id: str
    award_type: str          # mom | best_bat | best_bowl
    player_name: str
    detail: str = ""
    when: str = ""


class CareerMatch(BaseModel):
    """One match in a player's career, with everything they did in it.

    This is the row a player wants to see when they ask "what did I do that
    day": who it was against, in which competition, and their own batting,
    bowling and fielding line.
    """

    match_id: str
    played_on: Optional[str] = None   # ISO date the match was created
    format: str = ""                  # "T20", "Box", the rulebook's name
    team: str = ""                    # the side they turned out for
    opponent: str = ""
    tournament: Optional[str] = None
    venue: Optional[str] = None
    match_no: Optional[str] = None

    result: Optional[str] = None      # the engine's result sentence
    # won | lost | tied | no_result | in_progress — from THIS player's side
    outcome: str = "in_progress"

    # batting (all None when they did not bat)
    batted: bool = False
    runs: Optional[int] = None
    balls: Optional[int] = None
    fours: int = 0
    sixes: int = 0
    strike_rate: Optional[float] = None
    not_out: bool = False
    how_out: Optional[str] = None
    dismissal_text: Optional[str] = None
    bat_line: Optional[str] = None    # "45* (30)"

    # bowling (all None when they did not bowl)
    bowled: bool = False
    overs: Optional[str] = None
    maidens: int = 0
    runs_conceded: Optional[int] = None
    wickets: Optional[int] = None
    economy: Optional[float] = None
    bowl_line: Optional[str] = None   # "2/24 (4.0)"

    # fielding
    catches: int = 0
    run_outs: int = 0
    stumpings: int = 0


class CareerBucket(BaseModel):
    """A player's record inside one grouping — a tournament, or a year."""

    key: str                          # stable id for the group
    label: str                        # what to show: the tournament name, "2026"
    matches: int = 0
    won: int = 0
    lost: int = 0
    batting: BattingStats
    bowling: BowlingStats
    fielding: FieldingStats


class PlayerHistoryDTO(BaseModel):
    """A player's full record: every match, grouped every useful way.

    `matches` is the whole career, newest first — not a recent-form sample.
    """

    player: PlayerDTO
    debut: Optional[str] = None       # ISO date of the first match
    last_played: Optional[str] = None
    matches_played: int = 0
    won: int = 0
    lost: int = 0
    tied: int = 0
    no_result: int = 0
    win_pct: float = 0.0

    batting: BattingStats
    bowling: BowlingStats
    fielding: FieldingStats

    matches: list[CareerMatch] = []
    by_tournament: list[CareerBucket] = []
    by_year: list[CareerBucket] = []
    by_team: list[CareerBucket] = []
