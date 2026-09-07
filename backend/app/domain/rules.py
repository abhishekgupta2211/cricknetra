"""Configurable match-rules model — CricNetra's headline differentiator.

The rulebook is *data*, not code: an organizer composes a `MatchRules` object
(directly or from a preset), names it, and reuses it. The scoring engine takes a
`MatchRules` as a parameter and behaves accordingly, so box cricket, gully
cricket, T20, and The Hundred are all the same engine with different config.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import ALL_DISMISSALS, BallType, DismissalType


class PowerplayRange(BaseModel):
    """An inclusive, 1-based range of overs with a fielding restriction."""

    start_over: int = Field(ge=1)
    end_over: int = Field(ge=1)
    max_fielders_outside: int = Field(default=2, ge=0)
    label: str = "Powerplay"

    @model_validator(mode="after")
    def _check_range(self) -> "PowerplayRange":
        if self.end_over < self.start_over:
            raise ValueError("powerplay end_over must be >= start_over")
        return self

    def covers(self, over_number: int) -> bool:
        return self.start_over <= over_number <= self.end_over


class WideRules(BaseModel):
    enabled: bool = True
    run_penalty: int = Field(default=1, ge=0)
    counts_as_legal_ball: bool = False  # False => re-bowled (doesn't advance the over)
    allow_byes: bool = True  # can batters physically run extra on a wide?


class NoBallRules(BaseModel):
    enabled: bool = True
    run_penalty: int = Field(default=1, ge=0)
    counts_as_legal_ball: bool = False  # False => re-bowled
    free_hit: bool = True  # next legal delivery is a free hit
    off_bat_counts: bool = True  # runs hit off a no-ball go to the batter
    allow_byes: bool = True  # byes/leg-byes runnable after a no-ball


class Interruption(BaseModel):
    """One stoppage in play (rain, bad light, …) that may cut the overs.

    Lives on the match's own rulebook (persists in matches.rules JSON, no schema
    migration) and is re-applied on rebuild. Overs are *overs remaining* at the
    moment of the stoppage: the cut from ``overs_before`` → ``overs_after`` is what
    costs DLS resources. ``pending`` is True between the interruption and its resume.
    """

    innings: int = Field(ge=1, le=4)
    reason: str = "rain"              # rain | bad_light | wet_outfield | ground_delay | power_failure | other
    balls: int = 0                    # legal balls bowled in that innings when play stopped
    wickets: int = 0
    overs_before: float = 0.0         # overs remaining before the cut
    overs_after: float = 0.0          # overs remaining after resumption (≤ overs_before)
    interrupt_at: Optional[str] = None  # ISO time play stopped
    resume_at: Optional[str] = None     # ISO time play resumed
    pending: bool = False             # awaiting resume + overs confirmation

    @property
    def overs_lost(self) -> float:
        return round(max(0.0, self.overs_before - self.overs_after), 2)


class SuperOverRound(BaseModel):
    """Persisted setup for one super-over round.

    A super over is a one-over-per-side eliminator (all out at 2 wickets). Only
    the *setup* is stored here — who bats first, and whether the chase has begun;
    the deliveries themselves live in the event log as extra innings.
    """

    bat_first: str  # team name batting first this round
    second_started: bool = False


class MatchRules(BaseModel):
    """A complete, self-contained description of how a match is scored."""

    name: str = "Custom"
    format_id: str = "custom"
    description: str = ""

    # Shape of the contest
    players_per_side: int = Field(default=11, ge=2, le=20)
    overs_per_innings: int = Field(default=20, ge=1, le=200)
    balls_per_over: int = Field(default=6, ge=1, le=12)
    innings_per_side: int = Field(default=1, ge=1, le=2)
    ball_type: BallType = BallType.LEATHER

    # Bowling constraints
    max_overs_per_bowler: Optional[int] = Field(default=None, ge=1)
    allow_consecutive_overs: bool = False  # can a bowler bowl back-to-back overs?

    # Fielding restrictions
    powerplays: list[PowerplayRange] = Field(default_factory=list)
    # Max fielders allowed outside the 30-yard circle in normal (non-powerplay)
    # overs. Powerplay overs use their own (tighter) PowerplayRange limit.
    default_fielders_outside: int = Field(default=5, ge=0, le=20)

    # Extras
    wide: WideRules = Field(default_factory=WideRules)
    no_ball: NoBallRules = Field(default_factory=NoBallRules)
    byes_allowed: bool = True
    leg_byes_allowed: bool = True

    # Format quirks
    last_man_stands: bool = False  # last batter bats on alone (indoor/box)
    allow_declaration: bool = False
    super_over_on_tie: bool = False  # a tie is broken by a one-over eliminator
    # Rain/short-match revised targets (Duckworth–Lewis–Stern style). When on,
    # the match is flagged as DLS-eligible and the scorer may set a revised
    # target/overs; the automatic par-score table is not computed here.
    dls_enabled: bool = False
    # Per-match DLS overrides (NOT part of a saved template — they live on the
    # match's own rulebook so they persist in the matches.rules JSON with no
    # schema migration). Set by the scorer during a rain break; they reshape the
    # second innings (target to win + overs available).
    revised_target: Optional[int] = Field(default=None, ge=1)
    revised_overs: Optional[int] = Field(default=None, ge=1)
    # Rain interruptions (reason + times + overs cut). They DRIVE the automatic DLS
    # target — the scorer only confirms overs; revised_target/overs above are the
    # computed result. Persisted in rules JSON, re-applied on rebuild (no migration).
    interruptions: list["Interruption"] = Field(default_factory=list)
    # Match called off. abandoned=True with a completed 2nd innings past the DLS
    # minimum overs → decided on par; otherwise "No result".
    abandoned: bool = False
    abandon_reason: Optional[str] = None
    # Minimum overs the chasing side must face for a DLS result to stand (ICC: 20
    # for 50-over, 5 for T20). 0 = derive from the innings length.
    dls_min_overs: int = Field(default=0, ge=0)
    g50: int = Field(default=245, ge=1)  # avg 50-over score, for the "team 2 gained resources" case
    # Captain's declaration: which innings (1 or 2) was declared closed early.
    # Lives on the match's own rulebook (persists in matches.rules JSON, no schema
    # migration) and is re-applied on rebuild to keep that innings complete.
    declared_innings: Optional[int] = Field(default=None, ge=1, le=2)
    # Super-over rounds played to break a tie (one entry per round). Lives on the
    # match's own rulebook so the event log replays into the right innings with
    # no schema migration; empty for a saved template.
    super_over_rounds: list[SuperOverRound] = Field(default_factory=list)
    # "Rule-out" (vs "full ground"): hitting the ball over the boundary on the
    # full is OUT, not six — common in box/gully cricket with limited space.
    over_boundary_out: bool = False

    # Dismissals permitted in this format (e.g. gully cricket may ban LBW)
    allowed_dismissals: list[DismissalType] = Field(
        default_factory=lambda: list(ALL_DISMISSALS)
    )

    # Boundary values (kept configurable for exotic variants)
    four_value: int = 4
    six_value: int = 6

    @field_validator("max_overs_per_bowler")
    @classmethod
    def _cap_bowler_overs(cls, v: Optional[int], info) -> Optional[int]:
        return v

    @model_validator(mode="after")
    def _coherence(self) -> "MatchRules":
        if self.max_overs_per_bowler and self.max_overs_per_bowler > self.overs_per_innings:
            raise ValueError("max_overs_per_bowler cannot exceed overs_per_innings")
        for pp in self.powerplays:
            if pp.end_over > self.overs_per_innings:
                raise ValueError("powerplay range exceeds overs_per_innings")
        return self

    # ----- derived helpers used by the engine -----

    @property
    def wickets_to_all_out(self) -> int:
        """How many wickets end the innings.

        Normally players-1 (last batter has no partner). With last-man-stands the
        final batter continues alone, so it takes one more wicket to end it.
        """
        return self.players_per_side if self.last_man_stands else self.players_per_side - 1

    @property
    def total_legal_balls(self) -> int:
        return self.overs_per_innings * self.balls_per_over

    def is_powerplay(self, over_number: int) -> bool:
        return any(pp.covers(over_number) for pp in self.powerplays)

    def active_powerplay(self, over_number: int) -> Optional[PowerplayRange]:
        """The powerplay range covering this (1-based) over, if any."""
        for pp in self.powerplays:
            if pp.covers(over_number):
                return pp
        return None

    def fielders_outside_limit(self, over_number: int) -> int:
        """Max fielders allowed outside the circle in this (1-based) over.

        A powerplay's own restriction applies during its overs; otherwise the
        normal-over default governs.
        """
        pp = self.active_powerplay(over_number)
        return pp.max_fielders_outside if pp else self.default_fielders_outside

    def dismissal_allowed(self, d: DismissalType) -> bool:
        # "Boundary out" only exists in rule-out formats; everything else is
        # governed by the configured allow-list.
        if d is DismissalType.BOUNDARY_OUT:
            return self.over_boundary_out
        return d in self.allowed_dismissals
