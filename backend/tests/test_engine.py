"""Engine correctness tests — the contract the rest of CricNetra builds on."""

from __future__ import annotations

import pytest

from app.domain import presets
from app.domain.engine import (
    InningsComplete,
    InningsEngine,
    MatchEngine,
    NeedBowler,
    RuleViolation,
)
from app.domain.enums import DismissalType
from app.domain.events import BallEvent
from app.domain.rules import MatchRules

BAT = [f"bat{i}" for i in range(11)]
BOWL = [f"bowl{i}" for i in range(11)]


def fresh(rules: MatchRules | None = None, bat=None, target=None) -> InningsEngine:
    return InningsEngine(
        rules or presets.t20(),
        "Strikers",
        "Blasters",
        bat or BAT,
        BOWL,
        target=target,
    )


# --------------------------------------------------------------------------- #
# Basics: runs, over rollover, strike rotation, maiden
# --------------------------------------------------------------------------- #
def test_six_dots_complete_over_rotate_and_maiden():
    inn = fresh()
    inn.set_bowler("bowl0")
    for _ in range(6):
        inn.record(BallEvent.dot())
    sc = inn.scorecard()
    assert sc.runs == 0
    assert sc.legal_balls == 6
    assert sc.overs_str == "1.0"
    # opener0 faced all 6, then strike rotates to opener1 at end of over
    assert sc.striker == "bat1"
    assert inn.batters["bat0"].balls == 6
    assert inn.bowlers["bowl0"].maidens == 1


def test_wagon_wheel_shots_projection():
    """Scoring shots with a marked direction land in the wagon projection;
    plain shots and extras don't, and it survives a replay rebuild."""
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.runs(4, wagon_x=0.6, wagon_y=0.8))  # marked boundary
    inn.record(BallEvent.runs(1))                            # no direction marked
    inn.record(BallEvent.wide(ran=0, wagon_x=0.2, wagon_y=0.2))  # extra: not a shot
    wagon = inn.scorecard().wagon
    assert len(wagon) == 1
    assert (wagon[0].runs, wagon[0].x, wagon[0].y) == (4, 0.6, 0.8)
    assert wagon[0].batter == "bat0"

    # event-sourced: a fresh engine replaying the same log rebuilds the wagon
    rebuilt = InningsEngine(inn.rules, "Strikers", "Blasters", BAT, BOWL)
    rebuilt.load_events(inn.events)
    assert len(rebuilt.scorecard().wagon) == 1


def test_single_rotates_strike_within_over():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.runs(1))
    sc = inn.scorecard()
    assert sc.runs == 1
    assert sc.striker == "bat1"  # crossed on the single
    assert inn.batters["bat0"].runs == 1
    assert inn.batters["bat0"].balls == 1


def test_four_and_six_counted():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.runs(4))
    inn.record(BallEvent.runs(6))
    b0 = inn.batters["bat0"]
    assert b0.runs == 10 and b0.fours == 1 and b0.sixes == 1
    assert inn.bowlers["bowl0"].runs == 10


def test_need_bowler_before_first_ball():
    inn = fresh()
    with pytest.raises(NeedBowler):
        inn.record(BallEvent.dot())


def test_no_consecutive_overs():
    inn = fresh()
    inn.set_bowler("bowl0")
    for _ in range(6):
        inn.record(BallEvent.dot())
    inn.set_bowler("bowl0")  # same bowler again
    with pytest.raises(RuleViolation):
        inn.record(BallEvent.dot())


def test_eligible_bowlers_excludes_previous_over_bowler():
    """The picker must not offer the bowler who just bowled (no consecutive overs),
    so the scorer can't pick someone the next ball will reject."""
    inn = fresh()
    inn.set_bowler("bowl0")
    for _ in range(6):
        inn.record(BallEvent.dot())
    # between overs: a bowler is still needed, and bowl0 is no longer eligible
    assert inn.over_pending is True
    elig = inn.eligible_bowlers()
    assert "bowl0" not in elig and len(elig) == len(BOWL) - 1
    with pytest.raises(RuleViolation):
        inn.ensure_bowler_eligible("bowl0")
    # staging an eligible bowler keeps the over pending until the first ball
    inn.set_bowler("bowl1")
    assert inn.over_pending is True and inn.awaiting_new_over is False
    inn.record(BallEvent.dot())
    assert inn.over_pending is False


def test_eligible_bowlers_drops_maxed_out_bowler():
    rules = presets.t20()
    rules.max_overs_per_bowler = 1
    inn = fresh(rules)
    inn.set_bowler("bowl0")
    for _ in range(6):
        inn.record(BallEvent.dot())
    inn.set_bowler("bowl1")
    for _ in range(6):
        inn.record(BallEvent.dot())
    # bowl0 used its 1 over; bowl1 just bowled — neither is eligible now
    elig = inn.eligible_bowlers()
    assert "bowl0" not in elig and "bowl1" not in elig


def test_max_overs_per_bowler():
    rules = presets.t20()
    rules.max_overs_per_bowler = 1
    inn = fresh(rules)
    inn.set_bowler("bowl0")
    for _ in range(6):
        inn.record(BallEvent.dot())
    inn.set_bowler("bowl1")
    for _ in range(6):
        inn.record(BallEvent.dot())
    inn.set_bowler("bowl0")  # bowl0 already bowled its 1 allowed over
    with pytest.raises(RuleViolation):
        inn.record(BallEvent.dot())


# --------------------------------------------------------------------------- #
# Extras
# --------------------------------------------------------------------------- #
def test_wide_adds_run_no_legal_ball():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.wide())
    sc = inn.scorecard()
    assert sc.runs == 1
    assert sc.legal_balls == 0
    assert sc.extras["wides"] == 1
    assert inn.bowlers["bowl0"].wides == 1
    assert inn.bowlers["bowl0"].runs == 1
    assert inn.batters["bat0"].balls == 0  # striker didn't face a legal ball


def test_wide_with_byes_rotates_on_odd():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.wide(ran=1))  # 1 wide penalty + 1 run = 2, batters crossed
    sc = inn.scorecard()
    assert sc.runs == 2
    assert sc.extras["wides"] == 2
    assert sc.striker == "bat1"


def test_byes_not_charged_to_bowler():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.bye(2))
    sc = inn.scorecard()
    assert sc.runs == 2
    assert sc.legal_balls == 1
    assert sc.extras["byes"] == 2
    assert inn.bowlers["bowl0"].runs == 0
    assert inn.batters["bat0"].balls == 1
    assert inn.batters["bat0"].runs == 0


def test_leg_byes():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.leg_bye(1))
    sc = inn.scorecard()
    assert sc.extras["leg_byes"] == 1
    assert sc.runs == 1
    assert sc.striker == "bat1"


def test_no_ball_free_hit_protects_from_bowled():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.no_ball())
    assert inn.scorecard().free_hit is True
    # bowled on the free hit -> not out
    inn.record(BallEvent.out(DismissalType.BOWLED))
    sc = inn.scorecard()
    assert sc.wickets == 0
    assert inn.batters["bat0"].out is False
    assert sc.free_hit is False  # consumed by the legal delivery
    assert sc.legal_balls == 1


def test_no_ball_free_hit_allows_run_out():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.no_ball())
    inn.record(BallEvent.out(DismissalType.RUN_OUT, fielder="cover"))
    assert inn.scorecard().wickets == 1


def test_no_ball_off_bat_runs_to_batter():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.no_ball(off_bat=4))
    sc = inn.scorecard()
    assert sc.runs == 5  # 1 penalty + 4 off bat
    assert inn.batters["bat0"].runs == 4
    assert inn.batters["bat0"].fours == 1
    assert inn.bowlers["bowl0"].runs == 5


# --------------------------------------------------------------------------- #
# Wickets & new batter
# --------------------------------------------------------------------------- #
def test_bowled_brings_new_batter_on_strike():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.out(DismissalType.BOWLED))
    sc = inn.scorecard()
    assert sc.wickets == 1
    assert inn.batters["bat0"].out is True
    assert inn.batters["bat0"].how_out == DismissalType.BOWLED
    assert sc.striker == "bat2"  # next in order, on strike
    assert inn.bowlers["bowl0"].wickets == 1
    assert sc.fall_of_wickets[0].score == 0
    assert sc.fall_of_wickets[0].over == "0.1"


def test_wicket_last_ball_of_over_keeps_existing_batter_on_strike():
    inn = fresh()
    inn.set_bowler("bowl0")
    for _ in range(5):
        inn.record(BallEvent.dot())
    inn.record(BallEvent.out(DismissalType.BOWLED))  # 6th ball, striker out
    sc = inn.scorecard()
    # new batter came to striker's end, then over-swap -> existing batter on strike
    assert sc.striker == "bat1"
    assert sc.non_striker == "bat2"


def test_run_out_non_striker():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.out(DismissalType.RUN_OUT, batter_out="non_striker", fielder="mid-on"))
    sc = inn.scorecard()
    assert inn.batters["bat1"].out is True
    assert sc.striker == "bat0"  # striker unaffected
    assert inn.bowlers["bowl0"].wickets == 0  # run out not credited to bowler


# --------------------------------------------------------------------------- #
# UNDO
# --------------------------------------------------------------------------- #
def test_undo_restores_exact_state():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.runs(1))
    inn.record(BallEvent.runs(2))
    before = inn.scorecard()
    snapshot = (before.runs, before.striker, before.legal_balls, inn.batters["bat0"].runs)

    inn.record(BallEvent.runs(4))
    inn.undo()

    after = inn.scorecard()
    assert (after.runs, after.striker, after.legal_balls, inn.batters["bat0"].runs) == snapshot
    assert len(inn.events) == 2


def test_undo_a_wicket():
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.out(DismissalType.BOWLED))
    assert inn.scorecard().wickets == 1
    inn.undo()
    sc = inn.scorecard()
    assert sc.wickets == 0
    assert inn.batters["bat0"].out is False
    assert sc.striker == "bat0"


def test_undo_midover_then_continue():
    # Regression: replay (used by undo) must restore the "awaiting new over" flag
    # so mid-over scoring resumes without re-selecting the bowler.
    inn = fresh()
    inn.set_bowler("bowl0")
    inn.record(BallEvent.runs(1))
    inn.record(BallEvent.runs(2))
    inn.record(BallEvent.runs(4))
    inn.undo()  # back to 2 legal balls, still mid-over
    inn.record(BallEvent.runs(6))  # must NOT raise NeedBowler
    sc = inn.scorecard()
    assert sc.runs == 9
    assert sc.legal_balls == 3


# --------------------------------------------------------------------------- #
# Innings end & custom rules
# --------------------------------------------------------------------------- #
def test_box_cricket_all_out_with_last_man_stands():
    rules = presets.box_cricket()  # 6 a side, LMS -> all out at 6 wickets
    inn = fresh(rules, bat=[f"bat{i}" for i in range(6)])
    inn.set_bowler("bowl0")
    for _ in range(6):
        inn.record(BallEvent.out(DismissalType.BOWLED))
    sc = inn.scorecard()
    assert sc.wickets == 6
    assert sc.is_complete is True
    assert sc.result_note == "All out"
    with pytest.raises(InningsComplete):
        inn.record(BallEvent.dot())


def test_box_cricket_lbw_disallowed():
    rules = presets.box_cricket()
    inn = fresh(rules, bat=[f"bat{i}" for i in range(6)])
    inn.set_bowler("bowl0")
    inn.record(BallEvent.out(DismissalType.LBW))
    sc = inn.scorecard()
    assert sc.wickets == 0  # LBW not allowed in this format
    assert inn.batters["bat0"].out is False
    assert sc.legal_balls == 1  # still a legal delivery


def test_rule_out_over_boundary_is_a_wicket():
    rules = presets.street_ruleout()  # over_boundary_out=True
    inn = fresh(rules, bat=[f"bat{i}" for i in range(6)])
    inn.set_bowler("bowl0")
    inn.record(BallEvent.out(DismissalType.BOUNDARY_OUT))
    sc = inn.scorecard()
    assert sc.wickets == 1
    assert inn.batters["bat0"].out is True
    assert inn.batters["bat0"].how_out == DismissalType.BOUNDARY_OUT
    assert inn.bowlers["bowl0"].wickets == 1  # credited to the bowler
    assert sc.runs == 0  # no runs for hitting it out


def test_boundary_out_ignored_when_rule_off():
    # In a normal (full-ground) format, a BOUNDARY_OUT event is not a dismissal.
    inn = fresh()  # t20, over_boundary_out=False
    inn.set_bowler("bowl0")
    inn.record(BallEvent.out(DismissalType.BOUNDARY_OUT))
    sc = inn.scorecard()
    assert sc.wickets == 0
    assert inn.batters["bat0"].out is False
    assert sc.legal_balls == 1


def test_innings_ends_when_overs_exhausted():
    rules = MatchRules(name="1-over", overs_per_innings=1, balls_per_over=6)
    inn = fresh(rules)
    inn.set_bowler("bowl0")
    for _ in range(6):
        inn.record(BallEvent.runs(1))
    sc = inn.scorecard()
    assert sc.is_complete is True
    assert sc.runs == 6
    assert sc.legal_balls == 6


# --------------------------------------------------------------------------- #
# Match-level chase & result
# --------------------------------------------------------------------------- #
def _one_over_rules():
    return MatchRules(name="1-over", overs_per_innings=1, balls_per_over=6, players_per_side=11)


def test_match_chase_win_by_wickets():
    sa = [f"A{i}" for i in range(11)]
    sb = [f"B{i}" for i in range(11)]
    m = MatchEngine(_one_over_rules(), "Alpha", "Bravo", sa, sb, bat_first="Alpha")
    m.innings1.set_bowler("B0")
    for _ in range(6):
        m.innings1.record(BallEvent.runs(1))  # Alpha 6
    assert m.innings1.is_complete

    i2 = m.start_second_innings()
    assert i2.target == 7
    i2.set_bowler("A0")
    i2.record(BallEvent.runs(6))
    i2.record(BallEvent.runs(1))  # Bravo 7 -> chased
    assert i2.is_complete
    assert m.result == "Bravo won by 10 wicket(s)"


def test_match_tie():
    sa = [f"A{i}" for i in range(11)]
    sb = [f"B{i}" for i in range(11)]
    m = MatchEngine(_one_over_rules(), "Alpha", "Bravo", sa, sb, bat_first="Alpha")
    m.innings1.set_bowler("B0")
    for _ in range(6):
        m.innings1.record(BallEvent.runs(1))
    i2 = m.start_second_innings()
    i2.set_bowler("A0")
    for _ in range(6):
        i2.record(BallEvent.runs(1))  # Bravo 6 -> tie
    assert i2.is_complete
    assert m.result == "Match tied"


def test_chase_scorecard_exposes_required():
    sa = [f"A{i}" for i in range(11)]
    sb = [f"B{i}" for i in range(11)]
    rules = MatchRules(name="2-over", overs_per_innings=2, balls_per_over=6)
    m = MatchEngine(rules, "Alpha", "Bravo", sa, sb, bat_first="Alpha")
    m.innings1.set_bowler("B0")
    for _ in range(6):
        m.innings1.record(BallEvent.runs(2))  # 12
    m.innings1.set_bowler("B1")
    for _ in range(6):
        m.innings1.record(BallEvent.runs(1))  # +6 = 18
    assert m.innings1.is_complete
    i2 = m.start_second_innings()
    assert i2.target == 19
    i2.set_bowler("A0")
    i2.record(BallEvent.runs(4))
    sc = i2.scorecard()
    assert sc.required_runs == 15
    assert sc.balls_remaining == 11
