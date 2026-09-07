"""Career stats aggregated off the event log, via real player linkage."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _player(name: str) -> str:
    return client.post("/api/v1/players", json={"name": name}).json()["id"]


def test_career_stats_from_a_match():
    alice, bob, carol = _player("Alice"), _player("Bob"), _player("Carol")
    dave, eve, frank = _player("Dave"), _player("Eve"), _player("Frank")

    r = client.post(
        "/api/v1/matches",
        json={
            "team_a": "Aces", "team_b": "Blues", "format_id": "t20", "bat_first": "a",
            "squad_a": ["Alice", "Bob", "Carol"], "squad_b": ["Dave", "Eve", "Frank"],
            "squad_a_ids": [alice, bob, carol], "squad_b_ids": [dave, eve, frank],
        },
    )
    assert r.status_code == 201
    mid = r.json()["id"]

    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Dave"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 2})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "wicket", "dismissal": "bowled"})

    # Alice faced every ball (all even runs kept her on strike), then was out.
    a = client.get(f"/api/v1/players/{alice}/stats").json()["batting"]
    assert a["innings"] == 1
    assert a["runs"] == 10
    assert a["balls"] == 4
    assert a["fours"] == 2
    assert a["not_outs"] == 0
    assert a["average"] == 10.0
    assert a["highest"] == 10

    # Bob opened, never out -> not out 0.
    b = client.get(f"/api/v1/players/{bob}/stats").json()["batting"]
    assert b["innings"] == 1 and b["runs"] == 0 and b["not_outs"] == 1
    assert b["average"] is None  # never dismissed

    # Dave's bowling.
    d = client.get(f"/api/v1/players/{dave}/stats").json()["bowling"]
    assert d["wickets"] == 1
    assert d["runs"] == 10
    assert d["balls"] == 4
    assert d["best"] == "1/10"


def test_stats_empty_for_unplayed_player():
    pid = _player("Nobody")
    s = client.get(f"/api/v1/players/{pid}/stats").json()
    assert s["batting"]["innings"] == 0
    assert s["bowling"]["innings"] == 0
    assert s["player"]["name"] == "Nobody"


def test_stats_404_for_unknown_player():
    assert client.get("/api/v1/players/999999/stats").status_code == 404


def test_quick_match_does_not_affect_player_stats():
    pid = _player("Solo")
    # a quick match (no player-id linkage) must not contribute to anyone's stats
    mid = client.post("/api/v1/matches", json={"team_a": "X", "team_b": "Y", "format_id": "t20"}).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Y 1"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 6})
    assert client.get(f"/api/v1/players/{pid}/stats").json()["batting"]["innings"] == 0
