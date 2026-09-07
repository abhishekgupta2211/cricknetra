"""The highlights hub API: cross-match clip gallery + the user's manageable matches."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _mk(a: str, b: str) -> str:
    return client.post(
        "/api/v1/matches", json={"team_a": a, "team_b": b, "bat_first": "a"}
    ).json()["id"]


def test_highlights_endpoint_groups_clips_by_match():
    mid = _mk("Falcons", "Eagles")
    r = client.post(
        f"/api/v1/matches/{mid}/clips",
        json={"url": "https://youtu.be/dQw4w9WgXcQ", "label": "Screamer"},
    )
    assert r.status_code == 201

    r = client.get("/api/v1/highlights")
    assert r.status_code == 200
    grp = next((g for g in r.json() if g["match_id"] == str(mid)), None)
    assert grp is not None, "match with clips should be in the gallery"
    assert grp["team_a"] == "Falcons" and grp["team_b"] == "Eagles"
    assert grp["live"] is True and grp["status_label"] == "Live"
    assert len(grp["clips"]) == 1
    assert grp["clips"][0]["label"] == "Screamer"
    assert "embed/dQw4w9WgXcQ" in (grp["clips"][0]["embed_url"] or "")
    client.delete(f"/api/v1/matches/{mid}")


def test_highlights_excludes_matches_without_clips():
    mid = _mk("Plain", "Empty")
    r = client.get("/api/v1/highlights")
    assert r.status_code == 200
    assert all(g["match_id"] != str(mid) for g in r.json())
    client.delete(f"/api/v1/matches/{mid}")


def test_my_matches_lists_manageable():
    mid = _mk("Owned", "Side")
    r = client.get("/api/v1/highlights/my-matches")
    assert r.status_code == 200
    ids = {m["id"] for m in r.json()}
    assert str(mid) in ids  # the admin test-user can manage it
    client.delete(f"/api/v1/matches/{mid}")
