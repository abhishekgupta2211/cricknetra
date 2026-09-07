"""Venue / toss / tournament are captured at match creation and returned on the state."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_match_meta_captured_and_returned():
    mid = client.post("/api/v1/matches", json={
        "team_a": "CSK", "team_b": "MI", "bat_first": "a", "format_id": "t20",
        "venue": "MA Chidambaram Stadium", "tournament": "Summer Cup 2026", "match_no": "Final",
        "toss_winner": "b", "toss_decision": "bowl",
    }).json()
    st = client.get(f"/api/v1/matches/{mid['id']}").json()
    m = st["meta"]
    assert m["venue"] == "MA Chidambaram Stadium"
    assert m["tournament"] == "Summer Cup 2026"
    assert m["match_no"] == "Final"
    assert m["toss_winner"] == "MI"          # 'b' resolved to the team name
    assert m["toss_decision"] == "bowl"
    assert m["toss_text"] == "MI won the toss and chose to bowl"
    client.delete(f"/api/v1/matches/{mid['id']}")


def test_match_meta_absent_by_default():
    mid = client.post("/api/v1/matches",
                      json={"team_a": "A", "team_b": "B", "bat_first": "a", "format_id": "t20"}).json()["id"]
    m = client.get(f"/api/v1/matches/{mid}").json()["meta"]
    assert m["venue"] is None and m["toss_winner"] is None and m["toss_text"] is None
    client.delete(f"/api/v1/matches/{mid}")


def test_match_meta_toss_winner_without_decision():
    mid = client.post("/api/v1/matches", json={
        "team_a": "A", "team_b": "B", "bat_first": "a", "format_id": "t20", "toss_winner": "a",
    }).json()["id"]
    m = client.get(f"/api/v1/matches/{mid}").json()["meta"]
    assert m["toss_winner"] == "A" and m["toss_decision"] is None
    assert m["toss_text"] == "A won the toss"
    client.delete(f"/api/v1/matches/{mid}")
