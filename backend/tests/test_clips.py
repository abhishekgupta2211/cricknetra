"""Bring-your-own highlight clips (Option B) — owner/admin-managed clip links."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _match() -> str:
    return client.post(
        "/api/v1/matches",
        json={"team_a": "Alpha", "team_b": "Bravo", "format_id": "t20", "bat_first": "a"},
    ).json()["id"]


def test_add_list_and_remove_clip():
    mid = _match()
    assert client.get(f"/api/v1/matches/{mid}/clips").json() == []

    # tests run as admin (conftest) → owner/admin gate passes
    r = client.post(f"/api/v1/matches/{mid}/clips", json={"url": "https://youtu.be/dQw4w9WgXcQ", "label": "Big six"})
    assert r.status_code == 201
    clips = r.json()
    assert len(clips) == 1
    c = clips[0]
    assert c["kind"] == "youtube" and c["embed_url"].endswith("/embed/dQw4w9WgXcQ")
    assert c["label"] == "Big six" and c["id"]

    # a second clip gets a distinct id; the list persists on a fresh read
    client.post(f"/api/v1/matches/{mid}/clips", json={"url": "https://www.youtube.com/watch?v=abcdefghijk"})
    listed = client.get(f"/api/v1/matches/{mid}/clips").json()
    assert len(listed) == 2 and listed[0]["id"] != listed[1]["id"]

    # remove the first; the other remains
    r = client.delete(f"/api/v1/matches/{mid}/clips/{c['id']}")
    assert r.status_code == 200
    remaining = r.json()
    assert len(remaining) == 1 and remaining[0]["id"] != c["id"]


def test_bad_clip_url_rejected():
    mid = _match()
    assert client.post(f"/api/v1/matches/{mid}/clips", json={"url": "not-a-link"}).status_code == 400


def test_external_clip_link_has_no_embed():
    mid = _match()
    c = client.post(f"/api/v1/matches/{mid}/clips", json={"url": "https://example.com/clip.mp4"}).json()[0]
    assert c["kind"] == "external" and c["embed_url"] is None


def test_clips_missing_match_is_404():
    assert client.get("/api/v1/matches/999999/clips").status_code == 404
