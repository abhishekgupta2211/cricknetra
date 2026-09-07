"""SqlMatchRepository tests — event-sourced persistence, on SQLite (no Postgres
needed in CI). Proves a match survives a reload and stays resumable."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401 — register tables on Base
from app.db.base import Base
from app.domain import presets
from app.domain.engine import MatchEngine
from app.domain.events import BallEvent
from app.domain.rules import MatchRules
from app.repositories.sql_match_repository import SqlMatchRepository

SA = [f"A{i}" for i in range(11)]
SB = [f"B{i}" for i in range(11)]


@pytest.fixture
def repo():
    # One shared in-memory SQLite DB across sessions (StaticPool keeps a single
    # connection), so persisted data survives between repo operations.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SqlMatchRepository(sf)


def _t20_match() -> MatchEngine:
    return MatchEngine(presets.t20(), "Alpha", "Bravo", SA, SB, bat_first="Alpha")


def test_create_and_reload(repo):
    mid = repo.add(_t20_match())
    loaded = repo.get(mid)
    assert loaded is not None
    assert loaded.team_a == "Alpha"
    assert loaded.current.scorecard().runs == 0
    assert loaded.current.awaiting_new_over is True


def test_revised_target_survives_reload(repo):
    """A DLS revised target/overs lives on the match's rulebook and is re-persisted."""
    rules = MatchRules(name="DLS", overs_per_innings=1, players_per_side=4, dls_enabled=True)
    m = MatchEngine(rules, "Alpha", "Bravo", SA[:4], SB[:4], bat_first="Alpha")
    mid = repo.add(m)
    m.current.set_bowler("B0")
    for _ in range(6):
        m.current.record(BallEvent.runs(1))  # 1-over innings -> complete
    m.start_second_innings()
    m.set_revised_target(4, 1)
    repo.save(mid, m)

    loaded = repo.get(mid)
    assert loaded.rules.revised_target == 4
    assert loaded.rules.revised_overs == 1
    assert loaded.innings2 is not None
    assert loaded.innings2.target == 4
    assert loaded.innings2.rules.overs_per_innings == 1


def test_super_over_survives_reload(repo):
    """A tie -> super over is replayed from the event log across reloads."""
    rules = MatchRules(name="SO", overs_per_innings=1, players_per_side=4, super_over_on_tie=True)
    m = MatchEngine(rules, "Alpha", "Bravo", SA[:4], SB[:4], bat_first="Alpha")
    mid = repo.add(m)
    m.current.set_bowler("B0")
    for _ in range(6):
        m.current.record(BallEvent.runs(1))  # Alpha = 6
    m.start_second_innings()
    m.current.set_bowler("A0")
    for _ in range(6):
        m.current.record(BallEvent.runs(1))  # Bravo = 6 -> tie
    repo.save(mid, m)
    assert repo.get(mid).needs_super_over is True

    # super over: Alpha bats first, makes 4
    m.super_over("a")
    m.current.set_bowler("B1")
    for v in (1, 1, 1, 1, 0, 0):
        m.current.record(BallEvent.runs(v))
    repo.save(mid, m)

    loaded = repo.get(mid)
    assert len(loaded.super_overs) == 1
    assert loaded.super_overs[0].first.runs == 4
    assert loaded.awaiting_super_second is True

    # resume the reload and finish the chase
    loaded.super_over()
    loaded.current.set_bowler("A1")
    for _ in range(5):
        loaded.current.record(BallEvent.runs(1))  # Bravo = 5 -> wins the super over
    repo.save(mid, loaded)
    assert repo.get(mid).result == "Bravo won (Super Over)"


def test_scoring_survives_reload_and_resumes(repo):
    m = _t20_match()
    mid = repo.add(m)
    m.current.set_bowler("B0")
    repo.save(mid, m)
    for v in (4, 6, 1):
        m.current.record(BallEvent.runs(v))
        repo.save(mid, m)

    loaded = repo.get(mid)
    sc = loaded.current.scorecard()
    assert sc.runs == 11
    assert sc.bowler == "B0"  # current bowler restored from the replayed log

    # the reloaded engine is fully resumable
    loaded.current.record(BallEvent.runs(2))
    repo.save(mid, loaded)
    assert repo.get(mid).current.scorecard().runs == 13


def test_undo_is_persisted(repo):
    m = _t20_match()
    mid = repo.add(m)
    m.current.set_bowler("B0")
    repo.save(mid, m)
    m.current.record(BallEvent.runs(4))
    repo.save(mid, m)
    m.current.record(BallEvent.runs(6))
    repo.save(mid, m)
    m.current.undo()
    repo.save(mid, m)
    assert repo.get(mid).current.scorecard().runs == 4


def test_edit_is_persisted(repo):
    """Correcting a delivery (same log length, changed payload) must reach the DB —
    a reload has to show the edited value, not the original."""
    m = _t20_match()
    mid = repo.add(m)
    m.current.set_bowler("B0")
    repo.save(mid, m)
    for v in (4, 1):
        m.current.record(BallEvent.runs(v))
        repo.save(mid, m)
    assert repo.get(mid).current.scorecard().runs == 5

    m.current.edit_event(0, BallEvent.runs(6))  # 4 -> 6
    repo.save(mid, m)

    loaded = repo.get(mid)
    assert loaded.current.scorecard().runs == 7
    assert loaded.current.events[0].runs_off_bat == 6
    assert loaded.current.events[1].runs_off_bat == 1  # untouched ball intact


def test_mid_log_delete_is_persisted(repo):
    """Deleting a non-final delivery re-indexes the log; the DB must mirror the new
    order, not just drop the last row."""
    m = _t20_match()
    mid = repo.add(m)
    m.current.set_bowler("B0")
    repo.save(mid, m)
    for v in (4, 1, 2):
        m.current.record(BallEvent.runs(v))
        repo.save(mid, m)
    assert repo.get(mid).current.scorecard().runs == 7

    m.current.delete_event(1)  # remove the single in the middle -> [4, 2]
    repo.save(mid, m)

    loaded = repo.get(mid)
    sc = loaded.current.scorecard()
    assert sc.runs == 6 and sc.legal_balls == 2
    assert [e.runs_off_bat for e in loaded.current.events] == [4, 2]


def test_second_innings_survives_reload(repo):
    rules = MatchRules(name="1-over", overs_per_innings=1, balls_per_over=6)
    m = MatchEngine(rules, "Alpha", "Bravo", SA, SB, bat_first="Alpha")
    mid = repo.add(m)
    m.current.set_bowler("B0")
    repo.save(mid, m)
    for _ in range(6):
        m.current.record(BallEvent.runs(1))
        repo.save(mid, m)
    assert m.innings1.is_complete
    m.start_second_innings()
    repo.save(mid, m)

    loaded = repo.get(mid)
    assert loaded.innings2 is not None
    assert loaded.current.target == 7
    assert loaded.current.batting_team == "Bravo"
    assert len(loaded.innings1.events) == 6


def test_summaries_and_delete(repo):
    mid = repo.add(_t20_match())
    assert any(s.id == mid for s in repo.summaries())
    repo.delete(mid)
    assert repo.get(mid) is None
    assert all(s.id != mid for s in repo.summaries())
