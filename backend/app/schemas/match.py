"""Match request + response DTOs (the shape the React client will render)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.core.streaming import StreamInfo
from app.domain.rules import MatchRules


class CreateMatchRequest(BaseModel):
    team_a: str = Field(..., min_length=1)
    team_b: str = Field(..., min_length=1)
    format_id: str = Field(default="t20", description="preset id; ignored if `rules` is given")
    bat_first: str = Field(default="a", pattern="^(a|b)$")
    squad_a: Optional[list[str]] = Field(default=None, description="auto-generated if omitted")
    squad_b: Optional[list[str]] = None
    rules: Optional[MatchRules] = Field(
        default=None, description="full custom rules; overrides `format_id`"
    )
    # Optional real-player linkage (parallel to squad_a/squad_b), so the match
    # contributes to each player's career stats. Sent by the "from teams" flow.
    squad_a_ids: Optional[list[str]] = None
    squad_b_ids: Optional[list[str]] = None
    team_a_id: Optional[str] = None
    team_b_id: Optional[str] = None
    # display-only setup metadata captured at creation (not scoring rules)
    venue: Optional[str] = Field(default=None, max_length=120)
    tournament: Optional[str] = Field(default=None, max_length=120)
    match_no: Optional[str] = Field(default=None, max_length=40)
    toss_winner: Optional[str] = Field(default=None, pattern="^(a|b)$", description="which side won the toss")
    toss_decision: Optional[str] = Field(default=None, pattern="^(bat|bowl)$")


class BatterDTO(BaseModel):
    name: str
    order: int
    runs: int
    balls: int
    fours: int
    sixes: int
    out: bool
    how_out: Optional[str]
    dismissal_text: Optional[str]
    on_strike: bool
    has_batted: bool
    strike_rate: float
    player_id: Optional[str] = None  # real roster id (from-teams matches) → profile link


class BowlerDTO(BaseModel):
    name: str
    order: int
    overs: str
    maidens: int
    runs: int
    wickets: int
    economy: float
    wides: int
    no_balls: int
    player_id: Optional[str] = None  # real roster id (from-teams matches) → profile link


class FallOfWicketDTO(BaseModel):
    wicket: int
    score: int
    batter_out: str
    over: str


class PartnershipDTO(BaseModel):
    wicket: int          # which wicket the stand is for (1 = opening stand)
    runs: int
    balls: int
    batter_a: str
    batter_b: str
    unbroken: bool = False
    run_rate: float = 0.0


class WagonShotDTO(BaseModel):
    """One scoring shot for the wagon wheel (direction normalised -1..1)."""

    x: float
    y: float
    runs: int
    batter: str
    over: str
    ball: str = ""            # precise over.ball, e.g. "12.4"
    bowler: str = ""
    wicket: bool = False
    zone: str = ""            # derived fielding region (right-hander convention)


class PitchMarkDTO(BaseModel):
    """One delivery on the pitch map — line x (-1 leg..+1 off), length y (0..1)."""

    x: float
    y: float
    runs: int
    wicket: bool = False
    bowler: str = ""
    batter: str = ""
    over: str = ""            # over.ball
    speed: Optional[float] = None
    length: str = ""          # derived length band (Yorker … Bouncer)
    line: str = ""            # derived line band (Down Leg … Wide Outside Off)
    outcome: str = ""         # dot|single|two|three|four|six|wicket|runs


class InningsDTO(BaseModel):
    batting_team: str
    bowling_team: str
    runs: int
    wickets: int
    legal_balls: int
    overs_str: str
    max_overs: int
    max_wickets: int
    extras: dict
    run_rate: float
    batters: list[BatterDTO]
    bowlers: list[BowlerDTO]
    fall_of_wickets: list[FallOfWicketDTO]
    partnerships: list[PartnershipDTO] = []
    this_over: list[str]
    manhattan: list[int]
    worm: list[int]
    wagon: list[WagonShotDTO] = []
    pitch: list[PitchMarkDTO] = []
    striker: Optional[str]
    non_striker: Optional[str]
    bowler: Optional[str]
    free_hit: bool
    is_complete: bool
    target: Optional[int]
    required_runs: Optional[int]
    balls_remaining: Optional[int]
    required_run_rate: Optional[float]
    result_note: Optional[str]
    current_over: int = 1
    in_powerplay: bool = False
    powerplay_label: Optional[str] = None
    fielders_outside_limit: Optional[int] = None
    is_super_over: bool = False


class AwardEntry(BaseModel):
    name: str
    team: Optional[str] = None
    line: str = ""  # MoM: "45 (30) & 2/18"; best batter/bowler: their figure


class MatchAwards(BaseModel):
    man_of_the_match: Optional[AwardEntry] = None
    best_batter: Optional[AwardEntry] = None
    best_bowler: Optional[AwardEntry] = None


class MatchClipDTO(BaseModel):
    """A stored highlight clip — either a bring-your-own link or an auto-cut video."""

    id: str
    url: str
    label: Optional[str] = None
    kind: str            # youtube | facebook | external | video (auto-cut mp4)
    embed_url: Optional[str] = None
    source: str = "link"  # "link" (embed) | "auto" (server-cut mp4, play inline)


class MatchHighlightsDTO(BaseModel):
    """One match's highlight clips, for the cross-match highlights gallery."""

    match_id: str
    team_a: str
    team_b: str
    live: bool
    status_label: str  # "Live" | "Result"
    fmt: str
    clips: list[MatchClipDTO] = []


class MatchMeta(BaseModel):
    """Display-only match metadata captured at creation — venue, toss, tournament,
    match number. Shown on the public page, the broadcast overlay and the PDF; never
    part of the scoring rules."""

    venue: Optional[str] = None
    tournament: Optional[str] = None
    match_no: Optional[str] = None
    toss_winner: Optional[str] = None    # the team NAME that won the toss
    toss_decision: Optional[str] = None  # "bat" | "bowl"
    toss_text: Optional[str] = None      # e.g. "CSK won the toss and chose to bat"


class DlsInterruptionDTO(BaseModel):
    innings: int
    reason: str
    overs_lost: float
    wickets: int
    interrupt_at: Optional[str] = None
    resume_at: Optional[str] = None
    pending: bool = False


class DlsState(BaseModel):
    """Everything the scorer card / overlay / public page / PDF need about the rain
    revision — computed automatically from the interruptions (the scorer never does)."""

    enabled: bool
    applied: bool                       # a revision (or abandonment) is in effect
    pending: bool                       # play interrupted, awaiting resume + overs
    abandoned: bool = False
    abandon_reason: Optional[str] = None
    original_overs: int
    revised_overs: Optional[int] = None
    revised_target: Optional[int] = None
    par: Optional[int] = None           # live par for the chase
    r1: float = 0.0                     # team 1 resources %
    r2: float = 0.0                     # team 2 resources %
    min_overs: int = 0                  # overs the chase must reach for a DLS result
    overs_lost: float = 0.0
    revision_seq: int = 0               # bumps on each completed revision (overlay uses it)
    interruptions: list[DlsInterruptionDTO] = []


class MatchStateDTO(BaseModel):
    id: str
    team_a: str
    team_b: str
    bat_first: str
    format_id: str
    rules_name: str
    rules: MatchRules  # full rulebook, so the client can adapt the scoring pad
    current_innings: int
    awaiting_bowler: bool
    over_pending: bool = False  # between overs: a bowler can still be chosen/changed
    staged_bowler: Optional[str] = None  # bowler picked for the new over, not yet bowling
    available_bowlers: list[str]
    can_start_second_innings: bool
    needs_super_over: bool = False
    awaiting_super_second: bool = False
    result: Optional[str]
    innings: list[InningsDTO]
    awards: Optional[MatchAwards] = None  # auto MoM / best batter / best bowler (finished matches)
    stream: Optional[StreamInfo] = None  # bring-your-own live-stream (YouTube/Facebook), if attached
    clips: list[MatchClipDTO] = []       # highlight clips (links + auto-cut videos), shipped in the state
    meta: MatchMeta = Field(default_factory=MatchMeta)  # venue / toss / tournament (display only)
    dls: Optional[DlsState] = None  # rain revision state (None when DLS is off)


class StreamUrlRequest(BaseModel):
    """Attach (or clear, with null/empty) a bring-your-own live-stream link."""

    stream_url: Optional[str] = Field(default=None, max_length=500)


class ClipCreate(BaseModel):
    """Attach a bring-your-own highlight clip link (YouTube / Facebook / …)."""

    url: str = Field(..., min_length=1, max_length=500)
    label: Optional[str] = Field(default=None, max_length=80)


class AutoClipRequest(BaseModel):
    """Auto-cut clips from the uploaded recording. ``anchor`` = the video-time
    (seconds) at which the first ball is bowled."""

    anchor: float = Field(default=0.0, ge=0, le=86400)


class RevisedTargetRequest(BaseModel):
    """DLS-style rain revision applied to the chase."""

    target: int = Field(..., ge=1, description="runs the chasing side needs to win")
    overs: Optional[int] = Field(default=None, ge=1, description="revised overs for the chase")


_DLS_REASONS = "rain|bad_light|wet_outfield|ground_delay|power_failure|other"


class InterruptRequest(BaseModel):
    """The scorer flags that play has stopped."""

    reason: str = Field(default="rain", pattern=f"^({_DLS_REASONS})$")
    at: Optional[str] = Field(default=None, max_length=40, description="ISO time play stopped")


class ResumeRequest(BaseModel):
    """Play resumes; the scorer confirms the innings' new total overs — that's all."""

    overs: int = Field(..., ge=1, le=50, description="the interrupted innings' new TOTAL overs")
    at: Optional[str] = Field(default=None, max_length=40, description="ISO time play resumed")


class AbandonRequest(BaseModel):
    reason: str = Field(default="rain", pattern=f"^({_DLS_REASONS})$")


class DlsSuggestRequest(BaseModel):
    """Ask the DLS calculator for a revised target given a reduced chase length."""

    team2_overs: int = Field(..., ge=1, le=50, description="team 2's TOTAL available overs after the reduction")
    g50: Optional[int] = Field(default=None, ge=100, le=400, description="avg 50-over score (only used if team 2 gains resources)")


class DlsSuggestion(BaseModel):
    """The DLS calculator's answer — a suggested target + the live par score."""

    target: int          # runs team 2 needs to win off the reduced overs
    par: int             # score team 2 should be level with right now
    r1: float            # team 1's resources (%)
    r2: float            # team 2's resources (%)
    resources_used: float
    overs_left: float
    note: str


class SuperOverRequest(BaseModel):
    """Start a super over. ``bat_first`` (team a/b) only applies to a new round."""

    bat_first: Optional[str] = Field(default=None, pattern="^(a|b)$")


class BroadcastRequest(BaseModel):
    """Set the broadcast presentation mode for the single OBS overlay source."""

    mode: Optional[str] = Field(default=None, description="LIVE|WORM|WAGON|PITCH|PARTNERSHIP|SUMMARY")
    auto: Optional[bool] = None


class MatchSummaryDTO(BaseModel):
    id: str
    team_a: str
    team_b: str
    status: str
    result: Optional[str]
