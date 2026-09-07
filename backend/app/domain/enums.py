"""Shared enums for the domain core.

Kept in one module so `rules`, `events`, and `engine` can all import them
without circular dependencies.
"""

from __future__ import annotations

from enum import Enum


class BallType(str, Enum):
    """Physical ball used — affects stat segmentation (leather vs tennis, etc.)."""

    LEATHER = "leather"
    TENNIS = "tennis"
    OTHER = "other"


class ExtraType(str, Enum):
    """Non-standard deliveries / runs that are accounted separately from the bat."""

    WIDE = "wide"
    NO_BALL = "no_ball"
    BYE = "bye"
    LEG_BYE = "leg_bye"


class DismissalType(str, Enum):
    """All ways a batter can be out."""

    BOWLED = "bowled"
    CAUGHT = "caught"
    CAUGHT_BEHIND = "caught_behind"
    CAUGHT_AND_BOWLED = "caught_and_bowled"
    LBW = "lbw"
    RUN_OUT = "run_out"
    STUMPED = "stumped"
    HIT_WICKET = "hit_wicket"
    RETIRED_HURT = "retired_hurt"  # not out — can resume later
    RETIRED_OUT = "retired_out"
    OBSTRUCTING_FIELD = "obstructing_field"
    HIT_BALL_TWICE = "hit_ball_twice"
    TIMED_OUT = "timed_out"
    BOUNDARY_OUT = "boundary_out"  # over the boundary on the full — "rule-out" formats

    @property
    def credited_to_bowler(self) -> bool:
        """Does this dismissal count as a wicket for the bowler?"""
        return self in {
            DismissalType.BOWLED,
            DismissalType.CAUGHT,
            DismissalType.CAUGHT_BEHIND,
            DismissalType.CAUGHT_AND_BOWLED,
            DismissalType.LBW,
            DismissalType.STUMPED,
            DismissalType.HIT_WICKET,
            DismissalType.BOUNDARY_OUT,
        }

    @property
    def is_not_out(self) -> bool:
        """Retired hurt leaves the batter not out (may return)."""
        return self is DismissalType.RETIRED_HURT

    @property
    def allowed_on_free_hit(self) -> bool:
        """On a free hit, a batter can only be dismissed these ways."""
        return self in {
            DismissalType.RUN_OUT,
            DismissalType.OBSTRUCTING_FIELD,
            DismissalType.HIT_BALL_TWICE,
        }


# Standard dismissals — the default "everything allowed" set. BOUNDARY_OUT is
# excluded because it's a format-specific rule, gated by MatchRules.over_boundary_out.
ALL_DISMISSALS: list[DismissalType] = [
    d for d in DismissalType if d is not DismissalType.BOUNDARY_OUT
]
