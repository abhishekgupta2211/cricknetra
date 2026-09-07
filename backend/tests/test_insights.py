"""Expanded leaderboards, player insights breakdowns, and head-to-head compare."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _player(n):
    return client.post("/api/v1/players", json={"name": n}).json()["id"]


def _team(n):
    return client.post("/api/v1/teams", json={"name": n}).json()["id"]


def _setup():
    ids = {n: _player(n) for n in ["A1", "A2", "A3", "B1", "B2", "B3"]}
    aces, blues = _team("Aces"), _team("Blues")
    rules = {"name": "Mini", "format_id": "mini", "overs_per_innings": 1, "balls_per_over": 6}
    mid = client.post(
        "/api/v1/matches",
        json={
            "team_a": "Aces", "team_b": "Blues", "bat_first": "a", "rules": rules,
            "squad_a": ["A1", "A2", "A3"], "squad_b": ["B1", "B2", "B3"],
            "squad_a_ids": [ids["A1"], ids["A2"], ids["A3"]],
            "squad_b_ids": [ids["B1"], ids["B2"], ids["B3"]],
            "team_a_id": aces, "team_b_id": blues,
        },
    ).json()["id"]

    def ball(b):
        client.post(f"/api/v1/matches/{mid}/balls", json=b)

    # A1 two 4s then caught(B2); A3 two 4s then bowled. (Aces 16 all out)
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B1"})
    ball({"action": "runs", "value": 4}); ball({"action": "runs", "value": 4})
    ball({"action": "wicket", "dismissal": "caught", "fielder": "B2"})
    ball({"action": "runs", "value": 4}); ball({"action": "runs", "value": 4})
    ball({"action": "wicket", "dismissal": "bowled"})
    # A1 bowls: B1 two 4s then bowled; B3 a 4, a dot, then bowled. (Blues 12)
    client.post(f"/api/v1/matches/{mid}/second-innings")
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "A1"})
    ball({"action": "runs", "value": 4}); ball({"action": "runs", "value": 4})
    ball({"action": "wicket", "dismissal": "bowled"})
    ball({"action": "runs", "value": 4}); ball({"action": "runs", "value": 0})
    ball({"action": "wicket", "dismissal": "bowled"})
    return ids


def test_expanded_leaderboards():
    _setup()
    lb = client.get("/api/v1/leaderboards").json()
    assert lb["most_catches"][0]["name"] == "B2" and lb["most_catches"][0]["value"] == 1.0
    assert lb["best_bowling"][0]["name"] == "A1"          # 2/12 beats 2/16 (fewer runs)
    assert lb["best_bowling"][0]["detail"] == "2/12"
    assert lb["highest_score"][0]["value"] == 8.0
    assert lb["most_fours"][0]["value"] == 2.0
    assert lb["mvp"][0]["value"] == 48.0                  # 8 runs + 2 wkts*20


def test_player_insights_breakdowns():
    ids = _setup()
    a1 = client.get(f"/api/v1/players/{ids['A1']}/insights").json()
    bat = a1["batting"]
    assert bat["balls_faced"] == 3 and bat["dot_balls"] == 1 and bat["fours"] == 2
    assert bat["boundary_runs"] == 8 and bat["running_runs"] == 0
    assert bat["boundary_runs_pct"] == 100.0
    assert bat["dismissals"] == {"caught": 1}
    bowl = a1["bowling"]
    assert bowl["balls_bowled"] == 6 and bowl["dot_balls"] == 3
    assert bowl["wickets_by_type"] == {"bowled": 2}


def test_head_to_head_compare():
    ids = _setup()
    c = client.get(f"/api/v1/insights/compare?player_a={ids['A1']}&player_b={ids['B1']}").json()
    assert c["player_a"]["player"]["name"] == "A1"
    assert c["player_b"]["player"]["name"] == "B1"
    assert c["player_a"]["batting"]["runs"] == 8
    assert c["player_a"]["bowling"]["wickets"] == 2


def test_compare_404_for_unknown():
    assert client.get("/api/v1/insights/compare?player_a=999&player_b=998").status_code == 404
