"""Edit / delete any past delivery — the event-sourced engine re-derives, and an
illegal edit rolls back cleanly."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain import presets
from app.domain.engine import InningsEngine, ScoringError
from app.domain.events import BallEvent
from app.domain.rules import MatchRules
from app.main import app

client = TestClient(app)
BAT = [f"b{i}" for i in range(11)]
BOWL = [f"w{i}" for i in range(11)]


def _inn(rules=None) -> InningsEngine:
    e = InningsEngine(rules or presets.t20(), "A", "B", BAT, BOWL)
    e.set_bowler("w0")
    return e


# --------------------------------------------------------------------------- #
# engine
# --------------------------------------------------------------------------- #
def test_edit_event_recomputes_and_keeps_bowler():
    inn = _inn()
    inn.record(BallEvent.runs(4))
    inn.record(BallEvent.runs(1))
    assert inn.scorecard().runs == 5

    inn.edit_event(0, BallEvent.runs(6))  # 4 -> 6
    assert inn.scorecard().runs == 7
    assert inn.events[0].bowler == "w0"  # the over's bowler is preserved


def test_delete_event_recomputes():
    inn = _inn()
    for v in (4, 1, 2):
        inn.record(BallEvent.runs(v))
    assert inn.scorecard().runs == 7 and inn.scorecard().legal_balls == 3

    inn.delete_event(1)  # drop the single
    assert inn.scorecard().runs == 6 and inn.scorecard().legal_balls == 2


def test_bad_index_raises():
    inn = _inn()
    inn.record(BallEvent.runs(1))
    with pytest.raises(IndexError):
        inn.edit_event(5, BallEvent.runs(2))
    with pytest.raises(IndexError):
        inn.delete_event(-1)


def test_illegal_edit_rolls_back():
    rules = MatchRules(name="nobyes", overs_per_innings=5, players_per_side=11, byes_allowed=False)
    inn = _inn(rules)
    inn.record(BallEvent.runs(4))
    inn.record(BallEvent.runs(2))
    with pytest.raises(ScoringError):
        inn.edit_event(0, BallEvent.bye(2))  # byes disabled -> rejected
    # rolled back: original delivery + score intact
    assert inn.scorecard().runs == 6
    assert inn.events[0].runs_off_bat == 4


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
def _new_match() -> str:
    r = client.post("/api/v1/matches", json={"team_a": "A", "team_b": "B", "format_id": "t20", "bat_first": "a"})
    return r.json()["id"]


def test_api_edit_and_delete_delivery():
    mid = _new_match()
    bowler = client.get(f"/api/v1/matches/{mid}").json()["available_bowlers"][0]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})
    assert client.get(f"/api/v1/matches/{mid}").json()["innings"][0]["runs"] == 5

    # the feed exposes a per-innings index + editable flag for the live innings
    feed = client.get(f"/api/v1/matches/{mid}/ball-feed").json()
    assert feed[0]["idx"] == 0 and feed[0]["editable"] is True

    # edit the first ball 4 -> 6
    edited = client.put(f"/api/v1/matches/{mid}/balls/0", json={"action": "runs", "value": 6})
    assert edited.status_code == 200 and edited.json()["innings"][0]["runs"] == 7

    # delete the single (now at index 1)
    deleted = client.delete(f"/api/v1/matches/{mid}/balls/1")
    assert deleted.status_code == 200
    inn = deleted.json()["innings"][0]
    assert inn["runs"] == 6 and inn["legal_balls"] == 1

    # out-of-range index -> 404
    assert client.put(f"/api/v1/matches/{mid}/balls/9", json={"action": "runs", "value": 1}).status_code == 404
