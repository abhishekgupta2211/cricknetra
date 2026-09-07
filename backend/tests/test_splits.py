"""Per-format / per-ball-type stat splits + pace/spin matchups (#138)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.domain.presets import box_cricket, odi, t10, t20
from app.main import app
from app.services.stats_service import _ball_bucket, _format_bucket, classify_bowling

client = TestClient(app)


def _player(name, bowling=None):
    body = {"name": name}
    if bowling:
        body["bowling_style"] = bowling
    return client.post("/api/v1/players", json=body).json()["id"]


def _team(n):
    return client.post("/api/v1/teams", json={"name": n}).json()["id"]


# ----- pure helpers ---------------------------------------------------------
def test_classify_bowling():
    assert classify_bowling("Right-arm fast") == "pace"
    assert classify_bowling("Right-arm medium") == "pace"
    assert classify_bowling("Left-arm fast") == "pace"
    assert classify_bowling("Right-arm off-spin") == "spin"
    assert classify_bowling("Right-arm leg-spin") == "spin"
    assert classify_bowling("Left-arm orthodox") == "spin"
    assert classify_bowling("Left-arm wrist-spin") == "spin"
    assert classify_bowling(None) is None
    assert classify_bowling("") is None
    assert classify_bowling("part-timer") is None


def test_format_and_ball_buckets():
    assert _format_bucket(t20())[1] == "T20"
    assert _format_bucket(odi())[1] == "ODI"
    assert _format_bucket(t10())[1] == "T10"
    assert _format_bucket(box_cricket())[1] == "Box/Gully"  # 5 overs
    assert _ball_bucket(t20())[1] == "Leather"
    assert _ball_bucket(box_cricket())[1] == "Tennis"


# ----- a tiny 2-over match: PACE bowls over 1 to BATP, SPIN over 2 to BATS ---
def _setup():
    batp = _player("BATP")
    bats = _player("BATS")
    f3 = _player("F3a")
    pace = _player("PACE", "Right-arm fast")
    spin = _player("SPIN", "Right-arm off-spin")
    f3b = _player("F3b")
    aces, blues = _team("AcesX"), _team("BluesX")
    rules = {"name": "Mini2", "format_id": "mini2", "overs_per_innings": 2, "balls_per_over": 3}
    mid = client.post("/api/v1/matches", json={
        "team_a": "AcesX", "team_b": "BluesX", "bat_first": "a", "rules": rules,
        "squad_a": ["BATP", "BATS", "F3a"], "squad_b": ["PACE", "SPIN", "F3b"],
        "squad_a_ids": [batp, bats, f3], "squad_b_ids": [pace, spin, f3b],
        "team_a_id": aces, "team_b_id": blues,
    }).json()["id"]

    def ball(b):
        client.post(f"/api/v1/matches/{mid}/balls", json=b)

    # Over 1 — PACE to BATP: 4, 0, 6 (boundaries/dot keep strike), over rotates to BATS
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "PACE"})
    ball({"action": "runs", "value": 4})
    ball({"action": "runs", "value": 0})
    ball({"action": "runs", "value": 6})
    # Over 2 — SPIN to BATS: 0, 2, bowled
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "SPIN"})
    ball({"action": "runs", "value": 0})
    ball({"action": "runs", "value": 2})
    ball({"action": "wicket", "dismissal": "bowled"})
    return {"BATP": batp, "BATS": bats}


def test_vs_pace_matchup():
    ids = _setup()
    sp = client.get(f"/api/v1/players/{ids['BATP']}/splits").json()
    vp, vs = sp["vs_pace"], sp["vs_spin"]
    assert vp["balls"] == 3 and vp["runs"] == 10
    assert vp["fours"] == 1 and vp["sixes"] == 1 and vp["dot_balls"] == 1
    assert vp["dismissals"] == 0 and vp["average"] is None
    assert vp["strike_rate"] == round(100 * 10 / 3, 2)
    assert vs["balls"] == 0  # BATP never faced spin
    assert sp["has_matchup"] is True


def test_vs_spin_matchup_and_dismissal():
    ids = _setup()
    sp = client.get(f"/api/v1/players/{ids['BATS']}/splits").json()
    vs = sp["vs_spin"]
    assert vs["balls"] == 3 and vs["runs"] == 2
    assert vs["dot_balls"] == 2 and vs["dismissals"] == 1
    assert vs["average"] == 2.0
    assert sp["vs_pace"]["balls"] == 0


def test_by_format_and_ball_buckets():
    ids = _setup()
    sp = client.get(f"/api/v1/players/{ids['BATP']}/splits").json()
    assert len(sp["by_format"]) == 1
    fmt = sp["by_format"][0]
    assert fmt["label"] == "Box/Gully"  # 2 overs <= 6
    assert fmt["matches"] == 1 and fmt["batting"]["runs"] == 10
    assert sp["by_ball"][0]["label"] == "Leather"  # default ball type
    assert sp["by_ball"][0]["batting"]["runs"] == 10


def test_splits_404_for_unknown_player():
    assert client.get("/api/v1/players/999999/splits").status_code == 404
