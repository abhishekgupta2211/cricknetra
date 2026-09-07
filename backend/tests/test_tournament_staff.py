"""Organizer-scoped tournament staff, and per-tournament player participation.

The point of every test here is the same one sentence: an organizer runs their
own competition and nobody else's. Two organizers hold identical capabilities,
so the only thing standing between Organizer B and Organizer A's umpires is the
ownership lookup — which means changing the id in the URL is the attack these
tests are written to keep failing.

conftest runs as a default admin; ``_as`` swaps the authenticated caller the
way tests/test_permissions.py does. The staff repository is a module-level
singleton in deps, so it is overridden here too — otherwise one test's staff
would show up in the next one's list.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_current_active_user,
    get_current_user,
    get_staff_repo,
    get_user_repo,
)
from app.main import app
from app.repositories.tournament_staff_repository import InMemoryTournamentStaffRepository
from app.repositories.user_repository import UserRecord

client = TestClient(app)

API = "/api/v1"


# --------------------------------------------------------------------------- #
# Fixtures & helpers
# --------------------------------------------------------------------------- #
@pytest.fixture()
def staff_repo() -> InMemoryTournamentStaffRepository:
    """A fresh staff store per test.

    conftest rebuilds every other repository but the staff one lives behind a
    deps singleton, so without this an assignment made in one test would still
    be there in the next — and a "B can't see A's staff" test would pass for
    the wrong reason.
    """
    repo = InMemoryTournamentStaffRepository()
    app.dependency_overrides[get_staff_repo] = lambda: repo
    return repo  # conftest's autouse fixture clears the overrides afterwards


@pytest.fixture()
def users():
    """conftest's user repository — the same instance the routes resolve."""
    return app.dependency_overrides[get_user_repo]()


def _make_user(users, name: str, role: str) -> UserRecord:
    rec = users.add_user(
        full_name=name, username=name.lower().replace(" ", ""), mobile_no=f"9{abs(hash(name)) % 10**9:09d}",
        password_hash="x", role=role,
    )
    return rec


def _as(user: UserRecord) -> UserRecord:
    """Authenticate as this account for the requests that follow."""
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return user


def _team(name: str) -> str:
    return client.post(f"{API}/teams", json={"name": name}).json()["id"]


def _player(name: str) -> str:
    return client.post(f"{API}/players", json={"name": name}).json()["id"]


def _tournament(name: str) -> str:
    """Create a competition as whoever is currently authenticated — the route
    records them as its owner, which is what every scope check reads back."""
    ids = [_team(f"{name} Home"), _team(f"{name} Away")]
    res = client.post(
        f"{API}/tournaments",
        json={"name": name, "format": "round_robin", "format_id": "t20", "team_ids": ids},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


@pytest.fixture()
def world(staff_repo, users):
    """Organizer A with Tournament A, Organizer B with Tournament B, and a few
    roleless accounts to staff them with."""

    class World:
        pass

    w = World()
    w.admin = _make_user(users, "Site Admin", "admin")
    w.a = _make_user(users, "Organizer A", "organizer")
    w.b = _make_user(users, "Organizer B", "organizer")
    w.ump = _make_user(users, "Uma Umpire", "general_user")
    w.com = _make_user(users, "Colin Commentator", "general_user")
    w.player = _make_user(users, "Pat Player", "player")

    _as(w.a)
    w.tour_a = _tournament("A Cup")
    _as(w.b)
    w.tour_b = _tournament("B League")
    return w


def _add_umpire(tournament_id: str, user_id: str):
    return client.post(f"{API}/tournaments/{tournament_id}/staff/umpires", json={"user_id": user_id})


def _add_commentator(tournament_id: str, user_id: str):
    return client.post(
        f"{API}/tournaments/{tournament_id}/staff/commentators", json={"user_id": user_id}
    )


# --------------------------------------------------------------------------- #
# 1-2. An organizer staffs their own competition
# --------------------------------------------------------------------------- #
def test_two_organizers_each_own_their_own_tournament(world):
    """The setup the rest of the file leans on: ownership was recorded, so each
    organizer reaches their own competition and only that one."""
    _as(world.a)
    assert client.get(f"{API}/tournaments/{world.tour_a}/staff").status_code == 200
    _as(world.b)
    assert client.get(f"{API}/tournaments/{world.tour_b}/staff").status_code == 200


def test_organizer_adds_an_umpire_and_a_commentator_to_their_tournament(world, users):
    _as(world.a)
    ump = _add_umpire(world.tour_a, world.ump.id)
    com = _add_commentator(world.tour_a, world.com.id)
    assert ump.status_code == 201, ump.text
    assert com.status_code == 201, com.text
    assert ump.json()["staff_role"] == "umpire"
    assert ump.json()["full_name"] == "Uma Umpire"

    listed = client.get(f"{API}/tournaments/{world.tour_a}/staff").json()
    assert {(s["user_id"], s["staff_role"]) for s in listed} == {
        (world.ump.id, "umpire"),
        (world.com.id, "commentator"),
    }
    # joining the staff promoted the roleless accounts
    assert users.get_by_id(world.ump.id).role == "umpire"
    assert users.get_by_id(world.com.id).role == "commentator"


def test_staff_list_filters_by_role(world):
    _as(world.a)
    _add_umpire(world.tour_a, world.ump.id)
    _add_commentator(world.tour_a, world.com.id)

    umpires = client.get(f"{API}/tournaments/{world.tour_a}/staff?staff_role=umpire").json()
    assert [s["user_id"] for s in umpires] == [world.ump.id]
    bad = client.get(f"{API}/tournaments/{world.tour_a}/staff?staff_role=coach")
    assert bad.status_code == 400
    assert "staff role" in bad.json()["detail"]


def test_adding_somebody_who_already_holds_a_role_is_refused_not_demoted(world, users):
    """The 409 that keeps this endpoint from being a back door into role
    changes: an organizer must not turn somebody's player account into an
    umpire account by typing their id into the umpire box."""
    _as(world.a)
    clash = _add_umpire(world.tour_a, world.player.id)
    assert clash.status_code == 409
    assert "player" in clash.json()["detail"]
    assert "admin" in clash.json()["detail"].lower()
    assert users.get_by_id(world.player.id).role == "player"  # untouched
    assert client.get(f"{API}/tournaments/{world.tour_a}/staff").json() == []

    # …and the same goes for somebody who already holds the *other* staff role
    _add_commentator(world.tour_a, world.com.id)
    cross = _add_umpire(world.tour_a, world.com.id)
    assert cross.status_code == 409
    assert users.get_by_id(world.com.id).role == "commentator"


def test_adding_an_unknown_account_is_a_404(world):
    _as(world.a)
    missing = _add_umpire(world.tour_a, "999999")
    assert missing.status_code == 404
    assert "account" in missing.json()["detail"].lower()


# --------------------------------------------------------------------------- #
# 3-4. The other organizer, and the IDOR
# --------------------------------------------------------------------------- #
def test_other_organizer_cannot_add_staff_to_your_tournament(world):
    _as(world.b)
    assert _add_umpire(world.tour_a, world.ump.id).status_code == 403
    assert _add_commentator(world.tour_a, world.com.id).status_code == 403


def test_other_organizer_cannot_list_your_staff(world):
    _as(world.a)
    _add_umpire(world.tour_a, world.ump.id)
    _as(world.b)
    denied = client.get(f"{API}/tournaments/{world.tour_a}/staff")
    assert denied.status_code == 403
    assert "tournament" in denied.json()["detail"].lower()


def test_other_organizer_cannot_remove_or_deactivate_your_staff(world, staff_repo):
    _as(world.a)
    _add_umpire(world.tour_a, world.ump.id)

    _as(world.b)
    assert client.delete(
        f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}"
    ).status_code == 403
    assert client.patch(
        f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}",
        json={"is_active": False},
    ).status_code == 403
    # the entry is still there, still active
    rec = staff_repo.get(world.tour_a, world.ump.id, "umpire")
    assert rec is not None and rec.is_active


def test_idor_other_organizer_cannot_reach_your_tournament_by_changing_the_id_in_the_url(world):
    """Organizer B holds every capability Organizer A holds. The only thing
    that stops ``/tournaments/<A's id>/staff`` is the ownership lookup, so this
    is the test that would catch it being dropped."""
    _as(world.a)
    _add_umpire(world.tour_a, world.ump.id)

    _as(world.b)
    # B works their own competition perfectly well…
    assert client.get(f"{API}/tournaments/{world.tour_b}/staff").status_code == 200
    # …and swapping in A's id changes nothing but the 403.
    for res in (
        client.get(f"{API}/tournaments/{world.tour_a}/staff"),
        client.get(f"{API}/tournaments/{world.tour_a}/players"),
        _add_umpire(world.tour_a, world.com.id),
        _add_commentator(world.tour_a, world.com.id),
        client.delete(f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}"),
        client.patch(
            f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}",
            json={"is_active": False},
        ),
    ):
        assert res.status_code == 403, res.text


def test_idor_other_organizer_cannot_register_a_player_into_your_squad(world):
    """The same attack against the squad routes: both organizers hold
    ``tournament.create``, so accepting the capability alone let B write
    players into A's competition with

        POST /api/v1/tournaments/<A's id>/teams/<A's team>/squad
    """
    _as(world.a)
    a_team = client.get(f"{API}/tournaments/{world.tour_a}").json()["teams"][0]["id"]
    pid = _player("Ravi")

    _as(world.b)
    intruder = client.post(
        f"{API}/tournaments/{world.tour_a}/teams/{a_team}/squad", json={"player_id": pid}
    )
    assert intruder.status_code == 403
    assert client.delete(
        f"{API}/tournaments/{world.tour_a}/teams/{a_team}/squad/{pid}"
    ).status_code == 403

    _as(world.a)  # the owner still can
    assert client.post(
        f"{API}/tournaments/{world.tour_a}/teams/{a_team}/squad", json={"player_id": pid}
    ).status_code == 200


# --------------------------------------------------------------------------- #
# 5-6. One entry per tournament
# --------------------------------------------------------------------------- #
def test_staff_added_to_one_tournament_do_not_appear_on_another(world):
    _as(world.a)
    _add_umpire(world.tour_a, world.ump.id)
    _as(world.b)
    assert client.get(f"{API}/tournaments/{world.tour_b}/staff").json() == []


def test_the_same_person_is_staff_on_both_tournaments_through_two_entries(world, staff_repo):
    """Two independent rows, not one shared one — which is what makes removal
    from one competition leave the other alone."""
    _as(world.a)
    assert _add_umpire(world.tour_a, world.ump.id).status_code == 201
    _as(world.b)
    assert _add_umpire(world.tour_b, world.ump.id).status_code == 201

    assert [s["user_id"] for s in client.get(f"{API}/tournaments/{world.tour_b}/staff").json()] == [
        world.ump.id
    ]
    _as(world.a)
    assert [s["user_id"] for s in client.get(f"{API}/tournaments/{world.tour_a}/staff").json()] == [
        world.ump.id
    ]
    assert staff_repo.get(world.tour_a, world.ump.id, "umpire").id != staff_repo.get(
        world.tour_b, world.ump.id, "umpire"
    ).id


def test_removing_staff_touches_only_this_tournament(world, users, staff_repo):
    _as(world.a)
    _add_umpire(world.tour_a, world.ump.id)
    _as(world.b)
    _add_umpire(world.tour_b, world.ump.id)

    _as(world.a)
    assert client.delete(
        f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}"
    ).status_code == 204
    assert client.get(f"{API}/tournaments/{world.tour_a}/staff").json() == []

    # the account keeps its role, and B's competition keeps its umpire
    assert users.get_by_id(world.ump.id).role == "umpire"
    assert users.get_by_id(world.ump.id).is_active is True
    assert staff_repo.get(world.tour_b, world.ump.id, "umpire") is not None
    _as(world.b)
    assert [s["user_id"] for s in client.get(f"{API}/tournaments/{world.tour_b}/staff").json()] == [
        world.ump.id
    ]


def test_removing_somebody_who_is_not_on_the_staff_is_a_404(world):
    _as(world.a)
    gone = client.delete(f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}")
    assert gone.status_code == 404
    bad_role = client.delete(f"{API}/tournaments/{world.tour_a}/staff/coach/{world.ump.id}")
    assert bad_role.status_code == 400


def test_deactivating_staff_applies_to_this_tournament_only(world, staff_repo):
    _as(world.a)
    _add_umpire(world.tour_a, world.ump.id)
    _as(world.b)
    _add_umpire(world.tour_b, world.ump.id)

    _as(world.a)
    off = client.patch(
        f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}", json={"is_active": False}
    )
    assert off.status_code == 200 and off.json()["is_active"] is False
    assert staff_repo.get(world.tour_b, world.ump.id, "umpire").is_active is True

    # a stood-down umpire stops counting as staff on that competition…
    _as(world.ump)
    assert client.get(f"{API}/tournaments/{world.tour_a}/staff").status_code == 403

    # …until the organizer brings them back
    _as(world.a)
    on = client.patch(
        f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}", json={"is_active": True}
    )
    assert on.status_code == 200 and on.json()["is_active"] is True
    _as(world.ump)
    assert client.get(f"{API}/tournaments/{world.tour_a}/staff").status_code == 200


# --------------------------------------------------------------------------- #
# 7-8. What staff may do, and what admin may do
# --------------------------------------------------------------------------- #
def test_assigned_umpire_can_read_the_staff_list_but_not_change_it(world):
    _as(world.a)
    _add_umpire(world.tour_a, world.ump.id)

    _as(world.ump)  # promoted to 'umpire' when they were added
    assert client.get(f"{API}/tournaments/{world.tour_a}/staff").status_code == 200
    assert client.get(f"{API}/tournaments/{world.tour_a}/players").status_code == 200
    assert _add_umpire(world.tour_a, world.com.id).status_code == 403
    assert _add_commentator(world.tour_a, world.com.id).status_code == 403
    assert client.delete(
        f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}"
    ).status_code == 403
    assert client.patch(
        f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}", json={"is_active": False}
    ).status_code == 403
    # and being staff on A says nothing about B
    assert client.get(f"{API}/tournaments/{world.tour_b}/staff").status_code == 403


def test_admin_manages_staff_on_every_tournament(world):
    _as(world.admin)
    assert _add_umpire(world.tour_a, world.ump.id).status_code == 201
    assert _add_commentator(world.tour_b, world.com.id).status_code == 201
    assert len(client.get(f"{API}/tournaments/{world.tour_a}/staff").json()) == 1
    assert len(client.get(f"{API}/tournaments/{world.tour_b}/staff").json()) == 1
    assert client.patch(
        f"{API}/tournaments/{world.tour_b}/staff/commentator/{world.com.id}",
        json={"is_active": False},
    ).status_code == 200
    assert client.delete(
        f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}"
    ).status_code == 204
    assert client.delete(
        f"{API}/tournaments/{world.tour_b}/staff/commentator/{world.com.id}"
    ).status_code == 204


# --------------------------------------------------------------------------- #
# 9. The caller's own dashboard
# --------------------------------------------------------------------------- #
def test_mine_staffing_returns_only_the_callers_own_assignments(world):
    _as(world.a)
    _add_umpire(world.tour_a, world.ump.id)
    _add_commentator(world.tour_a, world.com.id)
    _as(world.b)
    _add_umpire(world.tour_b, world.ump.id)

    _as(world.ump)
    mine = client.get(f"{API}/tournaments/mine/staffing")
    assert mine.status_code == 200
    assert {(r["tournament_id"], r["staff_role"]) for r in mine.json()} == {
        (world.tour_a, "umpire"),
        (world.tour_b, "umpire"),
    }
    assert {r["tournament_name"] for r in mine.json()} == {"A Cup", "B League"}

    _as(world.com)
    theirs = client.get(f"{API}/tournaments/mine/staffing").json()
    assert [(r["tournament_id"], r["staff_role"]) for r in theirs] == [
        (world.tour_a, "commentator")
    ]

    # somebody with no assignments sees nothing — not everybody else's
    _as(world.player)
    assert client.get(f"{API}/tournaments/mine/staffing").json() == []


def test_mine_staffing_drops_assignments_you_were_stood_down_from(world):
    _as(world.a)
    _add_umpire(world.tour_a, world.ump.id)
    client.patch(
        f"{API}/tournaments/{world.tour_a}/staff/umpire/{world.ump.id}", json={"is_active": False}
    )
    _as(world.ump)
    assert client.get(f"{API}/tournaments/mine/staffing").json() == []


# --------------------------------------------------------------------------- #
# Per-tournament player participation
# --------------------------------------------------------------------------- #
def test_tournament_players_lists_everybody_across_the_squads(world):
    _as(world.a)
    teams = client.get(f"{API}/tournaments/{world.tour_a}").json()["teams"]
    home, away = teams[0]["id"], teams[1]["id"]
    names = {"Ishan": home, "Rahul": home, "Yash": away}
    ids = {}
    for name, team in names.items():
        ids[name] = _player(name)
        assert client.post(
            f"{API}/tournaments/{world.tour_a}/teams/{team}/squad", json={"player_id": ids[name]}
        ).status_code == 200

    rows = client.get(f"{API}/tournaments/{world.tour_a}/players")
    assert rows.status_code == 200
    got = {(r["player"]["name"], r["team_id"]) for r in rows.json()}
    assert got == {(n, t) for n, t in names.items()}
    assert all(r["team_name"] for r in rows.json())

    # a player registered in A's competition is not in B's
    _as(world.b)
    assert client.get(f"{API}/tournaments/{world.tour_b}/players").json() == []


def test_the_organizer_desk_lists_only_your_own_competitions(staff_repo, users):
    """An organizer's dashboard is "My Tournaments", not the public board.

    Scoping it on the server matters: the request carries no id for a client
    to swap for somebody else's — the owner is read from the token.
    """
    a = _make_user(users, "Desk A", "organizer")
    b = _make_user(users, "Desk B", "organizer")

    _as(a)
    ta = _tournament("A's Cup")
    _as(b)
    tb = _tournament("B's Cup")

    # The public board shows both — anybody may browse what is being played.
    _as(a)
    everyone = client.get(f"{API}/tournaments").json()
    assert {t["id"] for t in everyone} >= {ta, tb}

    # A's desk shows only A's.
    assert [t["id"] for t in client.get(f"{API}/tournaments/mine").json()] == [ta]

    _as(b)
    assert [t["id"] for t in client.get(f"{API}/tournaments/mine").json()] == [tb]
