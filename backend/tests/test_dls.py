"""DLS-style revised targets (rain rules).

The scorer can revise the chasing side's target (and overs) mid-match; the
engine reshapes the second innings and the result follows the new par. Gated by
the same ``match.score`` permission as the rest of scoring.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DLS_RULES = {
    "name": "DLS test", "format_id": "dls",
    "players_per_side": 4, "overs_per_innings": 1, "balls_per_over": 6,
    "dls_enabled": True,
}


def _bat_over(mid: str, bowler: str, runs_each: int = 1, balls: int = 6) -> None:
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler})
    for _ in range(balls):
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": runs_each})


def _to_chase(rules: dict = DLS_RULES) -> str:
    """New DLS match; A bats its (1-over) innings; return id at the chase."""
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": rules},
    ).json()["id"]
    _bat_over(mid, "Bx")  # A makes 6; a 1-over innings is now complete
    client.post(f"/api/v1/matches/{mid}/second-innings")
    return mid


def test_revised_target_overrides_the_chase_target():
    mid = _to_chase()
    st = client.post(f"/api/v1/matches/{mid}/revised-target", json={"target": 4, "overs": 1}).json()
    assert st["rules"]["revised_target"] == 4
    assert st["innings"][1]["target"] == 4  # was 7 (6 + 1)
    client.delete(f"/api/v1/matches/{mid}")


def test_revised_target_flips_the_result():
    mid = _to_chase()
    client.post(f"/api/v1/matches/{mid}/revised-target", json={"target": 4, "overs": 1})
    _bat_over(mid, "Ax", runs_each=1, balls=4)  # B reaches 4 -> wins on the revised target
    final = client.get(f"/api/v1/matches/{mid}").json()
    assert final["result"] and "B won" in final["result"]
    client.delete(f"/api/v1/matches/{mid}")


def test_revised_overs_shorten_the_chase():
    rules = dict(DLS_RULES, overs_per_innings=2)
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": rules},
    ).json()["id"]
    _bat_over(mid, "B1")
    _bat_over(mid, "B2")  # A bats its 2 overs
    client.post(f"/api/v1/matches/{mid}/second-innings")
    st = client.post(f"/api/v1/matches/{mid}/revised-target", json={"target": 20, "overs": 1}).json()
    assert st["innings"][1]["max_overs"] == 1  # rain cut the chase to a single over
    client.delete(f"/api/v1/matches/{mid}")


def test_revised_overs_cannot_drop_below_overs_bowled():
    rules = dict(DLS_RULES, overs_per_innings=3)
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": rules},
    ).json()["id"]
    for b in ("B1", "B2", "B3"):
        _bat_over(mid, b)  # A bats its 3 overs
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _bat_over(mid, "A1")
    _bat_over(mid, "A2")  # B has faced 2 full overs (12 legal balls) of the chase
    bad = client.post(f"/api/v1/matches/{mid}/revised-target", json={"target": 30, "overs": 1})
    assert bad.status_code == 409  # can't cut the chase below the 2 overs already bowled
    ok = client.post(f"/api/v1/matches/{mid}/revised-target", json={"target": 30, "overs": 2})
    assert ok.status_code == 200
    client.delete(f"/api/v1/matches/{mid}")


def test_dls_suggest_computes_target_and_par():
    # A make 6 off their 1 over; ask DLS for a same-length (1-over) chase
    mid = _to_chase()
    r = client.post(f"/api/v1/matches/{mid}/dls-suggest", json={"team2_overs": 1})
    assert r.status_code == 200
    body = r.json()
    # equal resources, uninterrupted → ordinary target of score+1
    assert body["target"] == 7
    assert body["r1"] == body["r2"]
    assert "par" in body and "Team 1 made 6" in body["note"]
    client.delete(f"/api/v1/matches/{mid}")


def test_dls_suggest_reduced_chase_lowers_target():
    # A make ~12 off 2 overs; a chase cut to 1 over must need fewer than 13
    rules = dict(DLS_RULES, overs_per_innings=2)
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": rules},
    ).json()["id"]
    _bat_over(mid, "B1")
    _bat_over(mid, "B2")  # A: 12 off 2 overs
    client.post(f"/api/v1/matches/{mid}/second-innings")
    r = client.post(f"/api/v1/matches/{mid}/dls-suggest", json={"team2_overs": 1}).json()
    assert 1 <= r["target"] < 13, r          # a 1-over chase of a 2-over 12 needs well under 13
    assert r["r2"] < r["r1"]
    client.delete(f"/api/v1/matches/{mid}")


def test_revised_target_rejected_when_dls_disabled():
    rules = dict(DLS_RULES, dls_enabled=False)
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": rules},
    ).json()["id"]
    _bat_over(mid, "Bx")
    client.post(f"/api/v1/matches/{mid}/second-innings")
    r = client.post(f"/api/v1/matches/{mid}/revised-target", json={"target": 4})
    assert r.status_code == 409
    client.delete(f"/api/v1/matches/{mid}")
