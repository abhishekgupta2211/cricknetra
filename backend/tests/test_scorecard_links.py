"""Scorecard batter/bowler DTOs carry the real-player id (for the 'tap name → profile'
link) on from-teams matches, and None on quick matches."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

RULES = {"name": "T20", "format_id": "t20", "players_per_side": 3, "overs_per_innings": 2, "balls_per_over": 6}


def test_from_teams_match_carries_player_ids():
    ta = client.post("/api/v1/teams", json={"name": "CSK"}).json()
    tb = client.post("/api/v1/teams", json={"name": "MI"}).json()
    pa = [client.post("/api/v1/players", json={"name": n}).json()["id"] for n in ("Gaikwad", "Jadeja", "Dhoni")]
    pb = [client.post("/api/v1/players", json={"name": n}).json()["id"] for n in ("Rohit", "Surya", "Bumrah")]
    mid = client.post("/api/v1/matches", json={
        "team_a": "CSK", "team_b": "MI", "bat_first": "a", "rules": RULES,
        "squad_a": ["Gaikwad", "Jadeja", "Dhoni"], "squad_b": ["Rohit", "Surya", "Bumrah"],
        "squad_a_ids": pa, "squad_b_ids": pb, "team_a_id": ta["id"], "team_b_id": tb["id"],
    }).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Bumrah"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})

    inn = client.get(f"/api/v1/matches/{mid}").json()["innings"][0]
    striker = next(b for b in inn["batters"] if b["has_batted"] and b["name"] == "Gaikwad")
    assert striker["player_id"] == pa[0]                 # tap → /player/{id}
    assert inn["bowlers"][0]["player_id"] == pb[2]        # Bumrah
    client.delete(f"/api/v1/matches/{mid}")
    for p in pa + pb:
        client.delete(f"/api/v1/players/{p}")
    client.delete(f"/api/v1/teams/{ta['id']}")
    client.delete(f"/api/v1/teams/{tb['id']}")


def test_quick_match_has_no_player_ids():
    mid = client.post("/api/v1/matches",
                      json={"team_a": "A", "team_b": "B", "bat_first": "a", "format_id": "t20"}).json()["id"]
    bowler = client.get(f"/api/v1/matches/{mid}").json()["available_bowlers"][0]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})
    inn = client.get(f"/api/v1/matches/{mid}").json()["innings"][0]
    assert all(b["player_id"] is None for b in inn["batters"])   # auto squads → not linked
    assert all(w["player_id"] is None for w in inn["bowlers"])
    client.delete(f"/api/v1/matches/{mid}")
