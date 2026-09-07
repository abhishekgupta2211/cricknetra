"""Auth module — register, login (username/mobile), me, roles, profile."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_user, get_current_user
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _real_auth(_in_memory_services):
    """Auth tests need the REAL current-user dependency, not conftest's default
    admin — so they can exercise 401s and token handling."""
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_user, None)
    yield


def _signup(**over):
    body = {
        "full_name": "Rohit Sharma",
        "username": "rohit45",
        "mobile_no": "9876543210",
        "password": "secret123",
        "role": "player",
    }
    body.update(over)
    return body


def _register(**over):
    return client.post("/api/v1/auth/register", json=_signup(**over))


def _token(identifier="rohit45", password="secret123"):
    r = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _approve(user_id):
    """Grant a pending elevated role by acting as an admin for one call."""
    admin = type("U", (), {})()
    admin.id, admin.role, admin.is_active = "0", "admin", True
    app.dependency_overrides[get_current_active_user] = lambda: admin
    r = client.post(f"/api/v1/admin/role-requests/{user_id}/approve")
    app.dependency_overrides.pop(get_current_active_user, None)
    return r


# ----- register -------------------------------------------------------------
def test_register_returns_user_with_codes_and_no_password():
    r = _register()
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "rohit45"
    # Sign-up always creates a general user. Saying "player" on the form is a
    # request for an admin to grant, not a role you award yourself.
    assert data["role"] == "general_user"
    assert data["user_code"].startswith("CN")
    assert data["is_active"] is True and data["is_verified"] is False
    assert "password" not in data


def test_register_lowercases_username():
    assert _register(username="RoHiT45").json()["username"] == "rohit45"


def test_register_rejects_invalid_role():
    assert _register(role="superhero").status_code == 422


def test_register_duplicate_username_and_mobile():
    _register()
    assert _register(mobile_no="9000000000").status_code == 409          # username taken
    assert _register(username="another").status_code == 409              # mobile taken


# ----- login ----------------------------------------------------------------
def test_login_by_username_and_by_mobile():
    _register()
    assert client.post("/api/v1/auth/login", json={"identifier": "rohit45", "password": "secret123"}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"identifier": "9876543210", "password": "secret123"}).status_code == 200


def test_register_and_login_accept_a_plus_prefixed_mobile():
    """A '+91 …' style number is accepted (normalised to digits) instead of being
    rejected, and login matches whether or not the '+' / spaces are included."""
    r = _register(username="dabbi07", mobile_no="+91 95922-42452")
    assert r.status_code == 201, r.text
    assert client.post("/api/v1/auth/login", json={"identifier": "919592242452", "password": "secret123"}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"identifier": "+919592242452", "password": "secret123"}).status_code == 200


def test_login_wrong_password_and_unknown_user_both_401():
    _register()
    assert client.post("/api/v1/auth/login", json={"identifier": "rohit45", "password": "wrongpass"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"identifier": "ghost99", "password": "secret123"}).status_code == 401


# ----- me / protected -------------------------------------------------------
def test_me_requires_a_token():
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers=_auth("not-a-real-token")).status_code == 401


def test_me_returns_the_logged_in_user():
    _register()
    me = client.get("/api/v1/auth/me", headers=_auth(_token()))
    assert me.status_code == 200
    assert me.json()["username"] == "rohit45"


# ----- refresh tokens -------------------------------------------------------
def _login(identifier="rohit45", password="secret123"):
    return client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password}).json()


def test_login_returns_refresh_token_and_rotates():
    _register()
    tokens = _login()
    assert tokens["access_token"] and tokens["refresh_token"]
    rt = tokens["refresh_token"]

    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert r2.status_code == 200
    new_rt = r2.json()["refresh_token"]
    assert new_rt and new_rt != rt                 # rotated

    # the old refresh token is now spent; the new one still works
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rt}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": new_rt}).status_code == 200


def test_logout_revokes_refresh_token():
    _register()
    rt = _login()["refresh_token"]
    assert client.post("/api/v1/auth/logout", json={"refresh_token": rt}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rt}).status_code == 401


def test_refresh_with_bad_token_rejected():
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-valid-token"}).status_code == 401


# ----- profile --------------------------------------------------------------
def _profile_body(**over):
    body = {
        "address": "12 MG Road", "pincode": "560001", "city": "Bengaluru",
        "district": "Bengaluru Urban", "state": "Karnataka", "region": "South",
    }
    body.update(over)
    return body


def test_profile_complete_get_update_flow():
    _register()
    tok = _token()
    # not completed yet
    assert client.get("/api/v1/auth/profile", headers=_auth(tok)).status_code == 404
    # complete
    r = client.post("/api/v1/auth/profile", json=_profile_body(), headers=_auth(tok))
    assert r.status_code == 201 and r.json()["city"] == "Bengaluru"
    # cannot complete twice
    assert client.post("/api/v1/auth/profile", json=_profile_body(), headers=_auth(tok)).status_code == 409
    # get
    assert client.get("/api/v1/auth/profile", headers=_auth(tok)).json()["state"] == "Karnataka"
    # update
    up = client.patch("/api/v1/auth/profile", json=_profile_body(city="Mysuru"), headers=_auth(tok))
    assert up.status_code == 200 and up.json()["city"] == "Mysuru"


def test_profile_pincode_must_be_digits():
    _register()
    bad = client.post("/api/v1/auth/profile", json=_profile_body(pincode="abc123"), headers=_auth(_token()))
    assert bad.status_code == 422


# ----- network directory ----------------------------------------------------
def test_directory_lists_members_by_role():
    _register()  # rohit45
    client.post("/api/v1/auth/register", json=_signup(full_name="Sunil Umpire", username="ump1", mobile_no="9000000001", role="umpire"))
    client.post("/api/v1/auth/register", json=_signup(full_name="Ravi Commentary", username="comm1", mobile_no="9000000002", role="commentator"))
    tok = _token()  # log in as rohit45

    assert client.get("/api/v1/users").status_code == 401  # directory is members-only

    everyone = client.get("/api/v1/users", headers=_auth(tok)).json()
    assert len(everyone) == 3
    assert all("password" not in u for u in everyone)   # never leak the hash
    # Nobody holds an elevated role until an admin grants one, whatever they
    # asked for on the form.
    assert {u["role"] for u in everyone} == {"general_user"}

    assert client.get("/api/v1/users?role=player", headers=_auth(tok)).json() == []


def test_member_records_track_scoring_and_commentating():
    # an organizer is created pending; an admin approves the role, then they score
    org = client.post("/api/v1/auth/register", json=_signup(full_name="Org One", username="org1", mobile_no="9000000010", role="organizer")).json()
    assert _approve(org["id"]).status_code == 200
    org_tok = _token("org1")
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "format_id": "t20", "bat_first": "a"},
        headers=_auth(org_tok),
    ).json()["id"]

    # Marking that you commentated feeds the public record organizers pick
    # officials from, so it takes the commentator role — not merely an account.
    comm = client.post("/api/v1/auth/register", json=_signup(full_name="Comm Two", username="comm2", mobile_no="9000000012", role="commentator")).json()
    comm_tok = _token("comm2")
    assert client.post(f"/api/v1/matches/{mid}/commentate", headers=_auth(comm_tok)).status_code == 403

    assert _approve(comm["id"]).status_code == 200
    comm_tok = _token("comm2")
    assert client.post(f"/api/v1/matches/{mid}/commentate", headers=_auth(comm_tok)).status_code == 204

    by_name = {u["username"]: u for u in client.get("/api/v1/users", headers=_auth(org_tok)).json()}
    assert by_name["org1"]["records"]["matches_scored"] == 1
    assert by_name["comm2"]["records"]["matches_commentated"] == 1
    assert client.get("/api/v1/auth/me", headers=_auth(org_tok)).json()["records"]["matches_scored"] == 1


def test_search_includes_members_only_when_signed_in():
    _register()  # rohit45
    tok = _token()
    # anonymous search omits members…
    assert client.get("/api/v1/search?q=rohit").json()["members"] == []
    # …signed in, members show up
    members = client.get("/api/v1/search?q=rohit", headers=_auth(tok)).json()["members"]
    assert any(u["username"] == "rohit45" for u in members)
