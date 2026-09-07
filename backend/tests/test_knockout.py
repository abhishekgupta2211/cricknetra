"""Knockout brackets — round generation, byes, winner advancement, champion."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MINI = {"name": "Mini", "format_id": "mini", "overs_per_innings": 1, "balls_per_over": 6}


def _team(name):
    return client.post("/api/v1/teams", json={"name": name}).json()["id"]


def _kteam(name):
    """A team of 2 players (so a match is all-out after 1 wicket)."""
    tid = _team(name)
    names = [name + "a", name + "b"]
    for pn in names:
        client.post(f"/api/v1/teams/{tid}/members", json={"name": pn})
    pids = [m["player_id"] for m in client.get(f"/api/v1/teams/{tid}").json()["members"]]
    return tid, pids, names


def _win_a(fixture, registry):
    """Start a fixture and let team_a win 6-0 (returns team_a's id)."""
    a_id, b_id = fixture["team_a"]["id"], fixture["team_b"]["id"]
    a_pids, a_names = registry[a_id]
    b_pids, b_names = registry[b_id]
    mid = client.post(
        f"/api/v1/tournaments/fixtures/{fixture['id']}/start",
        json={"squad_a_ids": a_pids, "squad_b_ids": b_pids, "bat_first": "a"},
    ).json()["match_id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": b_names[0]})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 6})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "wicket", "dismissal": "bowled"})
    client.post(f"/api/v1/matches/{mid}/second-innings")
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": a_names[0]})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "wicket", "dismissal": "bowled"})
    return a_id


def test_knockout_round1_structure():
    ids = [_team(n) for n in ["T1", "T2", "T3", "T4"]]
    t = client.post(
        "/api/v1/tournaments",
        json={"name": "Cup", "format": "knockout", "team_ids": ids, "format_id": "t20"},
    ).json()
    r1 = [f for f in t["fixtures"] if f["round"] == 1]
    assert len(r1) == 2  # 4 teams -> 2 semis
    assert max(f["round"] for f in t["fixtures"]) == 1  # round 2 not generated yet
    assert all(f["status"] == "scheduled" for f in r1)


def test_knockout_bye_is_auto_completed():
    ids = [_team(n) for n in ["A", "B", "C"]]
    t = client.post(
        "/api/v1/tournaments",
        json={"name": "Cup3", "format": "knockout", "team_ids": ids, "format_id": "t20"},
    ).json()
    byes = [f for f in t["fixtures"] if f["team_b"] is None]
    assert len(byes) == 1
    assert byes[0]["status"] == "completed"
    assert byes[0]["team_a"]["name"] == "C"  # third team gets the bye


def test_knockout_full_bracket_to_champion():
    reg, ids = {}, []
    for n in ["A", "B", "C"]:
        tid, pids, names = _kteam(n)
        reg[tid] = (pids, names)
        ids.append(tid)
    t = client.post(
        "/api/v1/tournaments",
        json={"name": "Cup3", "format": "knockout", "team_ids": ids, "rules": MINI},
    ).json()
    tid = t["id"]

    # round 1: (A v B) real + bye(C). A wins.
    real = [f for f in t["fixtures"] if f["team_b"] is not None][0]
    _win_a(real, reg)

    # reading the tournament advances the bracket: round 2 = (A v C) final
    d = client.get(f"/api/v1/tournaments/{tid}").json()
    final = [f for f in d["fixtures"] if f["round"] == 2]
    assert len(final) == 1
    assert {final[0]["team_a"]["name"], final[0]["team_b"]["name"]} == {"A", "C"}

    # play the final
    winner_id = _win_a(final[0], reg)
    d2 = client.get(f"/api/v1/tournaments/{tid}").json()
    assert d2["champion"] is not None
    assert d2["champion"]["id"] == winner_id
