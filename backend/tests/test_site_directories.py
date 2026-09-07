"""The public directories render real data from the same services as the API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_live_matches_shows_scored_match():
    rules = {"name": "Mini", "format_id": "mini", "overs_per_innings": 2, "balls_per_over": 6}
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "Lions", "team_b": "Bears", "bat_first": "a", "rules": rules},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Bears 1"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})

    r = client.get("/live-matches")
    assert r.status_code == 200
    assert "Lions" in r.text and "Bears" in r.text
    assert "4/0" in r.text           # live score rendered
    assert "Live" in r.text          # status badge
    client.delete(f"/api/v1/matches/{mid}")


def test_highlights_gallery_shows_match_clips():
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "Comets", "team_b": "Meteors", "bat_first": "a"},
    ).json()["id"]
    # attach a highlight clip (tests run as admin, so owner/admin gating passes)
    r = client.post(
        f"/api/v1/matches/{mid}/clips",
        json={"url": "https://youtu.be/dQw4w9WgXcQ", "label": "Last-ball six"},
    )
    assert r.status_code == 201

    r = client.get("/highlights")
    assert r.status_code == 200
    assert "Comets" in r.text and "Meteors" in r.text        # grouped by match
    assert "Last-ball six" in r.text                          # clip label rendered
    assert "youtube.com/embed/dQw4w9WgXcQ" in r.text          # safe embed
    client.delete(f"/api/v1/matches/{mid}")


def test_highlights_link_is_in_site_nav():
    # the Highlights entry is available site-wide, not just on its own page
    r = client.get("/live-matches")
    assert r.status_code == 200
    assert 'href="/highlights"' in r.text


def test_highlights_empty_state_when_no_clips():
    # a match with no clips must not appear on the highlights gallery
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "Noclip", "team_b": "Bland", "bat_first": "a"},
    ).json()["id"]
    r = client.get("/highlights")
    assert r.status_code == 200
    assert "Noclip" not in r.text
    client.delete(f"/api/v1/matches/{mid}")


def test_tournaments_shows_created_cup():
    a = client.post("/api/v1/teams", json={"name": "Aces"}).json()["id"]
    b = client.post("/api/v1/teams", json={"name": "Blues"}).json()["id"]
    tid = client.post(
        "/api/v1/tournaments",
        json={"name": "Premier Cup", "format": "round_robin", "format_id": "t20", "team_ids": [a, b]},
    ).json()["id"]

    r = client.get("/tournaments")
    assert r.status_code == 200
    assert "Premier Cup" in r.text
    assert "League" in r.text         # format badge
    client.delete(f"/api/v1/tournaments/{tid}")
    client.delete(f"/api/v1/teams/{a}")
    client.delete(f"/api/v1/teams/{b}")
