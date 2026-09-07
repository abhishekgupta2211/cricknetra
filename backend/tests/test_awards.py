"""Auto Man-of-the-Match / best batter / best bowler (#142)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_RULES = {"name": "Mini", "format_id": "mini", "overs_per_innings": 1, "players_per_side": 3, "balls_per_over": 6}


def _match():
    mid = client.post("/api/v1/matches", json={
        "team_a": "Aces", "team_b": "Blues", "bat_first": "a", "rules": _RULES,
        "squad_a": ["A1", "A2", "A3"], "squad_b": ["B1", "B2", "B3"],
    }).json()["id"]
    return mid


def _ball(mid, b):
    client.post(f"/api/v1/matches/{mid}/balls", json=b)


def test_awards_none_until_match_complete():
    mid = _match()
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B1"})
    _ball(mid, {"action": "runs", "value": 6})
    st = client.get(f"/api/v1/matches/{mid}").json()
    assert st["result"] is None
    assert st["awards"] is None


def test_awards_pick_mom_best_batter_best_bowler():
    mid = _match()
    # Innings 1 — A1 smashes 18 off 6 (three sixes), not out; Aces 18/0
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B1"})
    for v in (6, 6, 6, 0, 0, 0):
        _ball(mid, {"action": "runs", "value": v})
    # Innings 2 — A2 bowls Blues out for 0 (two bowled), Aces win by 18
    client.post(f"/api/v1/matches/{mid}/second-innings")
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "A2"})
    _ball(mid, {"action": "wicket", "dismissal": "bowled"})
    _ball(mid, {"action": "wicket", "dismissal": "bowled"})

    st = client.get(f"/api/v1/matches/{mid}").json()
    assert st["result"] is not None  # match complete
    aw = st["awards"]
    assert aw is not None

    # A2: 2 wickets (50 pts) outweighs A1's 18 runs (24 pts) → MoM + best bowler
    assert aw["man_of_the_match"]["name"] == "A2"
    assert aw["man_of_the_match"]["team"] == "Aces"
    assert "2/0" in aw["man_of_the_match"]["line"]

    assert aw["best_batter"]["name"] == "A1"
    assert aw["best_batter"]["line"] == "18* (6)"
    assert aw["best_batter"]["team"] == "Aces"

    assert aw["best_bowler"]["name"] == "A2"
    assert aw["best_bowler"]["line"].startswith("2/0")
