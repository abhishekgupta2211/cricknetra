"""Tournaments — round-robin fixtures, fixture→match, points table + NRR."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _team_with(name, players):
    tid = client.post("/api/v1/teams", json={"name": name}).json()["id"]
    for p in players:
        client.post(f"/api/v1/teams/{tid}/members", json={"name": p})
    team = client.get(f"/api/v1/teams/{tid}").json()
    return tid, [m["player_id"] for m in team["members"]]


def test_round_robin_fixture_count():
    tids = [client.post("/api/v1/teams", json={"name": n}).json()["id"] for n in ["T1", "T2", "T3", "T4"]]
    t = client.post(
        "/api/v1/tournaments",
        json={"name": "League", "format": "round_robin", "team_ids": tids, "format_id": "t20"},
    ).json()
    assert len(t["fixtures"]) == 6  # 4 teams round-robin
    assert len(t["standings"]) == 4
    assert all(s["points"] == 0 and s["played"] == 0 for s in t["standings"])


def test_tournament_custom_rules_reach_the_match():
    """A custom rulebook chosen at tournament-create flows into each fixture's match."""
    aces, aces_pids = _team_with("BoxAces", ["A1", "A2", "A3"])
    blues, blues_pids = _team_with("BoxBlues", ["B1", "B2", "B3"])
    t = client.post(
        "/api/v1/tournaments",
        json={
            "name": "Box Cup", "format": "round_robin", "team_ids": [aces, blues],
            "rules": {
                "name": "Box rules", "format_id": "custom",
                "players_per_side": 6, "overs_per_innings": 5, "balls_per_over": 6,
                "over_boundary_out": True, "super_over_on_tie": True,
            },
        },
    ).json()
    fx = t["fixtures"][0]
    started = client.post(
        f"/api/v1/tournaments/fixtures/{fx['id']}/start",
        json={"squad_a_ids": aces_pids, "squad_b_ids": blues_pids, "bat_first": "a"},
    ).json()
    rules = client.get(f"/api/v1/matches/{started['match_id']}").json()["rules"]
    # The custom rulebook's flags + shape survive into the match...
    assert rules["over_boundary_out"] is True
    assert rules["super_over_on_tie"] is True
    assert rules["overs_per_innings"] == 5 and rules["balls_per_over"] == 6
    # ...while players_per_side adapts to the actual XI that was picked (3 here).
    assert rules["players_per_side"] == 3
    client.delete(f"/api/v1/matches/{started['match_id']}")


def test_knockout_creates_single_final_for_two_teams():
    tids = [client.post("/api/v1/teams", json={"name": n}).json()["id"] for n in ["X", "Y"]]
    r = client.post("/api/v1/tournaments", json={"name": "KO", "format": "knockout", "team_ids": tids})
    assert r.status_code == 201
    t = r.json()
    assert len(t["fixtures"]) == 1  # 2 teams -> the final
    assert t["standings"] == []  # no points table in a knockout
    assert t["champion"] is None


def test_play_fixture_updates_standings_and_nrr():
    aces, aces_pids = _team_with("Aces", ["A1", "A2", "A3"])
    blues, blues_pids = _team_with("Blues", ["B1", "B2", "B3"])
    t = client.post(
        "/api/v1/tournaments",
        json={
            "name": "Mini Cup", "format": "round_robin", "team_ids": [aces, blues],
            "rules": {"name": "Mini", "format_id": "mini", "overs_per_innings": 1, "balls_per_over": 6},
        },
    ).json()
    assert len(t["fixtures"]) == 1
    fx = t["fixtures"][0]

    started = client.post(
        f"/api/v1/tournaments/fixtures/{fx['id']}/start",
        json={"squad_a_ids": aces_pids, "squad_b_ids": blues_pids, "bat_first": "a"},
    ).json()
    mid = started["match_id"]
    assert mid is not None

    def ball(b):
        client.post(f"/api/v1/matches/{mid}/balls", json=b)

    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B1"})
    ball({"action": "runs", "value": 4}); ball({"action": "runs", "value": 4})
    ball({"action": "wicket", "dismissal": "caught", "fielder": "B2"})
    ball({"action": "runs", "value": 4}); ball({"action": "runs", "value": 4})
    ball({"action": "wicket", "dismissal": "bowled"})
    client.post(f"/api/v1/matches/{mid}/second-innings")
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "A1"})
    ball({"action": "runs", "value": 4}); ball({"action": "runs", "value": 4})
    ball({"action": "wicket", "dismissal": "bowled"})
    ball({"action": "runs", "value": 4}); ball({"action": "runs", "value": 0})
    ball({"action": "wicket", "dismissal": "bowled"})

    detail = client.get(f"/api/v1/tournaments/{t['id']}").json()
    st = {s["name"]: s for s in detail["standings"]}
    assert st["Aces"]["won"] == 1 and st["Aces"]["points"] == 2 and st["Aces"]["played"] == 1
    assert st["Blues"]["lost"] == 1 and st["Blues"]["points"] == 0
    # NRR: 16 for, 12 against in 1 over each -> +4 / -4
    assert st["Aces"]["nrr"] == 4.0
    assert st["Blues"]["nrr"] == -4.0
    # standings sorted: Aces top
    assert detail["standings"][0]["name"] == "Aces"
    # fixture reflects completion
    assert detail["fixtures"][0]["status"] == "completed"
    assert "Aces won" in detail["fixtures"][0]["result"]


def test_tournament_404():
    assert client.get("/api/v1/tournaments/999999").status_code == 404
