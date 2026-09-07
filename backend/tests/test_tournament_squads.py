"""Per-tournament squads — a player is in only one team per tournament."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _team(n):
    return client.post("/api/v1/teams", json={"name": n}).json()["id"]


def _player(n):
    return client.post("/api/v1/players", json={"name": n}).json()["id"]


def _tournament(team_ids):
    return client.post(
        "/api/v1/tournaments",
        json={"name": "Cup", "format": "round_robin", "format_id": "t20", "team_ids": team_ids},
    ).json()["id"]


def test_register_and_one_team_per_tournament():
    a, b = _team("Alpha"), _team("Bravo")
    p = _player("Sharma")
    tid = _tournament([a, b])

    # register to team A
    sq = client.post(f"/api/v1/tournaments/{tid}/teams/{a}/squad", json={"player_id": p}).json()
    alpha = next(s for s in sq if s["team_id"] == a)
    assert [pl["id"] for pl in alpha["players"]] == [p]

    # the SAME player to team B in the SAME tournament -> rejected
    clash = client.post(f"/api/v1/tournaments/{tid}/teams/{b}/squad", json={"player_id": p})
    assert clash.status_code == 409
    assert "already in" in clash.json()["detail"].lower()

    # …but the same player IS allowed in a DIFFERENT tournament
    c, d = _team("Cee"), _team("Dee")
    tid2 = _tournament([c, d])
    assert client.post(f"/api/v1/tournaments/{tid2}/teams/{c}/squad", json={"player_id": p}).status_code == 200

    # unregister
    sq2 = client.delete(f"/api/v1/tournaments/{tid}/teams/{a}/squad/{p}").json()
    assert next(s for s in sq2 if s["team_id"] == a)["players"] == []


def test_fixture_xi_must_come_from_the_squad():
    a, b = _team("Aa"), _team("Bb")
    squad_a = [_player("A1"), _player("A2")]
    squad_b = [_player("B1"), _player("B2")]
    outsider = _player("Outsider")
    tid = _tournament([a, b])
    for p in squad_a:
        client.post(f"/api/v1/tournaments/{tid}/teams/{a}/squad", json={"player_id": p})
    for p in squad_b:
        client.post(f"/api/v1/tournaments/{tid}/teams/{b}/squad", json={"player_id": p})

    fx = next(
        f for f in client.get(f"/api/v1/tournaments/{tid}").json()["fixtures"]
        if f["team_a"] and f["team_b"]
    )
    by_team = {a: squad_a, b: squad_b}
    xi_a, xi_b = by_team[fx["team_a"]["id"]], by_team[fx["team_b"]["id"]]

    # an unregistered player in the XI -> rejected
    bad = client.post(
        f"/api/v1/tournaments/fixtures/{fx['id']}/start",
        json={"squad_a_ids": [xi_a[0], outsider], "squad_b_ids": xi_b, "bat_first": "a"},
    )
    assert bad.status_code == 400

    # a valid XI from the registered squads -> the match starts
    ok = client.post(
        f"/api/v1/tournaments/fixtures/{fx['id']}/start",
        json={"squad_a_ids": xi_a, "squad_b_ids": xi_b, "bat_first": "a"},
    )
    assert ok.status_code == 200
