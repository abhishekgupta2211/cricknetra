"""Admin broadcast announcements (P5) — fan-out with opt-outs, the email channel,
and the delivered/opened/clicked engagement funnel + CTR."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_user, get_social_service
from app.main import app
from app.repositories.social_repository import InMemorySocialRepository
from app.repositories.user_repository import InMemoryUserRepository, UserRecord
from app.services import email_service
from app.services.social_service import SocialError, SocialService

client = TestClient(app)


def _svc():
    users = InMemoryUserRepository()
    social = InMemorySocialRepository()
    return SocialService(social, users), social, users


_n = 0


def _user(users, role="player", email=None):
    global _n
    _n += 1
    return users.add_user(full_name=f"U{_n}", username=f"u{_n}", mobile_no=f"9{_n:09d}",
                          password_hash="x", role=role, email=email)


# --------------------------------------------------------------------------- #
# fan-out + opt-outs
# --------------------------------------------------------------------------- #
def test_system_broadcast_reaches_every_user():
    svc, social, users = _svc()
    admin = _user(users, role="admin")
    a, b = _user(users), _user(users)
    res = svc.broadcast(admin, title="Maintenance", text="Down at 2am", category="system")
    assert res["audience"] == 3 and res["recipients"] == 3      # system is on by default for all
    assert social.unread_count(a.id) == 1 and social.unread_count(b.id) == 1
    assert social.notifications(a.id)[0].category == "system"


def test_marketing_broadcast_only_reaches_opted_in():
    svc, social, users = _svc()
    admin = _user(users, role="admin")
    a, b = _user(users), _user(users)
    social.set_prefs(a.id, {"marketing": True})                 # marketing is opt-IN (default False)
    res = svc.broadcast(admin, title="Sale", text="50% off pro", category="marketing", link="#/pro")
    assert res["recipients"] == 1                               # only a opted in
    assert social.unread_count(a.id) == 1 and social.unread_count(b.id) == 0


def test_broadcast_rejects_non_announcement_category():
    svc, social, users = _svc()
    admin = _user(users, role="admin")
    with pytest.raises(SocialError):
        svc.broadcast(admin, title="x", text="y", category="match")


# --------------------------------------------------------------------------- #
# email channel
# --------------------------------------------------------------------------- #
def test_broadcast_emails_only_opted_in_addresses(monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(email_service, "_SYNC", True)
    monkeypatch.setattr(email_service, "_send", lambda to, subj, body: sent.append((to, subj)))

    svc, social, users = _svc()
    admin = _user(users, role="admin")
    mailed = _user(users, email="fan@example.com")
    _user(users, email="silent@example.com")                   # has email but email_enabled off
    social.set_prefs(mailed.id, {"email_enabled": True})

    svc.broadcast(admin, title="Notice", text="Read this", category="system", link="#/x")
    assert [to for to, _ in sent] == ["fan@example.com"]        # only the opted-in address
    assert sent[0][1] == "Notice"


# --------------------------------------------------------------------------- #
# engagement funnel: delivered / opened / clicked + rates
# --------------------------------------------------------------------------- #
def test_announcement_analytics_tracks_open_and_click_rates():
    svc, social, users = _svc()
    admin = _user(users, role="admin")
    a, b, c = _user(users), _user(users), _user(users)
    svc.broadcast(admin, title="News", text="hi", category="system", link="#/n")
    # audience = admin + a + b + c = 4 delivered
    social.mark_read(a.id)                                      # a opens
    b_nid = social.notifications(b.id)[0].id
    svc.mark_clicked(b.id, b_nid)                               # b clicks (implies open)

    stats = svc.announcement_analytics()
    assert len(stats) == 1
    s = stats[0]
    assert s["delivered"] == 4 and s["opened"] == 2 and s["clicked"] == 1
    assert s["open_rate"] == 0.5 and s["ctr"] == 0.25


# --------------------------------------------------------------------------- #
# routes
# --------------------------------------------------------------------------- #
def test_announcement_route_requires_admin():
    player = UserRecord(id="9", full_name="P", username="pp", mobile_no="9000000009",
                        user_code="CN9", role_code="PLR9", password="", role="player",
                        is_active=True, is_verified=True,
                        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    app.dependency_overrides[get_current_active_user] = lambda: player   # conftest teardown restores
    r = client.post("/api/v1/admin/announcements", json={"title": "x", "text": "y"})
    assert r.status_code == 403


def test_click_route_records_engagement():
    svc = app.dependency_overrides[get_social_service]()
    svc.social.add_notification("0", "admin", "hi", "#/x", category="system",
                                title="N", campaign_id="c1")
    nid = svc.social.notifications("0")[0].id
    assert client.post(f"/api/v1/social/notifications/{nid}/click").status_code == 204
    assert svc.social.campaign_counts().get("c1", (0, 0, 0))[2] == 1      # 1 clicked


def test_announcement_and_analytics_roundtrip_via_api():
    # register a real recipient so the broadcast has an audience
    client.post("/api/v1/auth/register", json={
        "full_name": "Reader One", "username": "reader1", "mobile_no": "9888800001",
        "password": "pw123456", "role": "general_user"})
    res = client.post("/api/v1/admin/announcements",
                      json={"title": "Hello", "text": "welcome", "category": "system"}).json()
    assert res["recipients"] >= 1
    stats = client.get("/api/v1/admin/announcements/analytics").json()
    assert any(s["title"] == "Hello" and s["delivered"] >= 1 for s in stats)
