"""Match commentary — commentators post, anyone reads, capability-gated."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.deps import get_current_active_user, get_current_user
from app.main import app

client = TestClient(app)


def _as(role: str, uid: str = "9"):
    now = datetime.now(timezone.utc)
    u = type("U", (), {})()
    u.id, u.role, u.is_active = uid, role, True
    u.full_name, u.username, u.mobile_no = "Comm Person", "commp", "x"
    u.user_code = u.role_code = u.password = "x"
    u.is_verified = True
    u.created_at = u.updated_at = now
    app.dependency_overrides[get_current_active_user] = lambda: u
    app.dependency_overrides[get_current_user] = lambda: u
    return u


def _match():  # created as the conftest admin
    return client.post(
        "/api/v1/matches", json={"team_a": "A", "team_b": "B", "format_id": "t20", "bat_first": "a"}
    ).json()["id"]


def test_commentator_can_post_and_anyone_can_read():
    mid = _match()
    _as("commentator", uid="50")
    r = client.post(f"/api/v1/matches/{mid}/commentary", json={"text": "What a shot!"})
    assert r.status_code == 201
    assert r.json()["text"] == "What a shot!" and r.json()["author_name"] == "Comm Person"
    # reading is public
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_current_user, None)
    items = client.get(f"/api/v1/matches/{mid}/commentary").json()
    assert any(c["text"] == "What a shot!" for c in items)


def test_commentary_requires_capability():
    mid = _match()
    _as("player", uid="60")  # players can't commentate
    assert client.post(f"/api/v1/matches/{mid}/commentary", json={"text": "hi"}).status_code == 403


def test_posting_records_commentated_once():
    mid = _match()
    _as("commentator", uid="70")
    client.post(f"/api/v1/matches/{mid}/commentary", json={"text": "Six!"})
    client.post(f"/api/v1/matches/{mid}/commentary", json={"text": "Four!"})
    rec = client.get("/api/v1/auth/me").json()["records"]
    assert rec["matches_commentated"] == 1  # idempotent per (user, match)


def test_commentary_404_for_unknown_match():
    _as("commentator", uid="80")
    assert client.post("/api/v1/matches/999999/commentary", json={"text": "x"}).status_code == 404


# ----- auto ball-by-ball feed -----------------------------------------------
def test_ball_feed_describes_each_delivery():
    mid = _match()  # created + scored as the conftest admin
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B 1"})
    for ball in (
        {"action": "runs", "value": 0},
        {"action": "runs", "value": 4},
        {"action": "runs", "value": 6},
        {"action": "wide", "value": 0},
        {"action": "wicket", "dismissal": "bowled"},
    ):
        client.post(f"/api/v1/matches/{mid}/balls", json=ball)

    feed = client.get(f"/api/v1/matches/{mid}/ball-feed").json()  # public
    assert [b["kind"] for b in feed] == ["dot", "four", "six", "wide", "wicket"]
    assert feed[0]["over_ball"] == "0.1"
    assert "FOUR" in feed[1]["text"]
    assert "OUT" in feed[-1]["text"]
    assert feed[2]["runs"] == 6 and feed[2]["bowler"] == "B 1"


def test_ball_feed_empty_for_new_match():
    mid = _match()
    assert client.get(f"/api/v1/matches/{mid}/ball-feed").json() == []
