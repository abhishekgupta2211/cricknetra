"""Elevated-role approval workflow — sign-up pending + admin approve/reject.

Core logic is tested at the service level (hermetic); the admin endpoints get a
smoke test (conftest runs as the default admin).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_user, get_current_user
from app.main import app
from app.repositories.role_request_repository import InMemoryRoleRequestRepository
from app.repositories.user_repository import InMemoryUserRepository
from app.schemas.auth import UserSignup
from app.services.auth_service import AuthError, AuthService
from app.services.role_service import RoleError, RoleService

client = TestClient(app)


def _wire():
    users = InMemoryUserRepository()
    reqs = InMemoryRoleRequestRepository()
    return AuthService(users, reqs), RoleService(users, reqs), users


def _signup(role, username="newbie"):
    return UserSignup(full_name="New Bie", username=username, mobile_no="9123456780", password="secret1", role=role)


# ----- sign-up gating -------------------------------------------------------
def test_every_signup_starts_as_a_general_user():
    """A role is granted by an admin after looking at the person, never chosen
    by a stranger at sign-up — otherwise anybody could register as an organizer
    and start running competitions."""
    auth, roles, _ = _wire()
    u = auth.register(_signup("player"))
    assert u.role == "general_user"
    # What they said they were is kept as a request for an admin to act on.
    assert roles.status_for(u.id) == (True, "player")


def test_general_user_code_prefix():
    auth, _roles, _ = _wire()
    u = auth.register(_signup("general_user"))
    assert u.role == "general_user" and u.role_code.startswith("GEN")


def test_elevated_role_is_pending_as_general_user():
    auth, roles, _ = _wire()
    u = auth.register(_signup("umpire"))
    assert u.role == "general_user"          # no powers until approved
    assert roles.status_for(u.id) == (True, "umpire")


def test_admin_cannot_be_obtained_at_signup():
    """There is no path from the sign-up form to an admin account: the field is
    only a request, and admin is never one of the roles it can ask for."""
    auth, roles, users = _wire()
    u = auth.register(_signup("admin"))
    assert users.get_by_id(u.id).role == "general_user"
    assert roles.status_for(u.id) == (False, None), "admin is not requestable"



def test_approve_promotes_and_assigns_role_code():
    auth, roles, users = _wire()
    u = auth.register(_signup("umpire"))
    res = roles.approve(u.id)
    assert res["role"] == "umpire" and res["role_code"].startswith("UMP")
    assert users.get_by_id(u.id).role == "umpire"
    assert roles.status_for(u.id) == (False, None)   # no longer pending


def test_reject_keeps_them_general_user():
    auth, roles, users = _wire()
    u = auth.register(_signup("organizer"))
    roles.reject(u.id)
    assert users.get_by_id(u.id).role == "general_user"
    assert roles.status_for(u.id)[0] is False


def test_approve_without_a_request_errors():
    auth, roles, _ = _wire()
    u = auth.register(_signup(None))             # asked for nothing
    with pytest.raises(RoleError):
        roles.approve(u.id)


def test_list_pending_includes_user_details():
    auth, roles, _ = _wire()
    auth.register(_signup("organizer", username="orgwait"))
    pending = roles.list_pending()
    assert len(pending) == 1
    assert pending[0]["username"] == "orgwait" and pending[0]["requested_role"] == "organizer"


# ----- admin API ------------------------------------------------------------
def test_admin_role_requests_list_ok_as_admin():
    assert client.get("/api/v1/admin/role-requests").status_code == 200  # conftest = admin


def test_role_requests_are_admin_only():
    user = type("U", (), {})()
    user.id, user.role, user.is_active = "5", "organizer", True
    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        assert client.get("/api/v1/admin/role-requests").status_code == 403
        assert client.post("/api/v1/admin/role-requests/9/approve").status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(get_current_user, None)


# ----- make_admin bootstrap script ------------------------------------------
def test_make_admin_promotes_existing_user():
    from scripts.make_admin import promote

    users = InMemoryUserRepository()
    u = users.add_user("Ann Admin", "annx", "9000000001", "x", "organizer")
    ok, msg = promote(users, "annx")
    assert ok is True
    promoted = users.get_by_id(u.id)
    assert promoted.role == "admin" and promoted.role_code.startswith("ADM")


def test_make_admin_promote_unknown_user_fails():
    from scripts.make_admin import promote

    ok, _ = promote(InMemoryUserRepository(), "ghost")
    assert ok is False


def test_make_admin_creates_new_admin():
    from scripts.make_admin import create

    users = InMemoryUserRepository()
    ok, msg = create(users, "Boss Man", "boss", "9000000002", "secret123")
    assert ok is True
    made = users.get_by_username("boss")
    assert made is not None and made.role == "admin"
    # duplicate username is refused
    ok2, _ = create(users, "Boss Two", "boss", "9000000003", "secret123")
    assert ok2 is False
