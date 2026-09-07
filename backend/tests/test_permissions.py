"""Role capabilities + ownership gating on the mutation endpoints.

conftest runs every test as a default admin; here we override the current user to
specific roles (and to different users, to exercise ownership). Under the current
policy only admin & organizer create/score; a match is deleted by whoever owns it
(or the admin), while a team is still admin-only.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.deps import get_current_active_user, get_current_user
from app.main import app

client = TestClient(app)


def _as(role: str, uid: str = "9"):
    now = datetime.now(timezone.utc)
    user = type("U", (), {})()  # lightweight stand-in with the attrs deps read
    user.id, user.role, user.is_active = uid, role, True
    user.full_name = user.username = user.mobile_no = "x"
    user.user_code = user.role_code = user.password = "x"
    user.is_verified = True
    user.created_at = user.updated_at = now
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return user


def _match_body():
    return {"team_a": "A", "team_b": "B", "format_id": "t20", "bat_first": "a"}


# ----- capability gating on creates ----------------------------------------
def test_create_match_only_for_organizer_and_admin():
    _as("organizer")
    assert client.post("/api/v1/matches", json=_match_body()).status_code == 201
    for role in ("player", "umpire", "commentator", "general_user"):
        _as(role)
        assert client.post("/api/v1/matches", json=_match_body()).status_code == 403


def test_only_tournament_capable_roles_create_tournaments():
    _as("organizer")
    a = client.post("/api/v1/teams", json={"name": "Alpha"}).json()["id"]
    b = client.post("/api/v1/teams", json={"name": "Bravo"}).json()["id"]
    body = {"name": "Cup", "format": "round_robin", "format_id": "t20", "team_ids": [a, b]}
    _as("player")
    assert client.post("/api/v1/tournaments", json=body).status_code == 403
    _as("organizer")
    assert client.post("/api/v1/tournaments", json=body).status_code == 201


def test_rule_template_needs_manage_rules():
    rules = client.get("/api/v1/presets/t20").json()
    rules["name"] = "Mine"
    _as("team_owner")  # team_owner manages teams, not rules
    assert client.post("/api/v1/rule-templates", json=rules).status_code == 403
    _as("organizer")
    assert client.post("/api/v1/rule-templates", json=rules).status_code == 201


def test_team_create_for_team_owner_blocked_for_others():
    _as("umpire")
    assert client.post("/api/v1/teams", json={"name": "Z"}).status_code == 403
    _as("player")
    assert client.post("/api/v1/teams", json={"name": "Z"}).status_code == 403
    _as("team_owner")
    assert client.post("/api/v1/teams", json={"name": "Z"}).status_code == 201


# ----- ownership / officiating on scoring ----------------------------------
def test_scoring_requires_owner_or_approved_umpire():
    _as("organizer", uid="100")  # owner
    mid = client.post("/api/v1/matches", json=_match_body()).json()["id"]
    assert client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B 1"}).status_code == 200

    _as("umpire", uid="400")  # an umpire can't score until approved for THIS match
    assert client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1}).status_code == 403
    assert client.post(f"/api/v1/matches/{mid}/officials/request").status_code == 204  # asks to officiate

    _as("organizer", uid="100")  # the owner approves them
    assert client.post(f"/api/v1/matches/{mid}/officials/400/approve").status_code == 204

    _as("umpire", uid="400")  # now they can score
    assert client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1}).status_code == 200

    # A different organizer must NOT score somebody else's match. Both hold
    # match.score, so accepting the capability alone let one organizer take
    # over another's fixture just by knowing its id.
    _as("organizer", uid="300")
    assert client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1}).status_code == 403

    _as("player", uid="500")  # a player can't score (no match.score, not approved)
    assert client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1}).status_code == 403

    _as("organizer", uid="100")  # the owner always scores their own match
    assert client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4}).status_code == 200


# ----- deletes: a match is the owner's, a team is still admin's --------------
def test_delete_match_is_for_its_owner_and_nobody_else():
    """Whoever started a match may take it down again — the same reasoning that
    lets an organizer delete their own tournament, one level down. Another
    organizer holds every capability the owner does and must still be refused."""
    _as("organizer", uid="100")  # owner-organizer
    mid = client.post("/api/v1/matches", json=_match_body()).json()["id"]

    _as("organizer", uid="300")  # a different organizer, same role and capabilities
    assert client.delete(f"/api/v1/matches/{mid}").status_code == 403
    _as("player", uid="500")
    assert client.delete(f"/api/v1/matches/{mid}").status_code == 403

    _as("organizer", uid="100")
    assert client.delete(f"/api/v1/matches/{mid}").status_code == 204
    assert client.get(f"/api/v1/matches/{mid}").status_code == 404


def test_admin_deletes_any_match():
    """The escalation path: somebody has to be able to clean up after an
    organizer who is unreachable."""
    _as("organizer", uid="100")
    mid = client.post("/api/v1/matches", json=_match_body()).json()["id"]
    _as("admin", uid="1")
    assert client.delete(f"/api/v1/matches/{mid}").status_code == 204


def test_delete_team_is_admin_only():
    _as("team_owner", uid="100")
    tid = client.post("/api/v1/teams", json={"name": "Owned"}).json()["id"]
    assert client.delete(f"/api/v1/teams/{tid}").status_code == 403  # owner can change, not delete
    _as("admin", uid="1")
    assert client.delete(f"/api/v1/teams/{tid}").status_code == 204


# ----- reads stay public ----------------------------------------------------
def test_reads_need_no_auth():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_user, None)
    assert client.get("/api/v1/matches").status_code == 200
    assert client.get("/api/v1/leaderboards").status_code == 200
    assert client.get("/api/v1/presets").status_code == 200
