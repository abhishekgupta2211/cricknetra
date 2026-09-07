"""Ready-made `MatchRules` presets.

These are just starting points — the whole value of the rules engine is that a
user can clone one of these, tweak it in the builder, and save their own named
template. Each preset is returned fresh (deep-copied defaults) so callers can
mutate without clobbering the canonical version.
"""

from __future__ import annotations

from .enums import BallType, DismissalType
from .rules import MatchRules, NoBallRules, PowerplayRange, WideRules


def t20() -> MatchRules:
    return MatchRules(
        name="T20",
        format_id="t20",
        description="Standard 20-over-a-side limited format.",
        players_per_side=11,
        overs_per_innings=20,
        balls_per_over=6,
        ball_type=BallType.LEATHER,
        max_overs_per_bowler=4,
        powerplays=[PowerplayRange(start_over=1, end_over=6, label="Powerplay")],
        no_ball=NoBallRules(free_hit=True),
    )


def t10() -> MatchRules:
    return MatchRules(
        name="T10",
        format_id="t10",
        description="Fast 10-over format.",
        overs_per_innings=10,
        max_overs_per_bowler=2,
        powerplays=[PowerplayRange(start_over=1, end_over=3, label="Powerplay")],
    )


def odi() -> MatchRules:
    return MatchRules(
        name="ODI (50)",
        format_id="odi",
        description="50-over one-day format.",
        overs_per_innings=50,
        max_overs_per_bowler=10,
        powerplays=[
            PowerplayRange(start_over=1, end_over=10, label="Powerplay 1"),
            PowerplayRange(start_over=11, end_over=40, max_fielders_outside=4, label="Powerplay 2"),
            PowerplayRange(start_over=41, end_over=50, max_fielders_outside=5, label="Powerplay 3"),
        ],
    )


def box_cricket() -> MatchRules:
    """Indoor / society box cricket: small side, tennis ball, last man stands."""
    return MatchRules(
        name="Box Cricket",
        format_id="box6",
        description="6-a-side, 5 overs, tennis ball, last-man-stands, no LBW.",
        players_per_side=6,
        overs_per_innings=5,
        balls_per_over=6,
        ball_type=BallType.TENNIS,
        max_overs_per_bowler=2,
        allow_consecutive_overs=False,
        last_man_stands=True,
        # Common box-cricket house rules:
        no_ball=NoBallRules(free_hit=False),
        leg_byes_allowed=False,
        allowed_dismissals=[
            d for d in DismissalType if d is not DismissalType.LBW
        ],
    )


def gully() -> MatchRules:
    """Street cricket: relaxed, no extras fuss, one-hand-one-bounce omitted here."""
    return MatchRules(
        name="Gully",
        format_id="gully",
        description="Casual street cricket — small side, no wides/no-ball penalties.",
        players_per_side=6,
        overs_per_innings=4,
        ball_type=BallType.TENNIS,
        wide=WideRules(enabled=True, run_penalty=1, allow_byes=False),
        no_ball=NoBallRules(enabled=True, run_penalty=1, free_hit=False),
        byes_allowed=False,
        leg_byes_allowed=False,
        last_man_stands=True,
    )


def street_ruleout() -> MatchRules:
    """Box/street cricket, 'rule-out': over the boundary on the full is OUT, not six."""
    return MatchRules(
        name="Street (Rule-out)",
        format_id="ruleout",
        description="Tennis-ball box cricket — hitting it over the boundary on the full is OUT.",
        players_per_side=6,
        overs_per_innings=6,
        balls_per_over=6,
        ball_type=BallType.TENNIS,
        max_overs_per_bowler=2,
        last_man_stands=True,
        over_boundary_out=True,
        no_ball=NoBallRules(free_hit=False),
        leg_byes_allowed=False,
        allowed_dismissals=[d for d in DismissalType if d is not DismissalType.LBW],
    )


# Registry the web layer can list / look up by id.
PRESETS = {
    "t20": t20,
    "t10": t10,
    "odi": odi,
    "box6": box_cricket,
    "gully": gully,
    "ruleout": street_ruleout,
}


def get_preset(format_id: str) -> MatchRules:
    if format_id not in PRESETS:
        raise KeyError(f"unknown preset '{format_id}'")
    return PRESETS[format_id]()
