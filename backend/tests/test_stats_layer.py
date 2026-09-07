"""Leaderboards, team stats, and fielding/form — via a full deterministic match."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _player(name):
    return client.post("/api/v1/players", json={"name": name}).json()["id"]


def _team(name):
    return client.post("/api/v1/teams", json={"name": name}).json()["id"]


def _play_full_match():
    a1, a2, a3 = _player("A1"), _player("A2"), _player("A3")
    b1, b2, b3 = _player("B1"), _player("B2"), _player("B3")
    aces, blues = _team("Aces"), _team("Blues")
    rules = {"name": "Mini", "format_id": "mini", "overs_per_innings": 1, "balls_per_over": 6}
    mid = client.post(
        "/api/v1/matches",
        json={
            "team_a": "Aces", "team_b": "Blues", "bat_first": "a", "rules": rules,
            "squad_a": ["A1", "A2", "A3"], "squad_b": ["B1", "B2", "B3"],
            "squad_a_ids": [a1, a2, a3], "squad_b_ids": [b1, b2, b3],
            "team_a_id": aces, "team_b_id": blues,
        },
    ).json()["id"]

    def ball(b):
        client.post(f"/api/v1/matches/{mid}/balls", json=b)

    # Innings 1: Aces. A1 8 then caught by B2; A3 8 then bowled. All out 16.
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B1"})
    ball({"action": "runs", "value": 4})
    ball({"action": "runs", "value": 4})
    ball({"action": "wicket", "dismissal": "caught", "fielder": "B2"})
    ball({"action": "runs", "value": 4})
    ball({"action": "runs", "value": 4})
    ball({"action": "wicket", "dismissal": "bowled"})

    # Innings 2: Blues chase 17. B1 8 bowled; B3 4 bowled. All out 12 -> Aces win.
    client.post(f"/api/v1/matches/{mid}/second-innings")
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "A1"})
    ball({"action": "runs", "value": 4})
    ball({"action": "runs", "value": 4})
    ball({"action": "wicket", "dismissal": "bowled"})
    ball({"action": "runs", "value": 4})
    ball({"action": "runs", "value": 0})
    ball({"action": "wicket", "dismissal": "bowled"})
    return dict(mid=mid, a1=a1, a2=a2, a3=a3, b1=b1, b2=b2, b3=b3, aces=aces, blues=blues)


def test_match_completes_with_winner():
    ids = _play_full_match()
    state = client.get(f"/api/v1/matches/{ids['mid']}").json()
    assert state["result"] is not None and state["result"].startswith("Aces won")


def test_team_stats():
    ids = _play_full_match()
    aces = client.get(f"/api/v1/teams/{ids['aces']}/stats").json()
    assert aces["played"] == 1 and aces["won"] == 1 and aces["lost"] == 0
    assert aces["runs_for"] == 16 and aces["runs_against"] == 12
    assert aces["win_pct"] == 100.0
    blues = client.get(f"/api/v1/teams/{ids['blues']}/stats").json()
    assert blues["won"] == 0 and blues["lost"] == 1 and blues["runs_for"] == 12


def test_leaderboards():
    _play_full_match()
    lb = client.get("/api/v1/leaderboards").json()
    assert lb["most_runs"][0]["value"] == 8.0  # A1/A3/B1 tied on 8
    assert lb["most_wickets"][0]["value"] == 2.0
    # A1 conceded 12 in his over, B1 conceded 16 -> A1 most economical
    assert lb["best_economy"][0]["name"] == "A1"
    assert lb["best_economy"][0]["value"] == 12.0


def test_fielding_and_form():
    ids = _play_full_match()
    b2 = client.get(f"/api/v1/players/{ids['b2']}/stats").json()
    assert b2["fielding"]["catches"] == 1

    a1 = client.get(f"/api/v1/players/{ids['a1']}/stats").json()
    assert a1["batting"]["runs"] == 8
    assert a1["bowling"]["wickets"] == 2
    assert a1["recent"][0]["bat"] == "8 (3)"  # two 4s + the dismissal ball faced
    assert a1["recent"][0]["bowl"] == "2/12 (1.0)"


def test_team_stats_404_for_unknown():
    assert client.get("/api/v1/teams/999999/stats").status_code == 404


def test_leaderboards_empty_when_no_matches():
    lb = client.get("/api/v1/leaderboards").json()
    assert lb["most_runs"] == [] and lb["most_wickets"] == []
