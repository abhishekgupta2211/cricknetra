"""JSON API tests — the contract a React client will rely on."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_presets():
    r = client.get("/api/v1/presets")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert "t20" in ids and "box6" in ids


def test_get_full_rule_template():
    r = client.get("/api/v1/presets/box6")
    assert r.status_code == 200
    body = r.json()
    assert body["last_man_stands"] is True
    assert body["players_per_side"] == 6
    # LBW excluded in box cricket
    assert "lbw" not in body["allowed_dismissals"]


def test_unknown_preset_404():
    assert client.get("/api/v1/presets/nope").status_code == 404


def test_full_match_flow():
    r = client.post(
        "/api/v1/matches",
        json={"team_a": "Alpha", "team_b": "Bravo", "format_id": "t20", "bat_first": "a"},
    )
    assert r.status_code == 201
    state = r.json()
    mid = state["id"]
    assert state["awaiting_bowler"] is True
    assert state["innings"][0]["batting_team"] == "Alpha"

    r = client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Bravo 1"})
    assert r.status_code == 200
    assert r.json()["awaiting_bowler"] is False

    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 6})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "wide", "value": 0})
    r = client.post(f"/api/v1/matches/{mid}/balls", json={"action": "wicket", "dismissal": "bowled"})
    inn = r.json()["innings"][0]
    assert inn["runs"] == 11
    assert inn["wickets"] == 1
    assert inn["bowler"] == "Bravo 1"

    # undo the wicket
    r = client.post(f"/api/v1/matches/{mid}/undo")
    assert r.json()["innings"][0]["wickets"] == 0

    assert client.get(f"/api/v1/matches/{mid}").status_code == 200
    assert any(m["id"] == mid for m in client.get("/api/v1/matches").json())

    assert client.delete(f"/api/v1/matches/{mid}").status_code == 204
    assert client.get(f"/api/v1/matches/{mid}").status_code == 404


def test_no_ball_and_wide_carry_runs():
    """The pad's extras chooser sends runs with the extra: a no-ball hit for 4 and a
    wide the batters ran 2 on. The penalty is added on top by the engine."""
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "Alpha", "team_b": "Bravo", "format_id": "t20", "bat_first": "a"},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Bravo 1"})

    # no-ball + 4 off the bat -> 1 penalty + 4 = 5, and the batter is credited a four
    r = client.post(f"/api/v1/matches/{mid}/balls", json={"action": "no_ball", "value": 4})
    inn = r.json()["innings"][0]
    assert inn["runs"] == 5
    assert inn["legal_balls"] == 0  # a no-ball doesn't advance the over
    assert inn["batters"][0]["runs"] == 4 and inn["batters"][0]["fours"] == 1

    # wide + 2 run -> 1 penalty + 2 = 3 more (total 8), still no legal ball
    r = client.post(f"/api/v1/matches/{mid}/balls", json={"action": "wide", "value": 2})
    inn = r.json()["innings"][0]
    assert inn["runs"] == 8
    assert inn["legal_balls"] == 0
    assert inn["extras"]["total"] == 4  # 1 (nb penalty) + 1 (wide penalty) + 2 (wide runs)


def test_over_change_picker_excludes_previous_bowler():
    """After an over the picker drops the last bowler, picking them is a clean 409,
    and the state stays 'over_pending' so the scorer can choose again."""
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "Strikers", "team_b": "Blasters", "format_id": "t20", "bat_first": "a"},
    ).json()["id"]
    b0 = client.get(f"/api/v1/matches/{mid}").json()["available_bowlers"][0]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": b0})
    for _ in range(6):
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})

    st = client.get(f"/api/v1/matches/{mid}").json()
    assert st["over_pending"] is True and st["awaiting_bowler"] is True
    assert b0 not in st["available_bowlers"]  # the just-bowled bowler isn't offered

    # picking the previous bowler is rejected up front (not a silent trap)
    r = client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": b0})
    assert r.status_code == 409 and "consecutive" in r.json()["detail"]
    # ...and the picker is still available (nothing got staged)
    st = client.get(f"/api/v1/matches/{mid}").json()
    assert st["over_pending"] is True and st["staged_bowler"] is None

    # a different bowler is accepted and is staged for the new over
    b1 = st["available_bowlers"][0]
    r = client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": b1})
    assert r.status_code == 200 and r.json()["staged_bowler"] == b1
    assert r.json()["over_pending"] is True  # still changeable until the first ball
    assert client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 0}).json()["over_pending"] is False


def test_record_without_bowler_is_409():
    mid = client.post(
        "/api/v1/matches", json={"team_a": "A", "team_b": "B", "format_id": "t20"}
    ).json()["id"]
    r = client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})
    assert r.status_code == 409


def test_create_with_custom_rules():
    rules = client.get("/api/v1/presets/box6").json()
    r = client.post(
        "/api/v1/matches", json={"team_a": "X", "team_b": "Y", "rules": rules}
    )
    assert r.status_code == 201
    state = r.json()
    assert state["innings"][0]["max_wickets"] == 6  # 6-a-side, last-man-stands
    assert state["rules_name"] == "Box Cricket"


def test_invalid_format_is_400():
    r = client.post("/api/v1/matches", json={"team_a": "A", "team_b": "B", "format_id": "zzz"})
    assert r.status_code == 400
