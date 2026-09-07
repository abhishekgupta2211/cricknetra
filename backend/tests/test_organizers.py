"""Admin-side organizer management: areas, organizations, organizers, roles, audit.

conftest runs every test as a default admin; where a test needs somebody else it
overrides the current user the way test_permissions does.

The org + audit repositories are process-wide singletons in ``deps`` that
conftest does not reset, so this module gives each test its own — otherwise the
areas one test creates turn up in the next one's listing.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_audit_repo,
    get_current_active_user,
    get_current_user,
    get_org_repo,
    get_ownership_repo,
    get_user_repo,
)
from app.main import app
from app.repositories.audit_repository import AuditActions, InMemoryAuditRepository
from app.repositories.org_repository import InMemoryOrgRepository

client = TestClient(app)

API = "/api/v1/admin"


@pytest.fixture(autouse=True)
def _fresh_admin_stores():
    orgs = InMemoryOrgRepository()
    audit = InMemoryAuditRepository()
    app.dependency_overrides[get_org_repo] = lambda: orgs
    app.dependency_overrides[get_audit_repo] = lambda: audit
    yield
    # conftest clears the whole override map after us; nothing else to undo.


def _users():
    """The in-memory user repo conftest built for this test."""
    return app.dependency_overrides[get_user_repo]()


def _owners():
    return app.dependency_overrides[get_ownership_repo]()


def _add_user(name: str, role: str = "general_user", mobile: str = "9000000001"):
    return _users().add_user(
        full_name=name, username=name.lower().replace(" ", ""), mobile_no=mobile,
        password_hash="x", role=role,
    )


def _as(role: str, uid: str = "9"):
    """Run the following requests as this role (see tests/test_permissions.py)."""
    now = datetime.now(timezone.utc)
    user = type("U", (), {})()
    user.id, user.role, user.is_active = uid, role, True
    user.full_name = user.username = user.mobile_no = "x"
    user.user_code = user.role_code = user.password = "x"
    user.is_verified = True
    user.created_at = user.updated_at = now
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return user


def _area(name: str = "Prayagraj", state: str = "UP") -> str:
    r = client.post(f"{API}/areas", json={"name": name, "state": state})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _organization(name: str = "XYZ Sports", area_id: str | None = None) -> str:
    r = client.post(f"{API}/organizations", json={"name": name, "area_id": area_id})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ----- areas + organizations ------------------------------------------------
def test_create_and_list_areas_and_organizations():
    area_id = _area()
    org_id = _organization("XYZ Sports", area_id)

    areas = client.get(f"{API}/areas").json()
    assert [a["name"] for a in areas] == ["Prayagraj"]
    assert areas[0]["state"] == "UP"
    assert areas[0]["organizers"] == 0 and areas[0]["tournaments"] == 0

    orgs = client.get(f"{API}/organizations").json()
    assert len(orgs) == 1
    assert orgs[0]["id"] == org_id
    assert orgs[0]["area_id"] == area_id
    assert orgs[0]["area_name"] == "Prayagraj"  # resolved, not just the id

    # the ?area_id= filter
    other = _area("Lucknow", "UP")
    assert client.get(f"{API}/organizations", params={"area_id": other}).json() == []
    assert len(client.get(f"{API}/organizations", params={"area_id": area_id}).json()) == 1

    assert client.delete(f"{API}/organizations/{org_id}").status_code == 204
    assert client.get(f"{API}/organizations").json() == []
    assert client.delete(f"{API}/areas/{area_id}").status_code == 204
    assert [a["id"] for a in client.get(f"{API}/areas").json()] == [other]
    assert client.delete(f"{API}/areas/{area_id}").status_code == 404  # already gone


def test_area_name_is_not_duplicated():
    _area("Prayagraj")
    assert client.post(f"{API}/areas", json={"name": "prayagraj"}).status_code == 409


# ----- promoting an existing account ----------------------------------------
def test_promote_existing_user_to_organizer():
    area_id = _area()
    org_id = _organization("XYZ Sports", area_id)
    user = _add_user("Ravi Kumar")
    assert user.role == "general_user"

    r = client.post(
        f"{API}/organizers",
        json={"user_id": user.id, "area_id": area_id, "organization_id": org_id},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user_id"] == user.id
    assert body["role"] == "organizer"
    assert body["full_name"] == "Ravi Kumar"
    assert body["area_id"] == area_id and body["area_name"] == "Prayagraj"
    assert body["organization_id"] == org_id and body["organization_name"] == "XYZ Sports"
    assert body["tournaments"] == 0

    # the account itself was promoted, not just the profile
    assert _users().get_by_id(user.id).role == "organizer"

    listed = client.get(f"{API}/organizers").json()
    assert [o["user_id"] for o in listed] == [user.id]
    assert [o["user_id"] for o in client.get(
        f"{API}/organizers", params={"area_id": area_id}).json()] == [user.id]
    assert client.get(f"{API}/organizers", params={"area_id": "999"}).json() == []

    # the area's rollup now sees them
    area = client.get(f"{API}/areas").json()[0]
    assert area["organizers"] == 1


def test_promoting_an_unknown_user_is_404_and_creates_nothing():
    before = len(_users().list_users())
    r = client.post(f"{API}/organizers", json={"user_id": "424242"})
    assert r.status_code == 404
    assert "exist" in r.json()["detail"].lower()
    assert len(_users().list_users()) == before
    assert client.get(f"{API}/organizers").json() == []


def test_organizer_tournament_count_comes_from_ownership():
    user = _add_user("Owner Om")
    assert client.post(f"{API}/organizers", json={"user_id": user.id}).status_code == 201
    _owners().set_owner("tournament", "31", user.id)
    _owners().set_owner("tournament", "32", user.id)
    assert client.get(f"{API}/organizers").json()[0]["tournaments"] == 2


def test_patch_organizer_moves_them_without_demoting():
    first, second = _area("Prayagraj"), _area("Varanasi")
    user = _add_user("Mover Meena")
    client.post(f"{API}/organizers", json={"user_id": user.id, "area_id": first})

    r = client.patch(f"{API}/organizers/{user.id}", json={"area_id": second})
    assert r.status_code == 200
    assert r.json()["area_name"] == "Varanasi"
    assert r.json()["is_active"] is True
    assert _users().get_by_id(user.id).role == "organizer"  # a move is not a demotion

    # suspending leaves the role alone — that is what makes it different to DELETE
    r = client.patch(f"{API}/organizers/{user.id}", json={"is_active": False})
    assert r.json()["is_active"] is False
    assert _users().get_by_id(user.id).role == "organizer"
    # ...and a later move must not quietly un-suspend them
    r = client.patch(f"{API}/organizers/{user.id}", json={"area_id": first})
    assert r.json()["is_active"] is False

    assert client.patch(f"{API}/organizers/999", json={"is_active": True}).status_code == 404


# ----- deactivation keeps the competitions ----------------------------------
def test_deactivating_an_organizer_demotes_but_keeps_their_tournaments():
    area_id = _area()
    user = _add_user("Leaving Lata")
    client.post(f"{API}/organizers", json={"user_id": user.id, "area_id": area_id})
    _owners().set_owner("tournament", "77", user.id)
    _owners().set_owner("tournament", "78", user.id)

    assert client.delete(f"{API}/organizers/{user.id}").status_code == 204

    assert _users().get_by_id(user.id).role == "general_user"
    profile = client.get(f"{API}/organizers").json()[0]
    assert profile["user_id"] == user.id and profile["is_active"] is False
    # The competitions are untouched: an admin reassigns or deletes them on purpose.
    assert _owners().get_owner("tournament", "77") == user.id
    assert _owners().get_owner("tournament", "78") == user.id
    assert sorted(_owners().list_by_owner(user.id, "tournament")) == ["77", "78"]
    # a deactivated organizer no longer counts towards their area
    assert client.get(f"{API}/areas").json()[0]["organizers"] == 0

    assert client.delete(f"{API}/organizers/999").status_code == 404


# ----- role assignment ------------------------------------------------------
def test_assign_role_changes_the_role():
    user = _add_user("Promoted Priya")
    r = client.put(f"{API}/users/{user.id}/role", json={"role": "umpire"})
    assert r.status_code == 200
    assert r.json()["role"] == "umpire"
    assert r.json()["role_code"].startswith("UMP")
    assert _users().get_by_id(user.id).role == "umpire"


def test_assign_role_rejects_an_unknown_role():
    user = _add_user("Curious Kabir")
    r = client.put(f"{API}/users/{user.id}/role", json={"role": "wizard"})
    assert r.status_code == 400
    assert "wizard" in r.json()["detail"]
    assert _users().get_by_id(user.id).role == "general_user"
    assert client.put(f"{API}/users/999/role", json={"role": "player"}).status_code == 404


def test_the_last_admin_cannot_be_demoted():
    only_admin = _add_user("Solo Admin", role="admin")
    r = client.put(f"{API}/users/{only_admin.id}/role", json={"role": "player"})
    assert r.status_code == 409
    assert "last admin" in r.json()["detail"].lower()
    assert _users().get_by_id(only_admin.id).role == "admin"

    # with a second admin in place the demotion goes through
    second = _add_user("Backup Admin", role="admin", mobile="9000000002")
    assert client.put(f"{API}/users/{only_admin.id}/role", json={"role": "player"}).status_code == 200
    assert _users().get_by_id(only_admin.id).role == "player"
    # ...and now the survivor is the last one
    assert client.put(f"{API}/users/{second.id}/role", json={"role": "player"}).status_code == 409


def test_the_last_admin_cannot_be_demoted_by_appointing_them_an_organizer():
    """The organizer endpoint rewrites a role too, so it needs the same guard —
    otherwise 'promote the last admin' is a way around it."""
    only_admin = _add_user("Solo Admin", role="admin")
    r = client.post(f"{API}/organizers", json={"user_id": only_admin.id})
    assert r.status_code == 409
    assert _users().get_by_id(only_admin.id).role == "admin"
    assert client.get(f"{API}/organizers").json() == []  # no profile written either


# ----- audit trail ----------------------------------------------------------
def test_audit_records_role_changes_and_organizer_creation():
    admin = _add_user("Audit Admin", role="admin")
    _as("admin", uid=admin.id)
    user = _add_user("Watched Wasim", mobile="9000000003")

    assert client.post(f"{API}/organizers", json={"user_id": user.id}).status_code == 201
    assert client.put(f"{API}/users/{user.id}/role", json={"role": "player"}).status_code == 200

    rows = client.get(f"{API}/audit").json()
    assert [r["action"] for r in rows] == [
        AuditActions.ROLE_ASSIGNED, AuditActions.ORGANIZER_CREATED,
    ]  # newest first
    assert all(r["actor_id"] == admin.id for r in rows)
    assert all(r["actor_name"] == "Audit Admin" for r in rows)  # resolved from the user repo
    assert rows[0]["resource_type"] == "user" and rows[0]["resource_id"] == user.id
    assert "organizer -> player" in rows[0]["detail"]

    # filters
    assert len(client.get(f"{API}/audit", params={"action": AuditActions.ROLE_ASSIGNED}).json()) == 1
    assert client.get(f"{API}/audit", params={"actor_id": "nobody"}).json() == []
    assert len(client.get(f"{API}/audit", params={"limit": 1}).json()) == 1


def test_audit_records_a_deactivation():
    user = _add_user("Ousted Om")
    client.post(f"{API}/organizers", json={"user_id": user.id})
    client.delete(f"{API}/organizers/{user.id}")
    actions = [r["action"] for r in client.get(f"{API}/audit").json()]
    assert AuditActions.ORGANIZER_DEACTIVATED in actions


def test_a_failing_audit_store_does_not_fail_the_action():
    """The trail is a record of what happened, never a gate on it happening."""

    class _Broken(InMemoryAuditRepository):
        def add(self, *a, **kw):
            raise RuntimeError("audit store is down")

    app.dependency_overrides[get_audit_repo] = lambda: _Broken()
    user = _add_user("Resilient Riya")
    assert client.post(f"{API}/organizers", json={"user_id": user.id}).status_code == 201
    assert _users().get_by_id(user.id).role == "organizer"


# ----- everything here is admin-only ----------------------------------------
_ADMIN_ONLY = [
    ("get", "/areas", None),
    ("post", "/areas", {"name": "Sneaky"}),
    ("delete", "/areas/1", None),
    ("get", "/organizations", None),
    ("post", "/organizations", {"name": "Sneaky FC"}),
    ("delete", "/organizations/1", None),
    ("get", "/organizers", None),
    ("post", "/organizers", {"user_id": "1"}),
    ("patch", "/organizers/1", {"is_active": False}),
    ("delete", "/organizers/1", None),
    ("put", "/users/1/role", {"role": "admin"}),
    ("get", "/audit", None),
]


@pytest.mark.parametrize("role", ["organizer", "player", "general_user", "umpire", "team_owner"])
def test_non_admins_are_refused_everywhere(role):
    victim = _add_user("Target Tara")
    _as(role, uid="9")
    for method, path, body in _ADMIN_ONLY:
        r = getattr(client, method)(f"{API}{path}", **({"json": body} if body else {}))
        assert r.status_code == 403, f"{method.upper()} {path} as {role} -> {r.status_code}"
    # nothing leaked through: the target account is untouched
    assert _users().get_by_id(victim.id).role == "general_user"


def test_an_organizer_cannot_promote_themselves():
    """The body says who to act on; it never says who is asking."""
    user = _add_user("Ambitious Anil")
    _as("organizer", uid=user.id)
    assert client.put(f"{API}/users/{user.id}/role", json={"role": "admin"}).status_code == 403
    assert _users().get_by_id(user.id).role == "general_user"
