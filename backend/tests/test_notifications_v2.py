"""Notification ecosystem P1 — entity follow, prefs-aware fan-out, categories, the
per-user realtime SSE stream, and the match-finished producer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.repositories.social_repository import InMemorySocialRepository
from app.repositories.user_repository import InMemoryUserRepository
from app.services.social_service import SocialService

client = TestClient(app)

RULES = {"name": "T20", "format_id": "t20", "players_per_side": 2, "overs_per_innings": 1, "balls_per_over": 6}


# ---- pure service / repo (fan-out + prefs + version) ----
def _svc() -> tuple[SocialService, InMemorySocialRepository]:
    repo = InMemorySocialRepository()
    return SocialService(repo, InMemoryUserRepository()), repo


def test_notify_followers_respects_category_prefs_and_exclude():
    svc, repo = _svc()
    for u in ("u1", "u2", "u3"):
        repo.follow_entity(u, "team", "5")
    repo.set_prefs("u2", {"team": False})           # u2 opted out of team notifications
    sent = svc.notify_followers("team", "5", category="team", kind="team",
                                text="Playing XI announced", link="#/team/5", exclude="u3")
    assert sent == 1                                 # u1 only (u2 opted out, u3 excluded/actor)
    assert repo.unread_count("u1") == 1
    assert repo.unread_count("u2") == 0 and repo.unread_count("u3") == 0
    assert repo.notifications("u1")[0].category == "team"


def test_notification_version_tracks_unread_and_maxid():
    svc, repo = _svc()
    assert svc.notification_version("u1") == (0, 0)
    repo.add_notification("u1", "match", "Match finished", "#/match/1", category="match")
    repo.add_notification("u1", "social", "New follower", "")
    v = svc.notification_version("u1")
    assert v[0] == 2 and v[1] > 0                    # 2 unread, a real max id
    repo.mark_read("u1")
    assert svc.notification_version("u1")[0] == 0    # read → unread 0, max id unchanged


def test_category_backfilled_on_read_for_legacy_kinds():
    svc, repo = _svc()
    repo.add_notification("u1", "follow", "X started following you", "")   # no category stored
    assert svc.notifications("u1")[0].category == "social"                 # derived from kind


# ---- entity follow via the API ----
def test_entity_follow_roundtrip():
    st = client.get("/api/v1/social/follow/entity/team/42").json()
    assert st == {"is_following": False, "followers": 0}
    assert client.post("/api/v1/social/follow/entity/team/42").json()["is_following"] is True
    assert client.get("/api/v1/social/follow/entity/team/42").json()["followers"] >= 1
    ents = client.get("/api/v1/social/following/entities").json()
    assert {"entity_type": "team", "entity_id": "42"} in ents
    assert client.delete("/api/v1/social/follow/entity/team/42").json()["is_following"] is False


def test_follow_rejects_unknown_entity_type():
    assert client.post("/api/v1/social/follow/entity/spaceship/1").status_code == 400


def test_preferences_get_and_update():
    d = client.get("/api/v1/social/notifications/preferences").json()
    assert d["match"] is True and d["marketing"] is False
    up = client.put("/api/v1/social/notifications/preferences", json={"match": False, "marketing": True}).json()
    assert up["match"] is False and up["marketing"] is True
    assert client.get("/api/v1/social/notifications/preferences").json()["match"] is False
    client.put("/api/v1/social/notifications/preferences", json={"match": True, "marketing": False})  # reset


# ---- realtime SSE ----
def test_notification_sse_stream_one_shot():
    token = create_access_token({"sub": "sse-user", "role": "player"})
    r = client.get(f"/api/v1/social/notifications/stream?token={token}&once=1")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    assert '"unread"' in r.text and '"latest"' in r.text


def test_notification_sse_rejects_bad_token():
    assert client.get("/api/v1/social/notifications/stream?token=garbage&once=1").status_code == 401
    assert client.get("/api/v1/social/notifications/stream?once=1").status_code == 401


# ---- generator: follow a match → get notified when it finishes ----
def test_match_finished_notifies_followers():
    # the per-test NotificationDispatcher (conftest) starts with empty idempotency state
    mid = client.post("/api/v1/matches", json={
        "team_a": "A", "team_b": "B", "bat_first": "a", "rules": RULES,
        "squad_a": ["a1", "a2"], "squad_b": ["b1", "b2"]}).json()["id"]
    client.post(f"/api/v1/social/follow/entity/match/{mid}")     # follow BEFORE it finishes

    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "b1"})
    for _ in range(6):
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})   # A: 6
    client.post(f"/api/v1/matches/{mid}/second-innings")
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "a1"})
    for _ in range(6):
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 0})   # B: 0 → A wins
    assert client.get(f"/api/v1/matches/{mid}").json()["result"]     # match finished

    notes = client.get("/api/v1/social/notifications").json()
    assert any(n["category"] == "match" and "finish" in (n["title"] or "").lower() for n in notes)
    client.delete(f"/api/v1/matches/{mid}")
