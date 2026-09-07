"""Web Push (P2) — VAPID key, subscription storage, prefs-gated fan-out to devices,
dead-subscription pruning, and 'log out everywhere'."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_social_service
from app.core import webpush
from app.core.security import hash_password
from app.main import app
from app.repositories.auth_token_repository import InMemoryAuthTokenRepository
from app.repositories.social_repository import InMemorySocialRepository
from app.repositories.user_repository import InMemoryUserRepository
from app.services import push_service
from app.services.auth_service import AuthError, AuthService
from app.services.social_service import SocialService

client = TestClient(app)


@pytest.fixture
def push_sync(monkeypatch):
    """Deliver pushes inline (assertable) and pretend pywebpush is present."""
    monkeypatch.setattr(push_service, "_SYNC", True)
    monkeypatch.setattr(webpush, "available", lambda: True)


@pytest.fixture
def sent(monkeypatch):
    """Capture every webpush.send call as (subscription_info, payload)."""
    calls: list[tuple[dict, dict]] = []

    def rec(info, payload, ttl=3600):
        calls.append((info, payload))
        return 201

    monkeypatch.setattr(webpush, "send", rec)
    return calls


# --------------------------------------------------------------------------- #
# delivery + pruning (push_service._deliver)
# --------------------------------------------------------------------------- #
def test_delivery_prunes_dead_subscription_on_410(monkeypatch):
    repo = InMemorySocialRepository()
    repo.add_subscription("u1", "https://good", "p", "a")
    repo.add_subscription("u1", "https://dead", "p", "a")

    def fake_send(info, payload, ttl=3600):
        return 410 if info["endpoint"] == "https://dead" else 201

    monkeypatch.setattr(webpush, "send", fake_send)
    push_service._deliver(repo, "u1", {"title": "t", "body": "b"})

    eps = {s.endpoint for s in repo.subscriptions_for_user("u1")}
    assert eps == {"https://good"}          # the 410 one was pruned, the good one kept


def test_delivery_prunes_on_gone_exception(monkeypatch):
    repo = InMemorySocialRepository()
    repo.add_subscription("u1", "https://dead", "p", "a")

    def boom(info, payload, ttl=3600):
        exc = Exception("gone")
        exc.response = type("R", (), {"status_code": 410})()
        raise exc

    monkeypatch.setattr(webpush, "send", boom)
    push_service._deliver(repo, "u1", {"title": "t", "body": "b"})
    assert repo.subscriptions_for_user("u1") == []


def test_delivery_keeps_subscription_on_transient_error(monkeypatch):
    repo = InMemorySocialRepository()
    repo.add_subscription("u1", "https://ep", "p", "a")

    def boom(info, payload, ttl=3600):
        raise RuntimeError("network blip")   # no .response → transient, don't prune

    monkeypatch.setattr(webpush, "send", boom)
    push_service._deliver(repo, "u1", {"title": "t", "body": "b"})
    assert len(repo.subscriptions_for_user("u1")) == 1


def test_push_url_maps_hash_links():
    assert push_service._push_url("#/match/9") == "/app/#/match/9"
    assert push_service._push_url("") == "/app/"
    assert push_service._push_url("https://x/y") == "https://x/y"


# --------------------------------------------------------------------------- #
# fan-out honours push_enabled + category prefs
# --------------------------------------------------------------------------- #
def test_notify_followers_pushes_only_to_enabled_devices(push_sync, sent):
    repo = InMemorySocialRepository()
    svc = SocialService(repo, InMemoryUserRepository())
    for u in ("u1", "u2"):
        repo.follow_entity(u, "team", "7")
        repo.add_subscription(u, f"https://ep/{u}", "p", "a")
    repo.set_prefs("u2", {"push_enabled": False})    # u2 keeps in-app, drops push

    svc.notify_followers("team", "7", category="team", kind="team",
                         text="Playing XI announced", link="#/team/7", title="Team update")

    assert repo.unread_count("u2") == 1              # u2 still got the in-app notification
    assert [info["endpoint"] for info, _ in sent] == ["https://ep/u1"]
    _, payload = sent[0]
    assert payload["title"] == "Team update" and payload["url"] == "/app/#/team/7"
    assert payload["tag"] == "team:7" and payload["category"] == "team"


def test_category_optout_suppresses_push_entirely(push_sync, sent):
    repo = InMemorySocialRepository()
    svc = SocialService(repo, InMemoryUserRepository())
    repo.follow_entity("u1", "team", "7")
    repo.add_subscription("u1", "https://ep/u1", "p", "a")
    repo.set_prefs("u1", {"team": False})           # opted out of team category

    svc.notify_followers("team", "7", category="team", kind="team", text="x", link="#/team/7")
    assert repo.unread_count("u1") == 0 and sent == []


def test_follow_pushes_new_follower_alert(push_sync, sent):
    users = InMemoryUserRepository()
    repo = InMemorySocialRepository()
    follower = users.add_user(full_name="Bob B", username="bob", mobile_no="9990001111",
                              password_hash="x", role="player")
    target = users.add_user(full_name="Amy A", username="amy", mobile_no="9990002222",
                            password_hash="x", role="player")
    repo.add_subscription(target.id, "https://ep/amy", "p", "a")

    SocialService(repo, users).follow(follower, target.id)

    assert len(sent) == 1
    _, payload = sent[0]
    assert payload["title"] == "New follower" and "bob" in payload["body"]


# --------------------------------------------------------------------------- #
# 'log out everywhere' — refresh tokens revoked, push devices forgotten
# --------------------------------------------------------------------------- #
def test_logout_all_revokes_every_refresh_token():
    users = InMemoryUserRepository()
    u = users.add_user(full_name="Cara C", username="cara", mobile_no="9992223333",
                       password_hash=hash_password("pw123456"), role="player")
    tokens = InMemoryAuthTokenRepository()
    auth = AuthService(users, None, tokens)

    a = auth._issue(u)["refresh_token"]
    b = auth._issue(u)["refresh_token"]              # a second device
    auth.logout_all(u.id)

    for tok in (a, b):
        with pytest.raises(AuthError):
            auth.refresh(tok)                        # both sessions dead


# --------------------------------------------------------------------------- #
# routes (run as the default admin, id "0")
# --------------------------------------------------------------------------- #
def test_vapid_key_endpoint():
    d = client.get("/api/v1/social/push/vapid-key").json()
    assert d["available"] is True and len(d["key"]) > 40 and "=" not in d["key"]


def test_subscribe_and_unsubscribe_roundtrip():
    svc = app.dependency_overrides[get_social_service]()
    body = {"endpoint": "https://fcm/abc", "keys": {"p256dh": "P", "auth": "A"}, "platform": "web"}
    assert client.post("/api/v1/social/push/subscribe", json=body).status_code == 204
    stored = svc.social.subscriptions_for_user("0")
    assert len(stored) == 1 and stored[0].endpoint == "https://fcm/abc"

    assert client.post("/api/v1/social/push/unsubscribe",
                       json={"endpoint": "https://fcm/abc"}).status_code == 204
    assert svc.social.subscriptions_for_user("0") == []


def test_logout_all_route_clears_push_subscriptions():
    svc = app.dependency_overrides[get_social_service]()
    svc.social.add_subscription("0", "https://ep/admin", "p", "a")
    assert svc.social.subscriptions_for_user("0")
    assert client.post("/api/v1/auth/logout-all").status_code == 204
    assert svc.social.subscriptions_for_user("0") == []


def test_rotate_moves_existing_subscription_to_new_endpoint():
    repo = InMemorySocialRepository()
    svc = SocialService(repo, InMemoryUserRepository())
    repo.add_subscription("u9", "https://old", "p", "a")

    assert svc.rotate_push_subscription("https://old", "https://new", "p2", "a2") is True
    eps = {s.endpoint for s in repo.subscriptions_for_user("u9")}
    assert eps == {"https://new"}                       # old gone, new under same owner
    # rotating an unknown endpoint is a no-op (doesn't create a subscription)
    assert svc.rotate_push_subscription("https://unknown", "https://x", "p", "a") is False
    assert repo.subscription_owner("https://x") is None


def test_rotate_route_is_unauthenticated_and_idempotent():
    svc = app.dependency_overrides[get_social_service]()
    svc.social.add_subscription("0", "https://old-ep", "p", "a")
    body = {"old_endpoint": "https://old-ep", "endpoint": "https://new-ep",
            "keys": {"p256dh": "p2", "auth": "a2"}}
    assert client.post("/api/v1/social/push/rotate", json=body).status_code == 204
    assert svc.social.subscription_owner("https://new-ep") == "0"
    assert svc.social.subscription_owner("https://old-ep") is None
