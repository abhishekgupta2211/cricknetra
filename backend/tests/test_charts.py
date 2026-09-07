"""Chart data over the HTTP API — manhattan/worm always present; a marked
scoring shot reaches the wagon-wheel projection end to end."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _new_match() -> str:
    r = client.post(
        "/api/v1/matches",
        json={"team_a": "Alpha", "team_b": "Bravo", "format_id": "t20", "bat_first": "a"},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def test_innings_dto_always_carries_chart_arrays():
    inn = client.get(f"/api/v1/matches/{_new_match()}").json()["innings"][0]
    assert inn["manhattan"] == []
    assert inn["worm"] == []
    assert inn["wagon"] == []


def test_marked_shot_reaches_wagon_projection():
    mid = _new_match()
    state = client.get(f"/api/v1/matches/{mid}").json()
    bowler = state["available_bowlers"][0]
    assert client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler}).status_code == 200

    # a boundary with a marked direction, then a single without one
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4, "wagon_x": 0.5, "wagon_y": 0.7})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})

    inn = client.get(f"/api/v1/matches/{mid}").json()["innings"][0]
    assert inn["manhattan"] == [5]      # 4 + 1 so far this (incomplete) over
    assert inn["worm"] == [5]
    assert len(inn["wagon"]) == 1       # only the marked boundary
    shot = inn["wagon"][0]
    assert shot["runs"] == 4 and shot["x"] == 0.5 and shot["y"] == 0.7
