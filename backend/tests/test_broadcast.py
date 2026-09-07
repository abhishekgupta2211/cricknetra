"""Broadcast presentation-mode channel — the single OBS overlay source's current
screen, set by the operator and polled by every overlay instance."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _new_match() -> str:
    return client.post("/api/v1/matches",
                       json={"team_a": "A", "team_b": "B", "bat_first": "a", "format_id": "t20"}).json()["id"]


def test_broadcast_default_is_live():
    mid = _new_match()
    d = client.get(f"/api/v1/matches/{mid}/broadcast").json()
    assert d == {"mode": "LIVE", "auto": False, "seq": 0}
    client.delete(f"/api/v1/matches/{mid}")


def test_broadcast_set_mode_and_auto_bump_seq():
    mid = _new_match()
    r = client.post(f"/api/v1/matches/{mid}/broadcast", json={"mode": "wagon"}).json()
    assert r["mode"] == "WAGON" and r["seq"] == 1                 # case-insensitive, seq bumped
    assert client.get(f"/api/v1/matches/{mid}/broadcast").json()["mode"] == "WAGON"   # persists
    r2 = client.post(f"/api/v1/matches/{mid}/broadcast", json={"auto": True}).json()
    assert r2["auto"] is True and r2["mode"] == "WAGON" and r2["seq"] == 2
    # a no-op set does NOT bump seq (avoids needless transitions)
    same = client.post(f"/api/v1/matches/{mid}/broadcast", json={"mode": "WAGON"}).json()
    assert same["seq"] == 2
    client.delete(f"/api/v1/matches/{mid}")


def test_broadcast_invalid_mode_and_missing_match():
    mid = _new_match()
    assert client.post(f"/api/v1/matches/{mid}/broadcast", json={"mode": "bogus"}).status_code == 400
    assert client.get("/api/v1/matches/99999999/broadcast").status_code == 404
    assert client.post("/api/v1/matches/99999999/broadcast", json={"mode": "LIVE"}).status_code == 404
    client.delete(f"/api/v1/matches/{mid}")
