"""Partnership breakdown — a projection over the fall-of-wickets + batting order."""

from __future__ import annotations

from app.domain import presets
from app.domain.engine import InningsEngine
from app.domain.enums import DismissalType
from app.domain.events import BallEvent

BAT = [f"A{i}" for i in range(1, 12)]
BOWL = [f"B{i}" for i in range(1, 12)]


def _inn():
    inn = InningsEngine(presets.t20(), "A", "B", BAT, BOWL)
    inn.set_bowler("B1")
    return inn


def test_partnerships_split_by_wicket_and_include_extras():
    inn = _inn()
    # opening stand A1 & A2: a four, a wide (extra, not a ball faced), then A1 run out at 5
    inn.record(BallEvent.runs(4))                                   # score 4
    inn.record(BallEvent.wide(ran=0))                              # +1 wide -> score 5
    inn.record(BallEvent.out(DismissalType.RUN_OUT, batter_out="striker", fielder="B3"))  # A1 out @5
    # 2nd wicket A2 & A3: a six, then bowled at 11
    inn.record(BallEvent.runs(6))                                   # score 11 (six + the bowled ball)
    inn.record(BallEvent.out(DismissalType.BOWLED))                # striker out @11
    inn.record(BallEvent.runs(2))                                  # open 3rd stand -> score 13

    ps = inn.scorecard().partnerships
    assert len(ps) == 3, ps                      # 1st, 2nd (broken) + open 3rd
    p1, p2, p3 = ps
    assert p1.wicket == 1 and p1.runs == 5 and not p1.unbroken     # 4 + the wide
    assert {p1.batter_a, p1.batter_b} == {"A1", "A2"}
    assert p2.wicket == 2 and p2.runs == 6                          # 11 - 5
    assert {p2.batter_a, p2.batter_b} == {"A2", "A3"}             # A2 stayed, A3 came in
    assert p1.balls == 2 and p2.balls == 2                          # wide isn't a ball faced
    assert p3.wicket == 3 and p3.runs == 2 and p3.unbroken is True


def test_partnership_runs_partition_the_total():
    inn = _inn()
    for v in (1, 2, 4, 6):
        inn.record(BallEvent.runs(v))
    inn.record(BallEvent.out(DismissalType.BOWLED))
    inn.record(BallEvent.runs(3))
    sc = inn.scorecard()
    assert sum(p.runs for p in sc.partnerships) == sc.runs   # stands partition the score
    assert sum(p.balls for p in sc.partnerships) == sc.legal_balls


def test_partnership_run_rate():
    inn = _inn()
    inn.record(BallEvent.runs(6))
    inn.record(BallEvent.runs(6))   # 12 off 2 balls -> RR 36.0
    p = inn.scorecard().partnerships[0]
    assert p.runs == 12 and p.balls == 2 and p.run_rate == 36.0
