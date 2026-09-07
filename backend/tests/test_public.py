"""Public, server-rendered, shareable pages — rich live scorecard & tournament."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_public_match_scorecard():
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "Lions", "team_b": "Tigers", "format_id": "t20", "bat_first": "a"},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Tigers 1"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 6})

    page = client.get(f"/m/{mid}")
    assert page.status_code == 200
    assert "text/html" in page.headers["content-type"]
    body = page.text
    assert "Lions vs Tigers" in body
    assert "6/0" in body
    assert 'property="og:title"' in body  # shareable link preview
    assert 'content="Lions vs Tigers"' in body
    # rich layout: tabs + sidebar + JS
    assert ">Live<" in body and ">Scorecard<" in body
    assert "Current run rate" in body
    assert "/site.js" in body
    client.delete(f"/api/v1/matches/{mid}")


def test_public_match_not_found():
    r = client.get("/m/999999")
    assert r.status_code == 404
    assert "not found" in r.text.lower()


def test_public_tournament_page():
    a = client.post("/api/v1/teams", json={"name": "Alpha"}).json()["id"]
    b = client.post("/api/v1/teams", json={"name": "Bravo"}).json()["id"]
    t = client.post(
        "/api/v1/tournaments",
        json={"name": "My League", "format": "round_robin", "team_ids": [a, b], "format_id": "t20"},
    ).json()

    page = client.get(f"/t/{t['id']}")
    assert page.status_code == 200
    body = page.text
    assert "My League" in body
    assert "Points table" in body          # standings tab label
    assert "Alpha" in body and "Bravo" in body
    assert 'property="og:title"' in body
    # rich layout: hero stat boxes + tabs + filter pills
    assert "Total matches" in body and "Total teams" in body
    assert ">Matches<" in body and ">Teams<" in body
    assert 'data-filter="upcoming"' in body

    client.delete(f"/api/v1/tournaments/{t['id']}")
    client.delete(f"/api/v1/teams/{a}")
    client.delete(f"/api/v1/teams/{b}")


def test_public_tournament_not_found():
    assert client.get("/t/999999").status_code == 404
