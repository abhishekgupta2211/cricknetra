"""Per-match fielding events — dropped catches / runs saved, and their stats (#144)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_RULES = {"name": "Mini", "format_id": "mini", "overs_per_innings": 2, "players_per_side": 3, "balls_per_over": 6}


def _player(n):
    return client.post("/api/v1/players", json={"name": n}).json()["id"]


def _setup():
    ids = {n: _player(n) for n in ["A1", "A2", "A3", "B1", "B2", "B3"]}
    mid = client.post("/api/v1/matches", json={
        "team_a": "Aces", "team_b": "Blues", "bat_first": "a", "rules": _RULES,
        "squad_a": ["A1", "A2", "A3"], "squad_b": ["B1", "B2", "B3"],
        "squad_a_ids": [ids["A1"], ids["A2"], ids["A3"]],
        "squad_b_ids": [ids["B1"], ids["B2"], ids["B3"]],
    }).json()["id"]
    return mid, ids


def test_log_list_and_delete_fielding():
    mid, _ = _setup()
    d = client.post(f"/api/v1/matches/{mid}/fielding", json={
        "fielder": "B2", "kind": "drop", "bowler": "B1", "batter": "A1", "over_ball": "0.3"}).json()
    s = client.post(f"/api/v1/matches/{mid}/fielding", json={"fielder": "B3", "kind": "save", "runs": 4}).json()
    assert d["kind"] == "drop" and d["fielder"] == "B2" and d["bowler"] == "B1" and d["batter"] == "A1"
    assert s["kind"] == "save" and s["runs"] == 4

    lst = client.get(f"/api/v1/matches/{mid}/fielding").json()
    assert len(lst) == 2

    assert client.delete(f"/api/v1/matches/{mid}/fielding/{d['id']}").status_code == 204
    assert len(client.get(f"/api/v1/matches/{mid}/fielding").json()) == 1


def test_drops_and_saves_surface_in_player_stats():
    mid, ids = _setup()
    client.post(f"/api/v1/matches/{mid}/fielding", json={"fielder": "B2", "kind": "drop"})
    client.post(f"/api/v1/matches/{mid}/fielding", json={"fielder": "B2", "kind": "drop"})
    client.post(f"/api/v1/matches/{mid}/fielding", json={"fielder": "B2", "kind": "save", "runs": 3})
    f = client.get(f"/api/v1/players/{ids['B2']}/stats").json()["fielding"]
    assert f["drops"] == 2 and f["runs_saved"] == 3


def test_invalid_kind_rejected():
    mid, _ = _setup()
    assert client.post(f"/api/v1/matches/{mid}/fielding", json={"fielder": "B2", "kind": "bogus"}).status_code == 400


def test_fielding_on_unknown_match_404():
    assert client.post("/api/v1/matches/999999/fielding", json={"fielder": "X", "kind": "drop"}).status_code == 404


def test_delete_unknown_fielding_404():
    mid, _ = _setup()
    assert client.delete(f"/api/v1/matches/{mid}/fielding/999999").status_code == 404
