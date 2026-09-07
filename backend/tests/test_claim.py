"""Claim a roster player — the unverified-stub → user-account model."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.roster_repository import InMemoryRosterRepository
from app.services.roster_service import RosterError, RosterService

client = TestClient(app)


def _svc_with_player(phone="9111100000"):
    repo = InMemoryRosterRepository()
    player = repo.add_player("Rohit", phone, None, None)
    return RosterService(repo), player


# --------------------------------------------------------------------------- #
# service logic
# --------------------------------------------------------------------------- #
def test_claimable_matches_mobile_only():
    svc, p = _svc_with_player("9111100000")
    assert [d.id for d in svc.claimable("9111100000")] == [p.id]
    assert svc.claimable("9999999999") == []
    assert svc.claimable(None) == []


def test_claim_links_and_is_idempotent():
    svc, p = _svc_with_player("9111100000")
    dto = svc.claim(p.id, user_id="u1", mobile="9111100000", is_verified=True, is_admin=False)
    assert dto.claimed_by == "u1"
    assert [d.id for d in svc.my_players("u1")] == [p.id]
    assert svc.claimable("9111100000") == []  # claimed → no longer claimable
    # re-claiming by the same user is a no-op, not an error
    assert svc.claim(p.id, user_id="u1", mobile="9111100000", is_verified=True, is_admin=False).claimed_by == "u1"


def test_claim_requires_verified_account():
    svc, p = _svc_with_player()
    with pytest.raises(RosterError):
        svc.claim(p.id, user_id="u1", mobile=p.phone, is_verified=False, is_admin=False)


def test_phone_must_match_unless_admin():
    svc, p = _svc_with_player("9111100000")
    with pytest.raises(RosterError):  # different mobile, not admin
        svc.claim(p.id, user_id="u2", mobile="9000000000", is_verified=True, is_admin=False)
    dto = svc.claim(p.id, user_id="adm", mobile="9000000000", is_verified=True, is_admin=True)
    assert dto.claimed_by == "adm"  # admin overrides the phone check


def test_cannot_steal_a_claimed_player():
    svc, p = _svc_with_player("9111100000")
    svc.claim(p.id, user_id="u1", mobile="9111100000", is_verified=True, is_admin=False)
    with pytest.raises(RosterError):
        svc.claim(p.id, user_id="u2", mobile="9111100000", is_verified=True, is_admin=False)


# --------------------------------------------------------------------------- #
# API wiring (conftest default user = admin, id "0", mobile "0000000000", verified)
# --------------------------------------------------------------------------- #
def test_api_claim_flow():
    pid = client.post("/api/v1/players", json={"name": "Admin Stub", "phone": "0000000000"}).json()["id"]

    assert any(p["id"] == pid for p in client.get("/api/v1/players/claimable").json())

    claimed = client.post(f"/api/v1/players/{pid}/claim")
    assert claimed.status_code == 200 and claimed.json()["claimed_by"] == "0"

    assert any(p["id"] == pid for p in client.get("/api/v1/players/mine").json())
    assert not any(p["id"] == pid for p in client.get("/api/v1/players/claimable").json())
