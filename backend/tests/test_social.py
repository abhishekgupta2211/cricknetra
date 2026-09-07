"""Community / social — follow graph, activity feed, notifications.

The two-user logic (follow notifies the target; a user's activity reaches their
followers' feed + inbox) is tested at the service level, since the API test
client runs as a single default admin. The endpoints/wiring are smoke-tested too.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.social_repository import InMemorySocialRepository
from app.repositories.user_repository import InMemoryUserRepository
from app.services.social_service import SocialError, SocialService

client = TestClient(app)


# ----- service-level (two real users) --------------------------------------
def _svc_two():
    users = InMemoryUserRepository()
    a = users.add_user("Alice A", "alice", "1111111111", "x", "player")
    b = users.add_user("Bob B", "bob", "2222222222", "x", "player")
    return SocialService(InMemorySocialRepository(), users), a, b


def test_follow_tracks_and_notifies_the_target():
    svc, a, b = _svc_two()
    state = svc.follow(a, b.id)
    assert state.is_following is True
    assert state.followers == 1            # bob now has one follower
    assert svc.following_ids(a.id) == [b.id]
    notes = svc.notifications(b.id)         # bob was notified
    assert len(notes) == 1 and "alice" in notes[0].text.lower()
    assert svc.unread(b.id) == 1


def test_following_a_user_surfaces_their_activity_in_your_feed():
    svc, a, b = _svc_two()
    svc.follow(a, b.id)
    svc.record(b, "match", "started scoring Lions vs Bears", "/m/9")
    feed = svc.feed(a.id)                   # alice follows bob
    assert any(i.actor_name == "bob" and "scoring" in i.text for i in feed)
    assert svc.unread(a.id) == 1           # and alice got a "bob did X" notification


def test_cannot_follow_yourself():
    svc, a, _b = _svc_two()
    with pytest.raises(SocialError):
        svc.follow(a, a.id)


def test_mark_read_clears_unread():
    svc, a, b = _svc_two()
    svc.follow(a, b.id)
    assert svc.unread(b.id) == 1
    svc.mark_read(b.id)
    assert svc.unread(b.id) == 0


def test_unfollow_removes_the_edge():
    svc, a, b = _svc_two()
    svc.follow(a, b.id)
    svc.unfollow(a, b.id)
    assert svc.following_ids(a.id) == []
    assert svc.state(a.id, b.id).is_following is False


def test_delete_notification_removes_it():
    svc, a, b = _svc_two()
    svc.follow(a, b.id)                     # bob now has one notification
    note_id = svc.notifications(b.id)[0].id
    assert svc.delete_notification(b.id, note_id) is True
    assert svc.notifications(b.id) == []
    assert svc.delete_notification(b.id, note_id) is False  # idempotent: already gone


def test_cannot_delete_someone_elses_notification():
    svc, a, b = _svc_two()
    svc.follow(a, b.id)                     # the notification belongs to bob
    note_id = svc.notifications(b.id)[0].id
    assert svc.delete_notification(a.id, note_id) is False  # alice can't delete it
    assert len(svc.notifications(b.id)) == 1                # still there


# ----- API wiring (runs as the default admin) ------------------------------
def test_follow_unfollow_endpoints():
    bob = client.post("/api/v1/auth/register", json={
        "full_name": "Bob Builder", "username": "bobx", "mobile_no": "9991110000",
        "password": "secret1", "role": "player",
    }).json()
    bid = bob["id"]
    st = client.post(f"/api/v1/social/follow/{bid}").json()
    assert st["is_following"] is True and st["followers"] == 1
    assert client.get("/api/v1/social/following").json() == [bid]
    st2 = client.delete(f"/api/v1/social/follow/{bid}").json()
    assert st2["is_following"] is False
    assert client.get("/api/v1/social/following").json() == []


def test_follow_self_rejected_via_api():
    assert client.post("/api/v1/social/follow/0").status_code == 400  # admin's own id


def test_feed_includes_own_match_activity():
    client.post("/api/v1/matches", json={"team_a": "Aces", "team_b": "Blues", "format_id": "t20"})
    feed = client.get("/api/v1/social/feed").json()
    assert any(i["kind"] == "match" and "Aces" in i["text"] for i in feed)


def test_notifications_endpoints_ok():
    assert client.get("/api/v1/social/notifications").status_code == 200
    assert "count" in client.get("/api/v1/social/notifications/unread").json()
    assert client.post("/api/v1/social/notifications/read").status_code == 204
    # delete is idempotent — a no-op on a non-existent id still returns 204
    assert client.delete("/api/v1/social/notifications/999999").status_code == 204
