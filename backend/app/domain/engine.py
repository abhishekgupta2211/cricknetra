"""The CricNetra scoring engine — event-sourced, framework-independent.

Design: a single innings is an **append-only list of `BallEvent`s**. All visible
state (scorecard, batting/bowling cards, extras, fall-of-wickets, charts) is a
*projection* folded from that list by `_apply`. Consequences:

  * UNDO  = pop the last event and replay (`_rebuild`).
  * EDIT  = patch/insert an event and replay from scratch — always consistent.
  * Stats never drift from the ball log, because the log *is* the truth.

Strike is tracked with a two-slot model: `ends[0]` / `ends[1]` hold the two
batters by crease end, and `striker_end` points at whoever is on strike. Running
an odd number of runs or completing an over flips the pointer — names only move
when a batter is dismissed. This makes the gnarly "who's on strike after a wicket
on the last ball of the over" cases fall out correctly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .enums import DismissalType, ExtraType
from .events import BallEvent
from .rules import Interruption, MatchRules, SuperOverRound


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class ScoringError(Exception):
    """Base class for all illegal scoring actions."""


class NeedBowler(ScoringError):
    """A new over has started and no bowler was set."""


class RuleViolation(ScoringError):
    """The action breaks a configured rule (max overs, consecutive overs...)."""


class InningsComplete(ScoringError):
    """The innings is already over."""


# --------------------------------------------------------------------------- #
# Projection value objects
# --------------------------------------------------------------------------- #
@dataclass
class BatterCard:
    name: str
    order: int = 0
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    out: bool = False
    how_out: Optional[DismissalType] = None
    dismissal_text: Optional[str] = None
    fielder: Optional[str] = None  # catcher / run-out thrower / stumper (for fielding stats)
    out_bowler: Optional[str] = None  # bowler credited (for wickets-by-type insight)
    on_strike: bool = False
    has_batted: bool = False

    @property
    def strike_rate(self) -> float:
        return round(100.0 * self.runs / self.balls, 2) if self.balls else 0.0

    @property
    def status(self) -> str:
        if self.out:
            return self.dismissal_text or "out"
        if self.has_batted:
            return "not out"
        return "did not bat"


@dataclass
class BowlerCard:
    name: str
    order: int = 0
    legal_balls: int = 0
    runs: int = 0
    wickets: int = 0
    maidens: int = 0
    wides: int = 0
    no_balls: int = 0

    @property
    def overs_str(self) -> str:
        # filled in by the engine which knows balls_per_over
        return self._overs_str

    _overs_str: str = "0.0"

    @property
    def economy(self) -> float:
        # set by engine (needs balls_per_over); fallback assumes 6
        return self._economy

    _economy: float = 0.0


@dataclass
class FallOfWicket:
    wicket: int
    score: int
    batter_out: str
    over: str


@dataclass
class Partnership:
    """A stand between two batters, delimited by wickets (a projection of the ball
    log). ``wicket`` is which wicket the stand is FOR (1 = the opening stand)."""

    wicket: int
    runs: int
    balls: int
    batter_a: str
    batter_b: str
    unbroken: bool = False

    @property
    def run_rate(self) -> float:
        return round(6.0 * self.runs / self.balls, 2) if self.balls else 0.0


@dataclass
class WagonShot:
    """One scoring shot for the wagon wheel — direction normalised to -1..1
    from the striker's position (x = off/leg, y = behind/in front)."""

    x: float
    y: float
    runs: int
    batter: str
    over: str
    ball: str = ""          # precise over.ball, e.g. "12.4"
    bowler: str = ""
    wicket: bool = False


@dataclass
class PitchMark:
    """One delivery on the pitch map — line x (-1 leg .. +1 off), length y
    (0 = yorker/at the batter .. 1 = bouncer). A projection of one ball event."""

    x: float
    y: float
    runs: int               # team runs off the delivery
    wicket: bool
    bowler: str
    batter: str
    over: str               # over.ball
    speed: Optional[float] = None


@dataclass
class BallComment:
    """One auto-generated ball-by-ball commentary line (a projection of one event)."""

    over_ball: str   # e.g. "12.3" (completed_overs.ball_in_over)
    kind: str        # dot|run|four|six|wide|noball|bye|legbye|wicket
    runs: int        # team runs off the delivery
    bowler: str
    striker: str
    text: str
    free_hit: bool = False  # was THIS delivery a free hit (not the next one)


@dataclass
class InningsScorecard:
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
    batters: list[BatterCard]
    bowlers: list[BowlerCard]
    fall_of_wickets: list[FallOfWicket]
    partnerships: list[Partnership]
    this_over: list[str]
    manhattan: list[int]
    worm: list[int]
    wagon: list[WagonShot]
    pitch: list[PitchMark]
    striker: Optional[str]
    non_striker: Optional[str]
    bowler: Optional[str]
    free_hit: bool
    is_complete: bool
    target: Optional[int] = None
    required_runs: Optional[int] = None
    balls_remaining: Optional[int] = None
    required_run_rate: Optional[float] = None
    result_note: Optional[str] = None
    current_over: int = 1
    in_powerplay: bool = False
    powerplay_label: Optional[str] = None
    fielders_outside_limit: Optional[int] = None


# --------------------------------------------------------------------------- #
# Innings engine
# --------------------------------------------------------------------------- #
class InningsEngine:
    def __init__(
        self,
        rules: MatchRules,
        batting_team: str,
        bowling_team: str,
        batting_order: list[str],
        bowling_order: Optional[list[str]] = None,
        target: Optional[int] = None,
    ):
        if len(batting_order) < 2:
            raise ValueError("need at least 2 batters")
        self.rules = rules
        self.batting_team = batting_team
        self.bowling_team = bowling_team
        self.batting_order = list(batting_order)
        self.bowling_order = list(bowling_order or [])
        self.target = target
        self.events: list[BallEvent] = []
        self._staged_bowler: Optional[str] = None
        self._declared = False  # captain's declaration — survives rebuilds
        self._rebuild()

    # ---- public API ----

    def set_bowler(self, name: str) -> None:
        """Stage the bowler for the upcoming over (live scoring path only).

        Deliberately does *no* validation so a stored match always reloads — the
        live scoring path validates with ``ensure_bowler_eligible`` before calling
        this, and ``record`` re-checks when the first ball is bowled."""
        self._staged_bowler = name

    def _consecutive_block(self, bowler: str) -> bool:
        return (not self.rules.allow_consecutive_overs) and bowler == self._last_over_bowler

    def _over_limit_reached(self, bowler: str) -> bool:
        return bool(self.rules.max_overs_per_bowler) and (
            self._completed_overs_by.get(bowler, 0) >= self.rules.max_overs_per_bowler
        )

    def ensure_bowler_eligible(self, bowler: str) -> None:
        """Raise if `bowler` may not bowl the upcoming over (back-to-back overs or
        their over allocation is used up)."""
        if self._consecutive_block(bowler):
            raise RuleViolation("a bowler cannot bowl consecutive overs")
        if self._over_limit_reached(bowler):
            done = self._completed_overs_by.get(bowler, 0)
            raise RuleViolation(
                f"{bowler} has already bowled {done} overs (max {self.rules.max_overs_per_bowler})"
            )

    def eligible_bowlers(self) -> list[str]:
        """Bowlers who may bowl the upcoming over — the bowling order minus whoever
        bowled the previous over (no back-to-back overs) and anyone who's used up
        their over allocation. Falls back to the full order if that strands the
        scorer with nobody to pick."""
        out = [b for b in self.bowling_order if not self._consecutive_block(b) and not self._over_limit_reached(b)]
        return out or list(self.bowling_order)

    def record(self, event: BallEvent) -> None:
        """Validate, stamp, append and fold one delivery."""
        if self._complete:
            raise InningsComplete("the innings is over")

        if self._awaiting_new_over:
            bowler = self._staged_bowler
            if not bowler:
                raise NeedBowler("set a bowler for the new over")
            self.ensure_bowler_eligible(bowler)
            self._awaiting_new_over = False
            event.bowler = bowler
        else:
            event.bowler = self._current_bowler

        event.striker = self.ends[self._striker_end]
        self.events.append(event)
        self._apply(event)
        self._staged_bowler = None

    def undo(self) -> Optional[BallEvent]:
        """Remove the last delivery and replay everything before it."""
        if not self.events:
            return None
        last = self.events.pop()
        self._rebuild()
        return last

    def edit_event(self, index: int, new_event: BallEvent) -> None:
        """Replace the delivery at `index` and replay. The over's bowler is kept
        (only the outcome changes). Rolls back if the edit makes the log illegal."""
        if not 0 <= index < len(self.events):
            raise IndexError("no such delivery")
        old = self.events[index]
        new_event.bowler = old.bowler
        self.events[index] = new_event
        try:
            self._rebuild()
        except Exception:
            self.events[index] = old
            self._rebuild()
            raise

    def delete_event(self, index: int) -> BallEvent:
        """Remove the delivery at `index` and replay. Rolls back on failure."""
        if not 0 <= index < len(self.events):
            raise IndexError("no such delivery")
        removed = self.events.pop(index)
        try:
            self._rebuild()
        except Exception:
            self.events.insert(index, removed)
            self._rebuild()
            raise
        return removed

    @property
    def is_complete(self) -> bool:
        return self._complete

    @property
    def awaiting_new_over(self) -> bool:
        """True when a bowler still needs to be chosen for a new over."""
        return self._awaiting_new_over and self._staged_bowler is None and not self._complete

    @property
    def over_pending(self) -> bool:
        """True between overs — a bowler may be chosen *or changed* right up until
        the first ball of the new over is bowled, even if one is already staged."""
        return self._awaiting_new_over and not self._complete

    @property
    def current_bowler(self) -> Optional[str]:
        return self._current_bowler

    @property
    def staged_bowler(self) -> Optional[str]:
        """Bowler chosen for the upcoming over but not yet bound to a delivery.

        Transient live state — persisted separately so a rebuilt match can resume
        scoring without re-selecting the bowler.
        """
        return self._staged_bowler

    def load_events(self, events: list[BallEvent]) -> None:
        """Replace the event log and replay it. Used to rebuild from storage."""
        self.events = list(events)
        self._rebuild()

    def set_result_note(self, note: str) -> None:
        self._result_note = note

    def declare(self) -> None:
        """Close this innings early (a captain's declaration)."""
        self._declared = True
        self._complete = True
        if not self._result_note:
            self._result_note = "Declared"

    # ---- internals ----

    def _rebuild(self) -> None:
        r = self.rules
        self.runs = 0
        self.wickets = 0
        self.legal_balls = 0
        self.extras = {"wides": 0, "no_balls": 0, "byes": 0, "leg_byes": 0, "penalty": 0}
        self.batters: dict[str, BatterCard] = {}
        self.bowlers: dict[str, BowlerCard] = {}
        self._bowler_seq = 0
        self.fall_of_wickets: list[FallOfWicket] = []
        self.commentary: list[BallComment] = []  # ball-by-ball, rebuilt with the log
        self.ends: list[Optional[str]] = [self.batting_order[0], self.batting_order[1]]
        self._striker_end = 0
        self._next_batter_index = 2
        self._current_bowler: Optional[str] = None
        self._last_over_bowler: Optional[str] = None
        self._completed_overs_by: dict[str, int] = {}
        self._legal_balls_this_over = 0
        self._over_runs_charged = 0
        self._over_had_wide_or_nb = False
        self._over_team_runs = 0
        self._current_over_symbols: list[str] = []
        self._completed_over_symbols: list[list[str]] = []
        self.manhattan: list[int] = []
        self.wagon_shots: list[WagonShot] = []
        self.pitch_marks: list[PitchMark] = []
        self.free_hit = False
        self._awaiting_new_over = True
        self._complete = False
        self._result_note: Optional[str] = None
        # seed opener cards
        self._bat(self.batting_order[0]).has_batted = True
        self._bat(self.batting_order[1]).has_batted = True
        for e in self.events:
            self._apply(e)
        if getattr(self, "_declared", False):  # a declared innings stays closed
            self._complete = True
            if not self._result_note:
                self._result_note = "Declared"

    def _bat(self, name: str) -> BatterCard:
        c = self.batters.get(name)
        if c is None:
            try:
                order = self.batting_order.index(name) + 1
            except ValueError:
                order = len(self.batters) + 1
            c = BatterCard(name=name, order=order)
            self.batters[name] = c
        return c

    def _bowl(self, name: str) -> BowlerCard:
        c = self.bowlers.get(name)
        if c is None:
            self._bowler_seq += 1
            c = BowlerCard(name=name, order=self._bowler_seq)
            self.bowlers[name] = c
        return c

    def _overs_str(self, legal_balls: int) -> str:
        bpo = self.rules.balls_per_over
        return f"{legal_balls // bpo}.{legal_balls % bpo}"

    def _balls_from_overs_str(self, ov: str) -> int:
        bpo = self.rules.balls_per_over
        o, _, b = str(ov).partition(".")
        return int(o) * bpo + (int(b) if b else 0)

    def _partnerships(self) -> list["Partnership"]:
        """Every stand of the innings, split by wicket — a pure projection over the
        fall-of-wickets + batting order. Partnership runs include extras (as real
        scorecards do), so they're the running-score deltas between wickets.
        (Retired-hurt replacements aren't in the fall list, so a stand spanning a
        retirement may name the pre-retirement pair — a rare grassroots edge.)"""
        out: list[Partnership] = []
        crease = [self.batting_order[0], self.batting_order[1]]
        nxt = 2
        prev_score = 0
        prev_balls = 0
        for fw in self.fall_of_wickets:
            end_balls = self._balls_from_overs_str(fw.over)
            out.append(Partnership(
                wicket=fw.wicket, runs=fw.score - prev_score, balls=end_balls - prev_balls,
                batter_a=crease[0] or "", batter_b=crease[1] or "", unbroken=False,
            ))
            slot = 0 if crease[0] == fw.batter_out else 1
            crease[slot] = self.batting_order[nxt] if nxt < len(self.batting_order) else None
            if nxt < len(self.batting_order):
                nxt += 1
            prev_score, prev_balls = fw.score, end_balls
        # the current, unbroken stand (two batters still at the crease)
        a, b = self.ends[0], self.ends[1]
        if a and b and (self.runs > prev_score or self.legal_balls > prev_balls):
            out.append(Partnership(
                wicket=len(self.fall_of_wickets) + 1, runs=self.runs - prev_score,
                balls=self.legal_balls - prev_balls, batter_a=a, batter_b=b, unbroken=True,
            ))
        return out

    def _resolve_strike(self) -> None:
        """If the on-strike slot is empty (last-man-stands lone batter), flip."""
        if self.ends[self._striker_end] is None and self.ends[1 - self._striker_end] is not None:
            self._striker_end ^= 1

    def _apply(self, event: BallEvent) -> None:  # noqa: C901 - inherently branchy
        r = self.rules
        prior_legal = self.legal_balls   # for the over.ball label of this delivery
        self._last_wicket_text = None    # set by _handle_wicket if a wicket falls
        start_striker_end = self._striker_end
        striker = self.ends[start_striker_end]
        non_striker = self.ends[1 - start_striker_end]
        bowler = event.bowler
        self._current_bowler = bowler
        # A delivery is being bowled, so we're no longer awaiting a new over's
        # bowler. (`record` already cleared this live; setting it here makes
        # REPLAY — used by undo and DB rebuild — restore the flag correctly.)
        self._awaiting_new_over = False
        bcard = self._bowl(bowler)
        scard = self._bat(striker)
        scard.has_batted = True
        was_free_hit = self.free_hit

        extra = event.extra
        legal_ball = True
        ball_faced = True
        off_bat = 0
        team_add = 0
        bowler_charged = 0
        swap_runs = 0
        is_wide = is_nb = False
        symbol = ""

        if extra is None:
            off_bat = event.runs_off_bat
            team_add = bowler_charged = swap_runs = off_bat
            symbol = "•" if off_bat == 0 else str(off_bat)
        elif extra is ExtraType.WIDE:
            if not r.wide.enabled:
                raise RuleViolation("wides are disabled in this format")
            legal_ball = r.wide.counts_as_legal_ball
            ball_faced = False
            ran = event.extra_runs if r.wide.allow_byes else 0
            penalty = r.wide.run_penalty
            team_add = bowler_charged = penalty + ran
            self.extras["wides"] += penalty + ran
            swap_runs = ran
            is_wide = True
            symbol = "Wd" if ran == 0 else f"{ran}+Wd"
        elif extra is ExtraType.NO_BALL:
            if not r.no_ball.enabled:
                raise RuleViolation("no-balls are disabled in this format")
            legal_ball = r.no_ball.counts_as_legal_ball
            penalty = r.no_ball.run_penalty
            off_bat = event.runs_off_bat if r.no_ball.off_bat_counts else 0
            byes = event.extra_runs if r.no_ball.allow_byes else 0
            team_add = penalty + off_bat + byes
            bowler_charged = penalty + off_bat
            self.extras["no_balls"] += penalty
            if byes:
                self.extras["byes"] += byes
            swap_runs = off_bat + byes
            is_nb = True
            symbol = "Nb" if off_bat == 0 else f"{off_bat}+Nb"
        elif extra is ExtraType.BYE:
            if not r.byes_allowed:
                raise RuleViolation("byes are disabled in this format")
            byes = event.extra_runs
            team_add = byes
            self.extras["byes"] += byes
            swap_runs = byes
            symbol = f"{byes}B"
        elif extra is ExtraType.LEG_BYE:
            if not r.leg_byes_allowed:
                raise RuleViolation("leg-byes are disabled in this format")
            lb = event.extra_runs
            team_add = lb
            self.extras["leg_byes"] += lb
            swap_runs = lb
            symbol = f"{lb}L"

        # credit batter
        if ball_faced:
            scard.balls += 1
        scard.runs += off_bat
        if extra is None or extra is ExtraType.NO_BALL:
            if off_bat == r.four_value:
                scard.fours += 1
            elif off_bat == r.six_value:
                scard.sixes += 1
            # wagon-wheel shot (direction is optional; only when the scorer marks it)
            if event.wagon_x is not None and event.wagon_y is not None:
                _ob = f"{prior_legal // r.balls_per_over}.{prior_legal % r.balls_per_over + 1}"
                self.wagon_shots.append(
                    WagonShot(
                        x=event.wagon_x, y=event.wagon_y, runs=off_bat,
                        batter=striker, over=self._overs_str(prior_legal),
                        ball=_ob, bowler=bowler or "", wicket=event.wicket is not None,
                    )
                )

        # pitch map: where the delivery bounced — any delivery the scorer marks
        if event.pitch_x is not None and event.pitch_y is not None:
            _pb = f"{prior_legal // r.balls_per_over}.{prior_legal % r.balls_per_over + 1}"
            self.pitch_marks.append(
                PitchMark(
                    x=event.pitch_x, y=event.pitch_y, runs=team_add,
                    wicket=event.wicket is not None, bowler=bowler or "", batter=striker or "",
                    over=_pb, speed=event.speed,
                )
            )

        # credit bowler
        if legal_ball:
            bcard.legal_balls += 1
        bcard.runs += bowler_charged
        if is_wide:
            bcard.wides += 1
        if is_nb:
            bcard.no_balls += 1

        # team totals
        self.runs += team_add
        self._over_team_runs += team_add
        self._over_runs_charged += bowler_charged
        if is_wide or is_nb:
            self._over_had_wide_or_nb = True
        if legal_ball:
            self.legal_balls += 1
            self._legal_balls_this_over += 1

        # wicket
        wkt = event.wicket
        if wkt is not None:
            self._handle_wicket(event, striker, non_striker, start_striker_end, swap_runs, was_free_hit, bcard, symbol)
        else:
            self._current_over_symbols.append(symbol)

        # strike rotation from running (odd completed runs cross the batters)
        if swap_runs % 2 == 1:
            self._striker_end ^= 1
        self._resolve_strike()

        # free-hit state for the *next* delivery
        if is_nb and r.no_ball.free_hit:
            self.free_hit = True
        elif legal_ball:
            self.free_hit = False
        # (a wide keeps an existing free hit alive)

        # ball-by-ball commentary (uses this delivery's already-computed outcome)
        self._record_comment(prior_legal, bowler, striker, extra, off_bat, swap_runs, team_add, was_free_hit)

        # over completion
        if legal_ball and self._legal_balls_this_over >= r.balls_per_over:
            self._complete_over(bowler, bcard)

        self._check_innings_end()

    def _record_comment(self, prior_legal, bowler, striker, extra, off_bat, swap_runs, team_add, was_free_hit=False) -> None:
        bpo = self.rules.balls_per_over
        over_ball = f"{prior_legal // bpo}.{prior_legal % bpo + 1}"
        who = f"{bowler or '—'} to {striker or '—'}"
        plural = lambda n: "" if n == 1 else "s"
        if self._last_wicket_text:
            kind, text = "wicket", f"{who}, OUT! {self._last_wicket_text}"
        elif extra is ExtraType.WIDE:
            kind = "wide"
            text = f"{who}, wide" + (f" + {swap_runs} run{plural(swap_runs)}" if swap_runs else "")
        elif extra is ExtraType.NO_BALL:
            kind = "noball"
            text = f"{who}, no ball" + (f", {off_bat} off the bat" if off_bat else "")
        elif extra is ExtraType.BYE:
            kind, text = "bye", f"{who}, {team_add} bye{plural(team_add)}"
        elif extra is ExtraType.LEG_BYE:
            kind, text = "legbye", f"{who}, {team_add} leg bye{plural(team_add)}"
        elif off_bat == self.rules.six_value:
            kind, text = "six", f"{who}, SIX!"
        elif off_bat == self.rules.four_value:
            kind, text = "four", f"{who}, FOUR!"
        elif off_bat == 0:
            kind, text = "dot", f"{who}, no run"
        else:
            kind, text = "run", f"{who}, {off_bat} run{plural(off_bat)}"
        self.commentary.append(
            BallComment(
                over_ball=over_ball, kind=kind, runs=team_add, bowler=bowler or "",
                striker=striker or "", text=text, free_hit=was_free_hit,
            )
        )

    def _handle_wicket(self, event, striker, non_striker, start_striker_end, swap_runs, was_free_hit, bcard, symbol):
        wkt = event.wicket
        dtype = wkt.type
        # free-hit protection: only run-out etc. allowed
        if was_free_hit and not dtype.allowed_on_free_hit:
            self._current_over_symbols.append(symbol)
            return
        if not self.rules.dismissal_allowed(dtype):
            self._current_over_symbols.append(symbol)
            return

        out_name = striker if wkt.batter_out == "striker" else non_striker
        out_slot = start_striker_end if wkt.batter_out == "striker" else 1 - start_striker_end
        ocard = self._bat(out_name)

        if dtype.is_not_out:
            # retired hurt — leaves not out, no wicket charged, may be replaced
            ocard.dismissal_text = "retired hurt"
            self._last_wicket_text = f"{out_name} retired hurt"
        else:
            ocard.out = True
            ocard.how_out = dtype
            ocard.dismissal_text = self._describe(dtype, event.bowler, wkt.fielder)
            self._last_wicket_text = f"{out_name} {ocard.dismissal_text}"
            ocard.fielder = event.bowler if dtype is DismissalType.CAUGHT_AND_BOWLED else wkt.fielder
            ocard.out_bowler = event.bowler if dtype.credited_to_bowler else None
            if dtype.credited_to_bowler:
                bcard.wickets += 1
            self.wickets += 1
            self.fall_of_wickets.append(
                FallOfWicket(
                    wicket=self.wickets,
                    score=self.runs,
                    batter_out=out_name,
                    over=self._overs_str(self.legal_balls),
                )
            )
            self._current_over_symbols.append("W" if symbol in ("•", "") else f"{symbol}+W")

        # caught-crossing with no runs (run-out crossing is already in swap_runs)
        if wkt.crossed and dtype in {
            DismissalType.CAUGHT,
            DismissalType.CAUGHT_BEHIND,
            DismissalType.CAUGHT_AND_BOWLED,
        } and swap_runs % 2 == 0:
            self._striker_end ^= 1

        # bring in a replacement (or go to lone-batter mode)
        if self._next_batter_index < len(self.batting_order):
            incoming = self.batting_order[self._next_batter_index]
            self._next_batter_index += 1
            self.ends[out_slot] = incoming
            self._bat(incoming).has_batted = True
        else:
            self.ends[out_slot] = None  # nobody left to come in

    def _complete_over(self, bowler: str, bcard: BowlerCard) -> None:
        if self._over_runs_charged == 0 and not self._over_had_wide_or_nb:
            bcard.maidens += 1
        self._completed_over_symbols.append(self._current_over_symbols)
        self.manhattan.append(self._over_team_runs)
        self._completed_overs_by[bowler] = self._completed_overs_by.get(bowler, 0) + 1
        self._last_over_bowler = bowler
        self._current_bowler = None
        self._awaiting_new_over = True
        # reset per-over counters
        self._legal_balls_this_over = 0
        self._over_runs_charged = 0
        self._over_had_wide_or_nb = False
        self._over_team_runs = 0
        self._current_over_symbols = []
        # end-of-over strike swap
        self._striker_end ^= 1
        self._resolve_strike()

    def _check_innings_end(self) -> None:
        r = self.rules
        if self.wickets >= r.wickets_to_all_out:
            self._complete = True
            if not self._result_note:
                self._result_note = "All out"
        elif self.legal_balls >= r.total_legal_balls:
            self._complete = True
            if not self._result_note:
                self._result_note = "Innings complete (overs)"
        elif self.target is not None and self.runs >= self.target:
            self._complete = True

    @staticmethod
    def _describe(dtype: DismissalType, bowler: Optional[str], fielder: Optional[str]) -> str:
        b = bowler or "?"
        f = fielder or "?"
        return {
            DismissalType.BOWLED: f"b {b}",
            DismissalType.LBW: f"lbw b {b}",
            DismissalType.CAUGHT: f"c {f} b {b}",
            DismissalType.CAUGHT_BEHIND: f"c †{f} b {b}",
            DismissalType.CAUGHT_AND_BOWLED: f"c & b {b}",
            DismissalType.STUMPED: f"st †{f} b {b}",
            DismissalType.HIT_WICKET: f"hit wkt b {b}",
            DismissalType.RUN_OUT: f"run out ({f})",
            DismissalType.RETIRED_OUT: "retired out",
            DismissalType.OBSTRUCTING_FIELD: "obstructing the field",
            DismissalType.HIT_BALL_TWICE: "hit the ball twice",
            DismissalType.TIMED_OUT: "timed out",
            DismissalType.BOUNDARY_OUT: f"out (over boundary) b {b}",
        }.get(dtype, str(dtype.value))

    # ---- projection ----

    def scorecard(self) -> InningsScorecard:
        r = self.rules
        bpo = r.balls_per_over
        striker = self.ends[self._striker_end]
        non_striker = self.ends[1 - self._striker_end]

        for c in self.batters.values():
            c.on_strike = False
        if striker and not self.batters[striker].out:
            self.batters[striker].on_strike = True

        for c in self.bowlers.values():
            c._overs_str = self._overs_str(c.legal_balls)
            overs = c.legal_balls / bpo
            c._economy = round(c.runs / overs, 2) if overs else 0.0

        self.extras["total"] = (
            self.extras["wides"]
            + self.extras["no_balls"]
            + self.extras["byes"]
            + self.extras["leg_byes"]
            + self.extras["penalty"]
        )

        this_over = (
            self._current_over_symbols
            if self._current_over_symbols
            else (self._completed_over_symbols[-1] if self._completed_over_symbols else [])
        )

        manhattan = list(self.manhattan)
        if self._current_over_symbols:
            manhattan = manhattan + [self._over_team_runs]
        worm: list[int] = []
        running = 0
        for v in manhattan:
            running += v
            worm.append(running)

        overs_f = self.legal_balls / bpo
        run_rate = round(self.runs / overs_f, 2) if overs_f else 0.0

        # Which (1-based) over is in progress, and is it a fielding-restriction
        # powerplay? Only meaningful while the innings is live.
        current_over = self.legal_balls // bpo + 1
        active_pp = None if self._complete else r.active_powerplay(current_over)

        required_runs = balls_remaining = None
        rrr = None
        if self.target is not None and not self._complete:
            required_runs = max(0, self.target - self.runs)
            balls_remaining = max(0, r.total_legal_balls - self.legal_balls)
            if balls_remaining:
                rrr = round(required_runs / balls_remaining * bpo, 2)

        return InningsScorecard(
            batting_team=self.batting_team,
            bowling_team=self.bowling_team,
            runs=self.runs,
            wickets=self.wickets,
            legal_balls=self.legal_balls,
            overs_str=self._overs_str(self.legal_balls),
            max_overs=r.overs_per_innings,
            max_wickets=r.wickets_to_all_out,
            extras=dict(self.extras),
            run_rate=run_rate,
            batters=sorted(self.batters.values(), key=lambda c: c.order),
            bowlers=sorted(self.bowlers.values(), key=lambda c: c.order),
            fall_of_wickets=list(self.fall_of_wickets),
            partnerships=self._partnerships(),
            this_over=list(this_over),
            manhattan=manhattan,
            worm=worm,
            wagon=list(self.wagon_shots),
            pitch=list(self.pitch_marks),
            striker=striker,
            non_striker=non_striker,
            bowler=self._current_bowler,
            free_hit=self.free_hit,
            is_complete=self._complete,
            target=self.target,
            required_runs=required_runs,
            balls_remaining=balls_remaining,
            required_run_rate=rrr,
            result_note=self._result_note,
            current_over=current_over,
            in_powerplay=active_pp is not None,
            powerplay_label=(active_pp.label if active_pp else None),
            fielders_outside_limit=(
                None if self._complete
                else (active_pp.max_fielders_outside if active_pp else r.default_fielders_outside)
            ),
        )


# --------------------------------------------------------------------------- #
# Match engine (2 innings + super overs + result)
# --------------------------------------------------------------------------- #
@dataclass
class SuperOver:
    """One super-over round: a 1-over innings per side (all out at 2 wickets)."""

    bat_first: str  # team name that batted first this round
    first: "InningsEngine"
    second: Optional["InningsEngine"] = None


@dataclass
class MatchEngine:
    rules: MatchRules
    team_a: str
    team_b: str
    squad_a: list[str]
    squad_b: list[str]
    bat_first: str = ""  # team name batting first

    def __post_init__(self):
        if not self.bat_first:
            self.bat_first = self.team_a
        if self.bat_first == self.team_a:
            bt, bo, bat_order, bowl_order = self.team_a, self.team_b, self.squad_a, self.squad_b
        else:
            bt, bo, bat_order, bowl_order = self.team_b, self.team_a, self.squad_b, self.squad_a
        self._bat1, self._bowl1 = bt, bo
        self._bat1_order, self._bowl1_order = bat_order, bowl_order
        # innings 1 runs on its (possibly rain-reduced) over cap — derived from any
        # innings-1 interruptions on the rulebook, so replay honours them for free.
        self.innings1 = InningsEngine(self._reduced_rules(self._innings1_overs()), bt, bo, bat_order, bowl_order)
        self.innings2: Optional[InningsEngine] = None
        self.super_overs: list[SuperOver] = []
        self.current = self.innings1

    def commentary_feed(self) -> list[dict]:
        """Flat ball-by-ball commentary across every innings, in play order."""
        feed: list[dict] = []

        def add(inn: "InningsEngine", label: str) -> None:
            editable = inn is self.current  # only the live innings can be edited
            for i, c in enumerate(inn.commentary):
                feed.append({
                    "innings": label, "over_ball": c.over_ball, "kind": c.kind,
                    "runs": c.runs, "bowler": c.bowler, "striker": c.striker, "text": c.text,
                    "idx": i, "editable": editable, "free_hit": c.free_hit,
                })

        add(self.innings1, f"{self.innings1.batting_team} innings")
        if self.innings2 is not None:
            add(self.innings2, f"{self.innings2.batting_team} innings")
        for i, so in enumerate(self.super_overs, 1):
            add(so.first, f"Super over {i}")
            if so.second is not None:
                add(so.second, f"Super over {i}")
        return feed

    def highlights(self) -> list[dict]:
        """Auto 'best moments' reel from the ball log + cards — wickets, boundaries,
        batting milestones, notable bowling, innings summaries and the result. A pure
        projection (no video, no storage): every match gets highlights for free."""
        out: list[dict] = []

        def hl(innings, over_ball, kind, title, text, team, importance, ts=None):
            out.append({
                "innings": innings, "over_ball": over_ball, "kind": kind,
                "title": title, "text": text, "team": team, "importance": importance, "ts": ts,
            })

        seq = [(self.innings1, f"{self.innings1.batting_team} innings")]
        if self.innings2 is not None:
            seq.append((self.innings2, f"{self.innings2.batting_team} innings"))
        for i, so in enumerate(self.super_overs, 1):
            seq.append((so.first, f"Super over {i}"))
            if so.second is not None:
                seq.append((so.second, f"Super over {i}"))

        for inn, label in seq:
            sc = inn.scorecard()
            team = sc.batting_team
            for c, ev in zip(inn.commentary, inn.events):  # chronological wickets + boundaries
                if c.kind == "wicket":
                    hl(label, c.over_ball, "wicket", "WICKET", c.text, team, 4, ev.ts)
                elif c.kind == "six":
                    hl(label, c.over_ball, "six", "SIX", c.text, team, 3, ev.ts)
                elif c.kind == "four":
                    hl(label, c.over_ball, "four", "FOUR", c.text, team, 2, ev.ts)
            for b in sc.batters:  # batting milestones (from the final card)
                if not b.has_batted:
                    continue
                if b.runs >= 100:
                    hl(label, "", "hundred", "HUNDRED", f"{b.name} — {b.runs} ({b.balls})", team, 5)
                elif b.runs >= 50:
                    hl(label, "", "fifty", "FIFTY", f"{b.name} — {b.runs} ({b.balls})", team, 4)
            for w in sc.bowlers:  # notable bowling
                if w.wickets >= 3:
                    hl(label, "", "bowling", f"{w.wickets} WICKETS",
                       f"{w.name} — {w.wickets}/{w.runs} ({w.overs_str})", sc.bowling_team, 4)
            hl(label, "", "innings", "INNINGS", f"{team} {sc.runs}/{sc.wickets} ({sc.overs_str})", team, 3)

        # DLS rain interruptions → the timeline (Rain Delay → Play Resumed → DLS Applied)
        if self.rules.dls_enabled and self.rules.interruptions:
            _RL = {"rain": "Rain", "bad_light": "Bad light", "wet_outfield": "Wet outfield",
                   "ground_delay": "Ground delay", "power_failure": "Power failure", "other": "Interruption"}
            for it in self.rules.interruptions:
                rl = _RL.get(it.reason, it.reason)
                hl(f"Innings {it.innings}", "", "dls", f"{rl.upper()} DELAY", f"Play stopped — {rl.lower()}", None, 3)
                if not it.pending:
                    hl(f"Innings {it.innings}", "", "dls", "PLAY RESUMED",
                       f"{it.overs_lost} over(s) lost to the break", None, 3)
            if self.innings2 is not None:
                hl("Innings 2", "", "dls", "DLS APPLIED",
                   f"Revised target {self.innings2.target} from {self._innings2_overs()} overs", None, 4)
        if self.rules.abandoned:
            hl("Result", "", "dls", "MATCH ABANDONED",
               f"Abandoned — {self.rules.abandon_reason or 'rain'}", None, 5)

        if self.result:
            hl("Result", "", "result", "RESULT", self.result, None, 6)
        return out

    def awards(self) -> Optional[dict]:
        """Auto Man-of-the-Match + best batter / best bowler for a finished match.

        A transparent impact score per player across both innings:
          batting = runs + 4s + 2·6s + milestone (50→16, 100→32)
          bowling = 25·wickets + 10·maidens
          fielding = 10·catch + 12·stumping + 8·run-out (credited to the fielder)
        MoM is the highest total; ties break toward the winning side. Returns None
        until the match has a result.
        """
        if self.result is None:
            return None
        catches = {DismissalType.CAUGHT, DismissalType.CAUGHT_BEHIND, DismissalType.CAUGHT_AND_BOWLED}
        bat_pts: dict[str, int] = {}
        bowl_pts: dict[str, int] = {}
        field_pts: dict[str, int] = {}
        bat_line: dict[str, str] = {}
        bowl_line: dict[str, str] = {}
        team_of: dict[str, str] = {}

        innings = [self.innings1] + ([self.innings2] if self.innings2 is not None else [])
        for inn in innings:
            sc = inn.scorecard()
            for b in sc.batters:
                if not b.has_batted:
                    continue
                team_of[b.name] = sc.batting_team
                milestone = 32 if b.runs >= 100 else 16 if b.runs >= 50 else 0
                bat_pts[b.name] = bat_pts.get(b.name, 0) + b.runs + b.fours + 2 * b.sixes + milestone
                bat_line[b.name] = f"{b.runs}{'' if b.out else '*'} ({b.balls})"
                if b.out and b.fielder:
                    add = 10 if b.how_out in catches else 12 if b.how_out is DismissalType.STUMPED else 8 if b.how_out is DismissalType.RUN_OUT else 0
                    if add:
                        field_pts[b.fielder] = field_pts.get(b.fielder, 0) + add
            for w in sc.bowlers:
                if w.legal_balls == 0 and w.wickets == 0:
                    continue
                team_of[w.name] = sc.bowling_team
                bowl_pts[w.name] = bowl_pts.get(w.name, 0) + 25 * w.wickets + 10 * w.maidens
                bowl_line[w.name] = f"{w.wickets}/{w.runs} ({w.overs_str})"

        names = set(bat_pts) | set(bowl_pts) | set(field_pts)
        if not names:
            return None
        total = {n: bat_pts.get(n, 0) + bowl_pts.get(n, 0) + field_pts.get(n, 0) for n in names}
        winner = self.winner_team if self.winner_team not in (None, "tie") else None

        def best(scores: dict[str, int], pool=None) -> Optional[str]:
            cands = [n for n in scores if pool is None or n in pool]
            if not cands:
                return None
            pick = max(cands, key=lambda n: (scores[n], 1 if team_of.get(n) == winner else 0, n))
            return pick if scores[pick] > 0 else None

        def line_for(n: str) -> str:
            parts = []
            if bat_pts.get(n, 0) > 0 and n in bat_line:
                parts.append(bat_line[n])
            if bowl_pts.get(n, 0) > 0 and n in bowl_line:
                parts.append(bowl_line[n])
            return " & ".join(parts) or "all-round effort"

        def entry(n, line):
            return {"name": n, "team": team_of.get(n), "line": line} if n else None

        mom = best(total)
        bb = best(bat_pts)
        bw = best(bowl_pts)
        return {
            "man_of_the_match": entry(mom, line_for(mom)) if mom else None,
            "best_batter": entry(bb, bat_line.get(bb, "")) if bb else None,
            "best_bowler": entry(bw, bowl_line.get(bw, "")) if bw else None,
        }

    def declare(self) -> None:
        """Declare the current innings closed (captain's declaration). Records the
        declared innings on the rulebook so it persists and replays as complete."""
        if not self.rules.allow_declaration:
            raise ScoringError("declarations are not enabled for this match")
        inn = self.current
        num = 1 if inn is self.innings1 else 2 if inn is self.innings2 else None
        if num is None:
            raise ScoringError("cannot declare during a super over")
        if inn.is_complete:
            raise ScoringError("the current innings is already complete")
        self.rules = self.rules.model_copy(update={"declared_innings": num})
        inn.declare()

    def _make_innings2(self) -> InningsEngine:
        """Build the chasing innings, applying any DLS revision.

        Rain interruptions drive the target automatically (the scorer only confirms
        overs); a manually-set revised_target is honoured only when there are no
        interruptions (the legacy manual path)."""
        if self.rules.dls_enabled and self.rules.interruptions:
            target = self._dls_target()               # auto: computed from resources
        elif self.rules.revised_target is not None:
            target = self.rules.revised_target         # legacy manual override
        else:
            target = self.innings1.runs + 1
        # A revised-overs chase runs on a copy of the rulebook with a shorter
        # innings; model_copy skips validation, so powerplays beyond the new
        # length simply never fire (they're clamped by active_powerplay()).
        overs = self.rules.revised_overs
        if overs is None and self.rules.interruptions:
            reduced = self._innings2_overs()
            if reduced != self.rules.overs_per_innings:
                overs = reduced
        inn_rules = self._reduced_rules(overs) if overs else self.rules
        if self._bat1 == self.team_a:
            bt, bo, bat_order, bowl_order = self.team_b, self.team_a, self.squad_b, self.squad_a
        else:
            bt, bo, bat_order, bowl_order = self.team_a, self.team_b, self.squad_a, self.squad_b
        return InningsEngine(inn_rules, bt, bo, bat_order, bowl_order, target=target)

    def start_second_innings(self) -> InningsEngine:
        if not self.innings1.is_complete:
            raise ScoringError("first innings is not complete")
        self.innings2 = self._make_innings2()
        self.current = self.innings2
        return self.innings2

    def set_revised_target(self, target: int, overs: Optional[int] = None) -> None:
        """Apply a DLS-style revised target (and optional reduced overs).

        Stored on the match's own rulebook (so it persists in the rules JSON).
        If the chase is already under way, the innings is rebuilt from its
        existing deliveries against the new target/overs.
        """
        if not self.rules.dls_enabled:
            raise ScoringError("DLS is not enabled for this match")
        if target < 1:
            raise ScoringError("revised target must be at least 1")
        if overs is not None and overs < 1:
            raise ScoringError("revised overs must be at least 1")
        if self.innings2 is not None and overs is not None:
            if overs * self.rules.balls_per_over < self.innings2.legal_balls:
                raise ScoringError("revised overs can't be fewer than the overs already bowled")
        self.rules = self.rules.model_copy(
            update={"revised_target": int(target), "revised_overs": (int(overs) if overs else None)}
        )
        if self.innings2 is not None:
            events = list(self.innings2.events)
            self.innings2 = self._make_innings2()
            self.innings2.load_events(events)
            self.current = self.innings2

    # ------------------------------------------------------------------ #
    # DLS rain interruptions — the scorer confirms overs; targets self-compute
    # ------------------------------------------------------------------ #
    def _reduced_rules(self, overs) -> MatchRules:
        """A rulebook copy capped at ``overs`` overs/innings (or self.rules unchanged)."""
        if not overs or int(overs) == self.rules.overs_per_innings:
            return self.rules
        return self.rules.model_copy(update={"overs_per_innings": int(overs)})

    def _cuts_for(self, innings: int):
        from app.domain import dls
        return [dls.Cut(it.overs_before, it.wickets, it.overs_after)
                for it in self.rules.interruptions if it.innings == innings and not it.pending]

    def _reduction_for(self, innings: int) -> float:
        return sum(it.overs_lost for it in self.rules.interruptions
                   if it.innings == innings and not it.pending)

    def _innings1_overs(self) -> int:
        return max(1, int(round(self.rules.overs_per_innings - self._reduction_for(1))))

    def _innings2_overs(self) -> int:
        base = self.rules.overs_per_innings - self._reduction_for(1)   # inherits the match shortening
        return max(1, int(round(base - self._reduction_for(2))))

    def _dls_min_overs(self) -> int:
        """Overs the chase must face for a DLS result to stand (ICC: 20 for a 50-over
        game, 5 for T20). Scaled down for short custom formats so it stays reachable."""
        if self.rules.dls_min_overs:
            return self.rules.dls_min_overs
        o = self.rules.overs_per_innings
        base = 20 if o >= 40 else 5 if o >= 10 else max(1, o // 2)
        return min(base, max(1, o - 1))

    def _dls_target(self) -> int:
        from app.domain import dls
        r1 = dls.innings_resources(self.rules.overs_per_innings, self._cuts_for(1))
        i2_base = self.rules.overs_per_innings - self._reduction_for(1)
        r2 = dls.innings_resources(i2_base, self._cuts_for(2))
        return dls.revised_target(self.innings1.runs, r1, r2, self.rules.g50)

    def _live_par(self) -> Optional[int]:
        """Current DLS par — the score team 2 should be level with right now — or None."""
        from app.domain import dls
        if self.innings2 is None:
            return None
        r1 = dls.innings_resources(self.rules.overs_per_innings, self._cuts_for(1))
        i2_base = self.rules.overs_per_innings - self._reduction_for(1)
        r2 = dls.innings_resources(i2_base, self._cuts_for(2))
        faced = self.innings2.legal_balls / self.rules.balls_per_over
        used = max(0.0, r2 - dls.resource_pct(max(0.0, self._innings2_overs() - faced), self.innings2.wickets))
        return dls.par_score(self.innings1.runs, r1, used)

    def _innings_no(self, inn) -> Optional[int]:
        return 1 if inn is self.innings1 else 2 if inn is self.innings2 else None

    def interrupt(self, reason: str = "rain", at: Optional[str] = None) -> None:
        """Record that play has stopped in the current innings (awaits resume + overs)."""
        if not self.rules.dls_enabled:
            raise ScoringError("DLS is not enabled for this match")
        if self.rules.abandoned:
            raise ScoringError("match has been abandoned")
        if any(it.pending for it in self.rules.interruptions):
            raise ScoringError("play is already interrupted — resume it first")
        inn_no = self._innings_no(self.current)
        if inn_no not in (1, 2):
            raise ScoringError("DLS applies to the main innings only")
        it = Interruption(innings=inn_no, reason=(reason or "rain"), balls=self.current.legal_balls,
                          wickets=self.current.wickets, interrupt_at=at, pending=True)
        self.rules = self.rules.model_copy(update={"interruptions": [*self.rules.interruptions, it]})

    def resume(self, new_overs: int, at: Optional[str] = None) -> None:
        """Resume after a stoppage with the interrupted innings cut to ``new_overs``
        total overs. Validates, records the overs lost; the target recomputes itself."""
        pend = next((it for it in self.rules.interruptions if it.pending), None)
        if pend is None:
            raise ScoringError("there is no interruption to resume")
        if new_overs is None or int(new_overs) < 1:
            raise ScoringError("revised overs must be at least 1")
        new_overs = int(new_overs)
        inn = self.innings1 if pend.innings == 1 else self.innings2
        bpo = self.rules.balls_per_over
        bowled = inn.legal_balls / bpo
        current_total = self._innings1_overs() if pend.innings == 1 else self._innings2_overs()
        if new_overs > current_total:
            raise ScoringError("revised overs can't exceed the current innings length")
        if new_overs * bpo < inn.legal_balls:
            raise ScoringError("revised overs can't be fewer than the overs already bowled")
        final = pend.model_copy(update={
            "overs_before": round(current_total - bowled, 3),
            "overs_after": round(new_overs - bowled, 3),
            "resume_at": at, "pending": False,
        })
        keep = [it for it in self.rules.interruptions if not it.pending]
        self.rules = self.rules.model_copy(update={"interruptions": [*keep, final]})
        self._rebuild_live()

    def cancel_interruption(self) -> None:
        """Drop a pending (not-yet-resumed) interruption — a false alarm."""
        self.rules = self.rules.model_copy(
            update={"interruptions": [it for it in self.rules.interruptions if not it.pending]})

    def abandon(self, reason: str = "rain") -> None:
        """Call the match off. Decided on DLS par if the chase passed the minimum
        overs, otherwise 'No result'."""
        if not self.rules.dls_enabled:
            raise ScoringError("DLS is not enabled for this match")
        self.rules = self.rules.model_copy(update={
            "interruptions": [it for it in self.rules.interruptions if not it.pending],
            "abandoned": True, "abandon_reason": (reason or "rain"),
        })

    def _rebuild_live(self) -> None:
        """Re-fold the current innings so a fresh overs-cap / target takes effect now."""
        if self.innings2 is not None:
            events = list(self.innings2.events)
            self.innings2 = self._make_innings2()
            self.innings2.load_events(events)
            self.current = self.innings2
        else:
            events = list(self.innings1.events)
            self.innings1 = InningsEngine(self._reduced_rules(self._innings1_overs()),
                                          self._bat1, self._bowl1, self._bat1_order, self._bowl1_order)
            self.innings1.load_events(events)
            self.current = self.innings1

    def _abandoned_result(self) -> str:
        from app.domain import dls
        if self.innings2 is None:
            return "Match abandoned — No result"
        faced = self.innings2.legal_balls / self.rules.balls_per_over
        if faced < self._dls_min_overs():
            return "Match abandoned — No result"
        par = self._live_par() or 0
        v = dls.verdict(self.innings2.runs, par)
        chasing, defending = self.innings2.batting_team, self.innings1.batting_team
        if v > 0:
            return f"{chasing} won by {self.innings2.runs - par} run(s) (DLS)"
        if v < 0:
            return f"{defending} won by {par - self.innings2.runs} run(s) (DLS)"
        return "Match tied (DLS)"

    def dls_summary(self) -> Optional[dict]:
        """The full DLS state for display (None when DLS is off)."""
        r = self.rules
        if not r.dls_enabled:
            return None
        from app.domain import dls
        done = [it for it in r.interruptions if not it.pending]
        r1 = dls.innings_resources(r.overs_per_innings, self._cuts_for(1))
        i2_base = r.overs_per_innings - self._reduction_for(1)
        r2 = dls.innings_resources(i2_base, self._cuts_for(2))
        target = par = None
        if self.innings2 is not None:
            target, par = self.innings2.target, self._live_par()
        elif self.innings1.is_complete and (done or r.revised_target):
            target = self._dls_target() if done else r.revised_target
        rev_overs = self._innings2_overs()
        return {
            "enabled": True,
            "applied": bool(done) or r.revised_target is not None or r.abandoned,
            "pending": any(it.pending for it in r.interruptions),
            "abandoned": r.abandoned,
            "abandon_reason": r.abandon_reason,
            "original_overs": r.overs_per_innings,
            "revised_overs": rev_overs if (done or r.revised_overs) and rev_overs != r.overs_per_innings else None,
            "revised_target": target,
            "par": par,
            "r1": round(r1, 1),
            "r2": round(r2, 1),
            "min_overs": self._dls_min_overs(),
            "overs_lost": round(self._reduction_for(1) + self._reduction_for(2), 2),
            "revision_seq": len(done),
            "interruptions": [
                {"innings": it.innings, "reason": it.reason, "overs_lost": it.overs_lost,
                 "wickets": it.wickets, "interrupt_at": it.interrupt_at,
                 "resume_at": it.resume_at, "pending": it.pending}
                for it in r.interruptions
            ],
        }

    @property
    def result(self) -> Optional[str]:
        if self.rules.abandoned:
            return self._abandoned_result()
        if self.innings2 is None or not self.innings2.is_complete:
            return None
        target = self.innings2.target
        par = target - 1  # the score that ties; reaching `target` wins
        second = self.innings2.runs
        chasing = self.innings2.batting_team
        defending = self.innings1.batting_team
        if second >= target:  # type: ignore[operator]
            wkts_left = self.rules.wickets_to_all_out - self.innings2.wickets
            return f"{chasing} won by {wkts_left} wicket(s)"
        if second < par:
            return f"{defending} won by {par - second} run(s)"
        # scores are level after the main match
        if self.rules.super_over_on_tie:
            won = self._super_over_winner()
            if won is not None:
                return f"{won} won (Super Over)"
            return None  # a super over is required / in progress — not decided yet
        return "Match tied"

    @property
    def winner_team(self) -> Optional[str]:
        """The winning team's name, "tie", or None if not yet decided."""
        if self.rules.abandoned:
            if self.innings2 is None:
                return None
            faced = self.innings2.legal_balls / self.rules.balls_per_over
            if faced < self._dls_min_overs():
                return None
            from app.domain import dls
            v = dls.verdict(self.innings2.runs, self._live_par() or 0)
            return (self.innings2.batting_team if v > 0
                    else self.innings1.batting_team if v < 0 else "tie")
        if self.innings2 is None or not self.innings2.is_complete:
            return None
        target = self.innings2.target
        if self.innings2.runs >= target:  # type: ignore[operator]
            return self.innings2.batting_team
        if self.innings2.runs < target - 1:
            return self.innings1.batting_team
        # tied main match
        if self.rules.super_over_on_tie:
            return self._super_over_winner()  # team name, or None until decided
        return "tie"

    # ----- super over (one-over eliminator on a tie) -----------------------

    def _main_tied(self) -> bool:
        return (
            self.innings2 is not None
            and self.innings2.is_complete
            and self.innings2.runs == self.innings2.target - 1  # chase finished exactly on par
        )

    def _super_rules(self) -> MatchRules:
        """A super-over rulebook: one over, all out at 2 wickets, no frills."""
        return self.rules.model_copy(update={
            "overs_per_innings": 1,
            "players_per_side": 3,  # wickets_to_all_out == 2
            "last_man_stands": False,
            "powerplays": [],
            "max_overs_per_bowler": None,
            "revised_target": None,
            "revised_overs": None,
            "super_over_on_tie": False,
        })

    def _round_result(self, so: SuperOver) -> Optional[str]:
        """Winner team name, ``"tie"``, or ``None`` if the round is unfinished."""
        if not so.first.is_complete:
            return None
        if so.second is None or not so.second.is_complete:
            return None
        target = so.second.target  # so.first.runs + 1
        if so.second.runs >= target:
            return so.second.batting_team
        if so.second.runs == target - 1:
            return "tie"
        return so.first.batting_team

    def _super_over_winner(self) -> Optional[str]:
        """The deciding super-over winner, if any round has produced one."""
        if not self.super_overs:
            return None
        last = self._round_result(self.super_overs[-1])
        return last if (last is not None and last != "tie") else None

    @property
    def super_over_in_progress(self) -> bool:
        return bool(self.super_overs) and self._round_result(self.super_overs[-1]) is None

    @property
    def awaiting_super_second(self) -> bool:
        """First super-over innings done, the reply not yet started."""
        if not self.super_overs:
            return False
        last = self.super_overs[-1]
        return last.second is None and last.first.is_complete

    @property
    def needs_super_over(self) -> bool:
        """A (further) super over should be started to break the tie."""
        if not self.rules.super_over_on_tie or not self._main_tied():
            return False
        if not self.super_overs:
            return True
        return self._round_result(self.super_overs[-1]) == "tie"  # last round also tied

    def _build_super_innings(self, batting_team: str, target: Optional[int] = None) -> InningsEngine:
        sr = self._super_rules()
        if batting_team == self.team_a:
            bt, bo, bat_order, bowl_order = self.team_a, self.team_b, self.squad_a, self.squad_b
        else:
            bt, bo, bat_order, bowl_order = self.team_b, self.team_a, self.squad_b, self.squad_a
        return InningsEngine(sr, bt, bo, bat_order, bowl_order, target=target)

    def _make_super_first(self, bat_first_team: str) -> SuperOver:
        inn = self._build_super_innings(bat_first_team)
        so = SuperOver(bat_first=bat_first_team, first=inn)
        self.super_overs.append(so)
        self.current = inn
        return so

    def _make_super_second(self) -> InningsEngine:
        so = self.super_overs[-1]
        other = self.team_b if so.bat_first == self.team_a else self.team_a
        so.second = self._build_super_innings(other, target=so.first.runs + 1)
        self.current = so.second
        return so.second

    def _sync_super_rounds(self) -> None:
        """Mirror the live super-over structure onto the rulebook for persistence."""
        rounds = [
            SuperOverRound(bat_first=so.bat_first, second_started=so.second is not None)
            for so in self.super_overs
        ]
        self.rules = self.rules.model_copy(update={"super_over_rounds": rounds})

    def _resolve_bat_first(self, token: Optional[str]) -> str:
        if token in (self.team_a, self.team_b):
            return token  # type: ignore[return-value]
        if token == "a":
            return self.team_a
        if token == "b":
            return self.team_b
        if not self.super_overs:
            return self.innings2.batting_team  # the chasing side bats first by default
        prev = self.super_overs[-1].bat_first  # otherwise swap from the previous round
        return self.team_b if prev == self.team_a else self.team_a

    def super_over(self, bat_first_team: Optional[str] = None) -> InningsEngine:
        """Start a super over, or begin the reply within the current round."""
        if not self.rules.super_over_on_tie:
            raise ScoringError("super over is not enabled for this match")
        # mid-round: the first innings is done, start the chase
        if self.super_overs and self.super_overs[-1].second is None:
            if not self.super_overs[-1].first.is_complete:
                raise ScoringError("finish the first super-over innings first")
            inn = self._make_super_second()
            self._sync_super_rounds()
            return inn
        # otherwise a brand-new round — only if the tie actually calls for one
        if not self.needs_super_over:
            raise ScoringError("a super over is not required")
        so = self._make_super_first(self._resolve_bat_first(bat_first_team))
        self._sync_super_rounds()
        return so.first
