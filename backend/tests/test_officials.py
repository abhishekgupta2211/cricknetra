"""Per-match umpire approval — request → owner approves → umpire can score."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.deps import get_current_active_user, get_current_user
from app.main import app

client = TestClient(app)


def _as(role: str, uid: str):
    now = datetime.now(timezone.utc)
    u = type("U", (), {})()
    u.id, u.role, u.is_active = uid, role, True
    u.full_name, u.username, u.mobile_no = "U " + uid, "u" + uid, "x"
    u.user_code = u.role_code = u.password = "x"
    u.is_verified = True
    u.created_at = u.updated_at = now
    app.dependency_overrides[get_current_active_user] = lambda: u
    app.dependency_overrides[get_current_user] = lambda: u
    return u


def _match(owner_uid: str):
    _as("organizer", owner_uid)
    return client.post(
        "/api/v1/matches", json={"team_a": "A", "team_b": "B", "format_id": "t20", "bat_first": "a"}
    ).json()["id"]


def test_request_approve_flow_unlocks_scoring():
    mid = _match("100")
    _as("umpire", "400")
    s = client.get(f"/api/v1/matches/{mid}/officials").json()
    assert s["my_status"] == "none" and s["can_score"] is False
    assert client.post(f"/api/v1/matches/{mid}/officials/request").status_code == 204
    assert client.get(f"/api/v1/matches/{mid}/officials").json()["my_status"] == "pending"
    # umpire still can't score while pending
    assert client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B 1"}).status_code == 403

    _as("organizer", "100")  # owner sees + approves the request
    mgr = client.get(f"/api/v1/matches/{mid}/officials").json()
    assert mgr["is_manager"] is True
    assert any(o["umpire_id"] == "400" and o["status"] == "pending" for o in mgr["officials"])
    assert client.post(f"/api/v1/matches/{mid}/officials/400/approve").status_code == 204

    _as("umpire", "400")  # now approved → can score
    assert client.get(f"/api/v1/matches/{mid}/officials").json()["can_score"] is True
    assert client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B 1"}).status_code == 200


def test_owner_can_decline():
    mid = _match("101")
    _as("umpire", "401")
    client.post(f"/api/v1/matches/{mid}/officials/request")
    _as("organizer", "101")
    assert client.delete(f"/api/v1/matches/{mid}/officials/401").status_code == 204
    _as("umpire", "401")
    assert client.get(f"/api/v1/matches/{mid}/officials").json()["my_status"] == "none"


def test_request_is_open_to_signed_in_users():
    mid = _match("102")
    _as("player", "402")  # anyone signed in may ask; the owner gates via approval
    assert client.post(f"/api/v1/matches/{mid}/officials/request").status_code == 204
    assert client.get(f"/api/v1/matches/{mid}/officials").json()["my_status"] == "pending"


def test_non_owner_cannot_approve():
    mid = _match("103")
    _as("umpire", "403")
    client.post(f"/api/v1/matches/{mid}/officials/request")
    _as("organizer", "999")  # a different organizer, not the match owner
    assert client.post(f"/api/v1/matches/{mid}/officials/403/approve").status_code == 403


def test_pending_inbox_lists_only_your_matches_requests():
    mid = _match("105")  # organizer 105 owns this match
    _as("umpire", "405")
    client.post(f"/api/v1/matches/{mid}/officials/request")
    # the owner sees the request in the consolidated inbox (no need to open the match)
    _as("organizer", "105")
    inbox = client.get("/api/v1/matches/officials/pending").json()
    item = next((r for r in inbox if r["umpire_id"] == "405" and r["match_id"] == mid), None)
    assert item is not None
    assert item["match_label"] == "A vs B" or item["match_label"].startswith("Match")
    # a different organizer (owns nothing) gets an empty inbox — only your own matches
    _as("organizer", "888")
    assert client.get("/api/v1/matches/officials/pending").json() == []


def test_approved_umpire_scoring_records_umpired():
    mid = _match("104")
    _as("umpire", "404")
    client.post(f"/api/v1/matches/{mid}/officials/request")
    _as("organizer", "104")
    client.post(f"/api/v1/matches/{mid}/officials/404/approve")
    _as("umpire", "404")
    assert client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B 1"}).status_code == 200
    assert client.get("/api/v1/auth/me").json()["records"]["matches_umpired"] == 1
