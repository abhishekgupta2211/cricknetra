"""Ball events — the append-only source of truth.

Every delivery is one `BallEvent`. The scorecard, stats, wagon wheel and charts
are all *projections* folded from this list, so UNDO = drop the last event and
replay, and editing history = patch an event and replay from there. No derived
state is ever the source of truth.

`extra_runs` semantics by `extra` type:
  - None      : pure off-bat (use `runs_off_bat`); a dot is runs_off_bat=0.
  - WIDE      : `extra_runs` = additional runs physically run (wide-byes); the
                mandatory wide penalty is added by the engine from the rules.
  - NO_BALL   : off-bat via `runs_off_bat`; `extra_runs` = byes/leg-byes run
                after the no-ball; the mandatory penalty comes from the rules.
  - BYE       : `extra_runs` = byes run (runs_off_bat must be 0).
  - LEG_BYE   : `extra_runs` = leg-byes run (runs_off_bat must be 0).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .enums import DismissalType, ExtraType


class Wicket(BaseModel):
    type: DismissalType
    # Which batter is dismissed. Run-outs / retirements can take the non-striker.
    batter_out: Literal["striker", "non_striker"] = "striker"
    fielder: Optional[str] = None  # catcher / run-out thrower / stumper
    # For a *caught* dismissal with 0 runs: did the batters cross before the
    # catch was taken? (For run-outs, crossing is implied by the runs completed.)
    crossed: bool = False


class BallEvent(BaseModel):
    """One delivery. Construct via the classmethods for clarity."""

    runs_off_bat: int = Field(default=0, ge=0)
    extra: Optional[ExtraType] = None
    extra_runs: int = Field(default=0, ge=0)
    wicket: Optional[Wicket] = None

    # Wagon-wheel shot coordinate (normalised -1..1 from the striker's position).
    wagon_x: Optional[float] = None
    wagon_y: Optional[float] = None

    # Pitch-map coordinate (bowling): line x (-1 down leg .. +1 wide off) and length
    # y (0 = yorker/at the batter .. 1 = bouncer). Optional release speed (kph). All
    # optional — old events replay unchanged (defaults apply on model_validate).
    pitch_x: Optional[float] = None
    pitch_y: Optional[float] = None
    speed: Optional[float] = None

    # Stamped by the engine at apply-time so replay is fully deterministic.
    bowler: Optional[str] = None
    striker: Optional[str] = None
    incoming_batter: Optional[str] = None  # who replaced a dismissed batter

    # Wall-clock time (epoch seconds) the delivery was scored — set once at record
    # time, preserved through replay. Used to sync auto highlight clips to a video.
    ts: Optional[float] = None

    # ---- ergonomic constructors ----

    @classmethod
    def runs(cls, n: int, **kw) -> "BallEvent":
        return cls(runs_off_bat=n, **kw)

    @classmethod
    def dot(cls, **kw) -> "BallEvent":
        return cls(runs_off_bat=0, **kw)

    @classmethod
    def wide(cls, ran: int = 0, wicket: Optional[Wicket] = None, **kw) -> "BallEvent":
        return cls(extra=ExtraType.WIDE, extra_runs=ran, wicket=wicket, **kw)

    @classmethod
    def no_ball(cls, off_bat: int = 0, byes: int = 0, wicket: Optional[Wicket] = None, **kw) -> "BallEvent":
        return cls(
            extra=ExtraType.NO_BALL,
            runs_off_bat=off_bat,
            extra_runs=byes,
            wicket=wicket,
            **kw,
        )

    @classmethod
    def bye(cls, n: int, **kw) -> "BallEvent":
        return cls(extra=ExtraType.BYE, extra_runs=n, **kw)

    @classmethod
    def leg_bye(cls, n: int, **kw) -> "BallEvent":
        return cls(extra=ExtraType.LEG_BYE, extra_runs=n, **kw)

    @classmethod
    def out(
        cls,
        dismissal: DismissalType,
        runs_off_bat: int = 0,
        batter_out: Literal["striker", "non_striker"] = "striker",
        fielder: Optional[str] = None,
        crossed: bool = False,
        **kw,
    ) -> "BallEvent":
        return cls(
            runs_off_bat=runs_off_bat,
            wicket=Wicket(
                type=dismissal, batter_out=batter_out, fielder=fielder, crossed=crossed
            ),
            **kw,
        )
