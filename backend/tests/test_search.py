"""Unified search across players, teams and tournaments (members covered in test_auth)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _seed():
    client.post("/api/v1/players", json={"name": "Virat Kohli"})
    a = client.post("/api/v1/teams", json={"name": "Mumbai Indians"}).json()["id"]
    b = client.post("/api/v1/teams", json={"name": "Chennai Kings"}).json()["id"]
    client.post(
        "/api/v1/tournaments",
        json={"name": "Spring Premier Cup", "format": "round_robin", "format_id": "t20", "team_ids": [a, b]},
    )


def test_search_finds_each_entity_type():
    _seed()
    teams = client.get("/api/v1/search?q=mumbai").json()["teams"]
    assert any(t["name"] == "Mumbai Indians" for t in teams)

    players = client.get("/api/v1/search?q=KOHLI").json()["players"]  # case-insensitive
    assert any(p["name"] == "Virat Kohli" for p in players)

    tours = client.get("/api/v1/search?q=premier").json()["tournaments"]
    assert any(t["name"] == "Spring Premier Cup" for t in tours)


def test_search_no_match_returns_empty_groups():
    _seed()
    r = client.get("/api/v1/search?q=zzznotacricketthing").json()
    assert r["players"] == [] and r["teams"] == [] and r["tournaments"] == []


def test_search_members_hidden_without_auth():
    _seed()
    assert client.get("/api/v1/search?q=mumbai").json()["members"] == []
