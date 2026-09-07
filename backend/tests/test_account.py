"""Account verification (mobile OTP) + password reset flows."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_user, get_current_user
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _real_auth(_in_memory_services):
    # use the real current-user dependency so tokens/identity behave normally
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_user, None)
    yield


def _register(username="vera", mobile="9876500000", password="secret123"):
    return client.post("/api/v1/auth/register", json={
        "full_name": "Vera Verify", "username": username, "mobile_no": mobile,
        "password": password, "role": "player",
    }).json()


def _token(identifier="vera", password="secret123"):
    return client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password}).json()["access_token"]


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


# ----- verification ---------------------------------------------------------
def test_verify_flow_sets_is_verified():
    _register()
    tok = _token()
    assert client.get("/api/v1/auth/me", headers=_auth(tok)).json()["is_verified"] is False

    req = client.post("/api/v1/auth/verify/request", headers=_auth(tok))
    assert req.status_code == 200 and req.json()["sent"] is True
    code = req.json()["dev_code"]  # dev delivery returns the code

    ok = client.post("/api/v1/auth/verify/confirm", json={"code": code}, headers=_auth(tok))
    assert ok.status_code == 200 and ok.json()["verified"] is True
    assert client.get("/api/v1/auth/me", headers=_auth(tok)).json()["is_verified"] is True


def test_verify_wrong_code_rejected():
    _register(username="wrongc", mobile="9876500001")
    tok = _token("wrongc")
    client.post("/api/v1/auth/verify/request", headers=_auth(tok))
    assert client.post("/api/v1/auth/verify/confirm", json={"code": "000000"}, headers=_auth(tok)).status_code == 400


def test_verify_requires_auth():
    assert client.post("/api/v1/auth/verify/request").status_code == 401


# ----- account email (so existing users can add one) ------------------------
def test_update_email_normalizes_and_shows_on_me():
    _register(username="emu", mobile="9876500009")
    tok = _token("emu")
    r = client.patch("/api/v1/auth/email", json={"email": "Emu@Example.com"}, headers=_auth(tok))
    assert r.status_code == 200 and r.json()["email"] == "emu@example.com"  # lower-cased
    assert client.get("/api/v1/auth/me", headers=_auth(tok)).json()["email"] == "emu@example.com"


def test_update_email_rejects_garbage():
    _register(username="emu2", mobile="9876500010")
    tok = _token("emu2")
    assert client.patch("/api/v1/auth/email", json={"email": "not-an-email"}, headers=_auth(tok)).status_code == 422


def test_update_email_requires_auth():
    assert client.patch("/api/v1/auth/email", json={"email": "x@y.com"}).status_code == 401


# ----- password reset -------------------------------------------------------
def test_forgot_then_reset_changes_password():
    _register(username="reset1", mobile="9876500002", password="oldpass1")
    forgot = client.post("/api/v1/auth/password/forgot", json={"identifier": "reset1"})
    assert forgot.status_code == 200 and forgot.json()["sent"] is True
    token = forgot.json()["dev_token"]

    assert client.post("/api/v1/auth/password/reset", json={"token": token, "new_password": "newpass1"}).json()["ok"] is True
    # old password no longer works, new one does
    assert client.post("/api/v1/auth/login", json={"identifier": "reset1", "password": "oldpass1"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"identifier": "reset1", "password": "newpass1"}).status_code == 200


def test_forgot_by_email_finds_the_account():
    """You can request a reset with your email address (not just username/mobile),
    which is the path that actually delivers when only SMTP is configured."""
    _register(username="byemail", mobile="9876500077", password="oldpass1")
    tok = _token("byemail", "oldpass1")
    client.patch("/api/v1/auth/email", json={"email": "ByEmail@Example.com"}, headers=_auth(tok))

    forgot = client.post("/api/v1/auth/password/forgot", json={"identifier": "byemail@example.com"})
    assert forgot.status_code == 200 and forgot.json()["sent"] is True
    token = forgot.json()["dev_token"]
    assert token, "reset by email should find the account and issue a token"
    assert client.post("/api/v1/auth/password/reset", json={"token": token, "new_password": "fresh123"}).json()["ok"] is True
    assert client.post("/api/v1/auth/login", json={"identifier": "byemail", "password": "fresh123"}).status_code == 200


def test_forgot_unknown_user_is_generic_no_token():
    r = client.post("/api/v1/auth/password/forgot", json={"identifier": "nobody"})
    assert r.status_code == 200 and r.json()["sent"] is True
    assert "dev_token" not in r.json()  # nothing leaked for a non-existent account


def test_reset_with_bad_token_rejected():
    assert client.post("/api/v1/auth/password/reset", json={"token": "not-a-real-token", "new_password": "whatever1"}).status_code == 400
