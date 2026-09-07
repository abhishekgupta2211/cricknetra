"""The authorization matrix, written as an attack.

Two organizers run competitions in two different cities. Everything below is
one question asked from every angle: *can Organizer A reach anything that
belongs to Organizer B?* The suite builds the scenario the product requires —
an admin who appoints both, a tournament each, staff and players each — and
then, from A's session, fires A's own working requests at B's ids.

Three rules this file holds itself to, because a permission test that breaks
them proves nothing:

* **Every assertion is on a status code.** A denial is an explicit ``403``
  (or ``404`` where a resource is deliberately hidden). ``200`` with an empty
  body is a silent write, and ``500`` is a crash the client cannot act on —
  both are failures here, so the client is built with
  ``raise_server_exceptions=False`` and a 500 shows up as a 500.
* **A test that cannot pass yet is ``xfail``, never softened.** Several
  requirements below are not met by the current routes. The reason string
  names the endpoint and the exact hole, so the suite reads as the spec and
  the xfail list reads as the backlog.
* **Nothing is proved by an empty store.** ``conftest`` gives the routes their
  own in-memory repositories but leaves ``get_tournament_repo``,
  ``get_staff_repo`` and ``get_org_repo`` pointing at the process-wide
  singletons, so ``ScopeService`` would authorize against a *different*
  tournament table than the one the tournament routes write to — and every
  "B was refused" would be vacuous. ``_isolated_authorization_stores`` below
  points them at the same objects, so a 403 here means the guard said no.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import count
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_audit_repo,
    get_award_repo,
    get_commentary_service,
    get_current_active_user,
    get_current_user,
    get_fielding_event_service,
    get_match_official_repo,
    get_match_service,
    get_optional_user,
    get_org_repo,
    get_ownership_repo,
    get_staff_repo,
    get_tournament_repo,
    get_tournament_service,
    get_user_repo,
)
from app.core.permissions import Roles
from app.main import app
from app.repositories.audit_repository import InMemoryAuditRepository
from app.repositories.org_repository import InMemoryOrgRepository
from app.repositories.tournament_staff_repository import (
    COMMENTATOR,
    UMPIRE,
    InMemoryTournamentStaffRepository,
)
from app.repositories.user_repository import UserRecord

# raise_server_exceptions=False so an unhandled exception arrives as a 500
# response we can assert on, instead of blowing up the test with a traceback
# that hides *which* guard crashed.
client = TestClient(app, raise_server_exceptions=False)

_MOBILES = count(9000000001)

API = "/api/v1"


# --------------------------------------------------------------------------- #
# Harness
# --------------------------------------------------------------------------- #
@dataclass
class Stores:
    """The live repositories behind this test's app, so the scenario can be
    seeded where no endpoint exists yet."""

    users: Any
    tournaments: Any
    owners: Any
    orgs: Any
    staff: Any
    audit: Any
    admin: UserRecord


@pytest.fixture(autouse=True)
def _isolated_authorization_stores():
    """Give the authorization guards the same stores the routes write to.

    ``get_scope_service`` takes its repositories through ``Depends`` precisely
    so a test can swap them, but conftest only swaps some of them. Left alone,
    ``ScopeService.tournament_of_match`` reads a module-level singleton that no
    route in this test ever wrote to (and that every *other* test in the
    session has been writing to), so "B cannot score A's match" would pass even
    with the guard deleted. Same for the staff / org / audit registries.
    """
    users = app.dependency_overrides[get_user_repo]()
    owners = app.dependency_overrides[get_ownership_repo]()
    tournaments = app.dependency_overrides[get_tournament_service]().repo
    orgs = InMemoryOrgRepository()
    staff = InMemoryTournamentStaffRepository()
    audit = InMemoryAuditRepository()

    app.dependency_overrides[get_tournament_repo] = lambda: tournaments
    app.dependency_overrides[get_org_repo] = lambda: orgs
    app.dependency_overrides[get_staff_repo] = lambda: staff
    app.dependency_overrides[get_audit_repo] = lambda: audit

    yield Stores(
        users=users, tournaments=tournaments, owners=owners, orgs=orgs,
        staff=staff, audit=audit,
        admin=app.dependency_overrides[get_current_active_user](),
    )
    # conftest clears app.dependency_overrides in its own teardown.


def _as(user: Any) -> Any:
    """Switch the caller. Everything after this runs as ``user``.

    All three current-user dependencies are swapped, ``get_optional_user``
    included: a route that is public but shows more to a signed-in member asks
    for the caller that way, and leaving it unswapped would make every such
    route see an anonymous visitor no matter who the test says it is — which
    would quietly turn "the organizer is told this cup is theirs" into a test
    of what a stranger sees.
    """
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user
    return user


def _anonymous() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_optional_user, None)


def _account(stores: Stores, name: str, username: str, role: str = Roles.GENERAL_USER) -> UserRecord:
    """A registered account. Created straight in the repository because the
    password hash is irrelevant here and argon2 is not; the *role* is always
    granted through the real admin endpoint below."""
    return stores.users.add_user(
        full_name=name, username=username, mobile_no=str(next(_MOBILES)),
        password_hash="not-used", role=role,
    )


def _assign_role(user_id: str, role: str):
    """The admin endpoint that is meant to be the only way a role changes."""
    return client.put(f"{API}/admin/users/{user_id}/role", json={"role": role})


def _appoint_organizer(stores: Stores, user: UserRecord, area_name: str) -> str:
    """Admin appoints ``user`` an organizer for ``area_name``, through the admin
    API. Falls back to seeding the registry if that surface is unavailable, so
    the isolation tests do not all collapse into setup errors when only the
    appointment screen is broken — ``test_admin_appoints_an_organizer_for_an_area``
    is the test that holds that endpoint to account.
    """
    area = client.post(f"{API}/admin/areas", json={"name": area_name, "state": "UP"})
    area_id = area.json()["id"] if area.status_code == 201 else stores.orgs.add_area(area_name, "UP").id
    made = client.post(f"{API}/admin/organizers", json={"user_id": user.id, "area_id": area_id})
    if made.status_code != 201:  # pragma: no cover - only while the route is unbuilt
        _assign_role(user.id, Roles.ORGANIZER)
        stores.orgs.upsert_organizer(user.id, area_id, None, stores.admin.id)
    return area_id


def _team(name: str) -> str:
    res = client.post(f"{API}/teams", json={"name": name})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _player(name: str) -> str:
    res = client.post(f"{API}/players", json={"name": name})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _tournament(name: str, team_ids: list[str]) -> dict:
    res = client.post(
        f"{API}/tournaments",
        json={"name": name, "format": "round_robin", "format_id": "t20", "team_ids": team_ids},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _start(fixture_id: str, squad_a: list[str], squad_b: list[str]):
    return client.post(
        f"{API}/tournaments/fixtures/{fixture_id}/start",
        json={"squad_a_ids": squad_a, "squad_b_ids": squad_b, "bat_first": "a"},
    )


def _staff(tournament_id: str, kind: str, user_id: str):
    """Put somebody on a competition's staff. ``kind`` is the route's plural —
    ``umpires`` or ``commentators``."""
    return client.post(
        f"{API}/tournaments/{tournament_id}/staff/{kind}", json={"user_id": user_id}
    )


def _score(match_id: str, value: int = 1):
    """The canonical scoring write."""
    return client.post(f"{API}/matches/{match_id}/balls", json={"action": "runs", "value": value})


def _denied(res, what: str, allow_404: bool = False) -> None:
    """A refusal must *say* it refused."""
    allowed = (403, 404) if allow_404 else (403,)
    assert res.status_code in allowed, (
        f"{what}: expected {' or '.join(map(str, allowed))}, got "
        f"{res.status_code} — {res.text[:300]}"
    )


# --------------------------------------------------------------------------- #
# The scenario
# --------------------------------------------------------------------------- #
@dataclass
class World:
    stores: Stores
    admin: UserRecord
    a: UserRecord            # Organizer A — Prayagraj
    b: UserRecord            # Organizer B — Lucknow
    umpire_a: UserRecord
    umpire_b: UserRecord
    commentator_a: UserRecord
    commentator_b: UserRecord
    player_user: UserRecord
    general: UserRecord
    t_a: str                 # Tournament A
    t_b: str                 # Tournament B
    teams_a: list[str]
    teams_b: list[str]
    players_a: list[str]
    players_b: list[str]
    fixture_a: str
    fixture_b: str
    open_fixture_a: str      # a second, not-yet-started fixture in A's tournament
    match_a: str             # the live match inside Tournament A
    match_a2: str            # a second live match inside Tournament A
    match_b: str             # the live match inside Tournament B


@pytest.fixture()
def world(_isolated_authorization_stores: Stores) -> World:
    """ADMIN creates ORGANIZER A (Prayagraj) and ORGANIZER B (Lucknow);
    each then builds a competition, a roster and a staff of their own."""
    stores = _isolated_authorization_stores
    admin = _as(stores.admin)

    a = _account(stores, "Anita Rao", "organizer_a")
    b = _account(stores, "Bilal Khan", "organizer_b")
    umpire_a = _account(stores, "Umpire A", "umpire_a")
    umpire_b = _account(stores, "Umpire B", "umpire_b")
    commentator_a = _account(stores, "Commentator A", "commentator_a")
    commentator_b = _account(stores, "Commentator B", "commentator_b")
    player_user = _account(stores, "Player Person", "player_user")
    general = _account(stores, "Nobody Special", "general")

    _appoint_organizer(stores, a, "Prayagraj")
    _appoint_organizer(stores, b, "Lucknow")
    for user, role in (
        (umpire_a, Roles.UMPIRE), (umpire_b, Roles.UMPIRE),
        (commentator_a, Roles.COMMENTATOR), (commentator_b, Roles.COMMENTATOR),
        (player_user, Roles.PLAYER),
    ):
        assert _assign_role(user.id, role).status_code == 200

    # --- A's competition: three teams so one fixture stays unstarted ---------
    _as(a)
    teams_a = [_team("Prayagraj Reds"), _team("Prayagraj Blues"), _team("Prayagraj Greens")]
    players_a = [_player(f"A Player {i}") for i in range(1, 7)]
    detail_a = _tournament("Prayagraj Cup", teams_a)
    t_a = detail_a["id"]
    fixtures_a = detail_a["fixtures"]
    started_a = _start(fixtures_a[0]["id"], players_a[0:2], players_a[2:4])
    assert started_a.status_code == 200, started_a.text
    match_a = started_a.json()["match_id"]
    started_a2 = _start(fixtures_a[1]["id"], players_a[0:2], players_a[4:6])
    assert started_a2.status_code == 200, started_a2.text
    match_a2 = started_a2.json()["match_id"]
    open_fixture_a = fixtures_a[2]["id"]

    # --- B's competition (also three teams, so a fixture stays unstarted for
    #     A to try to hijack) ----------------------------------------------
    _as(b)
    teams_b = [_team("Lucknow Whites"), _team("Lucknow Golds"), _team("Lucknow Greys")]
    players_b = [_player(f"B Player {i}") for i in range(1, 7)]
    detail_b = _tournament("Lucknow League", teams_b)
    t_b = detail_b["id"]
    fixture_b_first = detail_b["fixtures"][0]["id"]
    started_b = _start(fixture_b_first, players_b[0:2], players_b[2:4])
    assert started_b.status_code == 200, started_b.text
    match_b = started_b.json()["match_id"]

    # --- put a delivery on the board so edit/undo have something to attack ---
    _as(admin)
    for mid in (match_a, match_a2, match_b):
        assert client.post(f"{API}/matches/{mid}/bowler", json={"bowler": "Opening Bowler"}).status_code == 200
        assert _score(mid, 1).status_code == 200

    return World(
        stores=stores, admin=admin, a=a, b=b,
        umpire_a=umpire_a, umpire_b=umpire_b,
        commentator_a=commentator_a, commentator_b=commentator_b,
        player_user=player_user, general=general,
        t_a=t_a, t_b=t_b, teams_a=teams_a, teams_b=teams_b,
        players_a=players_a, players_b=players_b,
        fixture_a=fixtures_a[0]["id"], fixture_b=fixture_b_first,
        open_fixture_a=open_fixture_a,
        match_a=match_a, match_a2=match_a2, match_b=match_b,
    )


def test_the_scenario_is_actually_two_separate_organizers(world: World) -> None:
    """Guards the guards. If A and B were the same account, or if the ownership
    rows were never written, every isolation test below would pass while
    proving nothing."""
    assert world.a.id != world.b.id
    assert world.a.role == Roles.ORGANIZER and world.b.role == Roles.ORGANIZER
    assert world.stores.owners.get_owner("tournament", world.t_a) == world.a.id
    assert world.stores.owners.get_owner("tournament", world.t_b) == world.b.id
    # and the match really is stamped as belonging to A's competition
    assert world.stores.tournaments.tournament_id_for_match(world.match_a) == world.t_a
    assert world.stores.tournaments.tournament_id_for_match(world.match_b) == world.t_b


# --------------------------------------------------------------------------- #
# 1. An organizer runs their own competition
# --------------------------------------------------------------------------- #
def test_organizer_a_can_change_settings_on_their_own_tournament(world: World) -> None:
    """The organizer who created a competition must be able to run it, or the
    product has no organizer role at all."""
    _as(world.a)
    res = client.patch(f"{API}/tournaments/{world.t_a}/settings", json={"dls_enabled": True})
    assert res.status_code == 200, res.text
    assert res.json()["config"]["dls_enabled"] is True


def test_organizer_a_can_register_a_squad_in_their_own_tournament(world: World) -> None:
    """Picking who plays for whom is the organizer's job; if this needed an
    admin, every team sheet in the country would queue behind one person."""
    _as(world.a)
    res = client.post(
        f"{API}/tournaments/{world.t_a}/teams/{world.teams_a[0]}/squad",
        json={"player_id": world.players_a[4]},
    )
    assert res.status_code == 200, res.text
    reds = next(s for s in res.json() if s["team_id"] == world.teams_a[0])
    assert world.players_a[4] in [p["id"] for p in reds["players"]]


def test_organizer_a_can_start_a_fixture_in_their_own_tournament(world: World) -> None:
    """Starting a fixture is what turns a schedule into a live scorecard."""
    _as(world.a)
    res = _start(world.open_fixture_a, world.players_a[0:2], world.players_a[4:6])
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "live"


def test_organizer_a_can_score_the_match_inside_their_own_tournament(world: World) -> None:
    """A fixture-started match records no owner of its own, so the only thing
    that can authorize its organizer is the competition it belongs to. If that
    link breaks, an organizer is locked out of their own live game mid-over."""
    _as(world.a)
    assert _score(world.match_a, 4).status_code == 200


def test_organizer_a_can_delete_their_own_tournament(world: World) -> None:
    """An organizer who created a competition by mistake must be able to remove
    it without opening a support ticket."""
    _as(world.a)
    assert client.delete(f"{API}/tournaments/{world.t_a}").status_code == 204


def test_deleting_a_tournament_leaves_nothing_pointing_at_it(world: World) -> None:
    """A deleted competition must take its dependants with it. Fixtures, squads,
    staff entries and the ownership row all key on the tournament id, so any one
    of them left behind is a row referring to something that no longer resolves
    — and a staff entry in particular would keep showing on somebody's dashboard
    as a job on a cup that does not exist.
    """
    _as(world.a)
    assert _staff(world.t_a, "umpires", world.umpire_a.id).status_code in (200, 201)
    assert world.stores.staff.list_for_tournament(world.t_a) != []

    assert client.delete(f"{API}/tournaments/{world.t_a}").status_code == 204

    assert client.get(f"{API}/tournaments/{world.t_a}").status_code == 404
    assert world.stores.tournaments.fixtures(world.t_a) == []
    assert world.stores.staff.list_for_tournament(world.t_a) == []
    assert world.stores.staff.list_for_user(world.umpire_a.id) == []
    assert world.stores.owners.get_owner("tournament", world.t_a) is None
    squads = app.dependency_overrides[get_tournament_service]().squads
    assert squads.list_tournament(world.t_a) == []


def test_deleting_a_tournament_does_not_orphan_the_matches_played_in_it(
    world: World,
) -> None:
    """The scorecards outlive the competition. Once the fixtures are gone the
    derived "which tournament is this match in" lookup returns nothing, so the
    match's own ownership row is the only remaining fact that says whose it is.
    If deleting the cup dropped that too, the organizer would be locked out of
    their own completed games and nobody but an admin could ever touch them.
    """
    _as(world.a)
    assert client.delete(f"{API}/tournaments/{world.t_a}").status_code == 204

    assert world.stores.tournaments.tournament_id_for_match(world.match_a) is None
    assert world.stores.owners.get_owner("match", world.match_a) == world.a.id
    assert client.get(f"{API}/matches/{world.match_a}").status_code == 200
    assert _score(world.match_a, 4).status_code == 200
    assert client.put(
        f"{API}/matches/{world.match_a}/balls/0", json={"action": "runs", "value": 6}
    ).status_code == 200
    # …and still nobody else's to score. Losing the fixture link must not turn a
    # tournament match into an unowned friendly anybody may edit.
    _as(world.b)
    _denied(_score(world.match_a, 4), "B scoring A's match after the cup was deleted")


def test_deleting_a_tournament_is_written_to_the_audit_trail(world: World) -> None:
    """Destroying a season's scorecards is exactly the kind of act the trail
    exists for, and now that an organizer can do it — not only an admin — the
    line naming who did it is the only record left."""
    _as(world.a)
    assert client.delete(f"{API}/tournaments/{world.t_a}").status_code == 204

    rows = world.stores.audit.list(action="tournament.deleted")
    assert [(r.actor_id, r.resource_id) for r in rows] == [(world.a.id, world.t_a)]
    assert "Prayagraj Cup" in rows[0].detail


# --------------------------------------------------------------------------- #
# 2. …and must not reach anybody else's. One verb per test.
# --------------------------------------------------------------------------- #
def test_organizer_a_cannot_patch_settings_on_organizer_bs_tournament(world: World) -> None:
    """Rain rules decide matches. One organizer rewriting another's is a result
    changed by somebody with no standing in that competition."""
    _as(world.a)
    _denied(
        client.patch(f"{API}/tournaments/{world.t_b}/settings", json={"dls_enabled": True}),
        "A patching B's tournament settings",
    )


def test_organizer_a_cannot_register_a_squad_in_organizer_bs_tournament(world: World) -> None:
    """A stranger adding a player to your squad is a ringer in your team sheet."""
    _as(world.a)
    _denied(
        client.post(
            f"{API}/tournaments/{world.t_b}/teams/{world.teams_b[0]}/squad",
            json={"player_id": world.players_b[2]},
        ),
        "A registering a squad in B's tournament",
    )


def test_organizer_a_cannot_delete_organizer_bs_tournament(world: World) -> None:
    """Deleting a competition takes every scorecard in it with it."""
    _as(world.a)
    _denied(client.delete(f"{API}/tournaments/{world.t_b}"), "A deleting B's tournament")
    _as(world.b)
    assert client.get(f"{API}/tournaments/{world.t_b}").status_code == 200  # still there


def test_organizer_a_cannot_start_a_fixture_in_organizer_bs_tournament(world: World) -> None:
    """Whoever starts a fixture picks the XI and opens the scoring session."""
    _as(world.b)
    detail = client.get(f"{API}/tournaments/{world.t_b}").json()
    unstarted = next(f for f in detail["fixtures"] if not f.get("match_id"))
    _as(world.a)
    _denied(
        _start(unstarted["id"], world.players_b[0:2], world.players_b[2:4]),
        "A starting B's fixture",
    )


# --------------------------------------------------------------------------- #
# 3. IDOR — the same request, one id changed
# --------------------------------------------------------------------------- #
def test_idor_changing_the_tournament_id_in_the_url_is_refused(world: World) -> None:
    """The classic insecure-direct-object-reference: A does something they are
    genuinely allowed to do, then sends the byte-for-byte identical request with
    a different id in the path. Tournament ids are public — they are in the
    listing every visitor can read — so guessing is not even required.
    """
    _as(world.a)
    listing = client.get(f"{API}/tournaments")
    assert listing.status_code == 200
    ids = {t["id"] for t in listing.json()}
    assert world.t_b in ids, "B's tournament id is public, so this is a pure IDOR"

    mine = client.patch(f"{API}/tournaments/{world.t_a}/settings", json={"dls_enabled": True})
    assert mine.status_code == 200, "the legitimate request A is allowed to make"

    theirs = client.patch(f"{API}/tournaments/{world.t_b}/settings", json={"dls_enabled": True})
    _denied(theirs, "the same request with B's id substituted")


# --------------------------------------------------------------------------- #
# 4. B must not touch a match inside A's competition
# --------------------------------------------------------------------------- #
def test_organizer_b_cannot_score_a_match_in_organizer_as_tournament(world: World) -> None:
    """Both organizers hold match.score. If the capability alone were accepted,
    one organizer could take over another's live game by knowing its id."""
    _as(world.b)
    _denied(_score(world.match_a), "B scoring A's match")


def test_organizer_b_cannot_edit_a_ball_in_organizer_as_match(world: World) -> None:
    """Editing a delivery rewrites the scorecard retroactively — the quietest
    way to change a result."""
    _as(world.b)
    _denied(
        client.put(f"{API}/matches/{world.match_a}/balls/0", json={"action": "runs", "value": 6}),
        "B editing a ball in A's match",
    )


def test_organizer_b_cannot_undo_in_organizer_as_match(world: World) -> None:
    """Undo removes the last delivery. Repeated by an outsider it empties an
    innings."""
    _as(world.b)
    _denied(client.post(f"{API}/matches/{world.match_a}/undo"), "B undoing in A's match")


def test_organizer_b_cannot_delete_organizer_as_match(world: World) -> None:
    """Deleting a match destroys every career statistic derived from it."""
    _as(world.b)
    _denied(client.delete(f"{API}/matches/{world.match_a}"), "B deleting A's match")
    assert client.get(f"{API}/matches/{world.match_a}").status_code == 200  # still there


def test_organizer_b_cannot_approve_an_umpire_onto_organizer_as_match(world: World) -> None:
    """Approving officials is how scoring rights are handed out. If B could
    approve on A's match, B could grant themselves a scorer."""
    _as(world.umpire_b)
    assert client.post(f"{API}/matches/{world.match_a}/officials/request").status_code == 204
    _as(world.b)
    _denied(
        client.post(f"{API}/matches/{world.match_a}/officials/{world.umpire_b.id}/approve"),
        "B approving their own umpire on A's match",
    )


# --------------------------------------------------------------------------- #
# 5. Other people's teams and players
# --------------------------------------------------------------------------- #
def test_organizer_a_cannot_delete_organizer_bs_team(world: World) -> None:
    """A team carries its whole roster and history."""
    _as(world.a)
    _denied(client.delete(f"{API}/teams/{world.teams_b[0]}"), "A deleting B's team")
    assert client.get(f"{API}/teams/{world.teams_b[0]}").status_code == 200


def test_organizer_a_cannot_delete_organizer_bs_players(world: World) -> None:
    """Deleting a roster player erases a cricketer's record."""
    _as(world.a)
    for pid in world.players_b:
        _denied(client.delete(f"{API}/players/{pid}"), f"A deleting B's player {pid}")
    assert client.get(f"{API}/players/{world.players_b[0]}").status_code == 200


def test_organizer_a_cannot_add_a_member_to_organizer_bs_team(world: World) -> None:
    """Squad membership is the team owner's to set."""
    _as(world.a)
    _denied(
        client.post(f"{API}/teams/{world.teams_b[0]}/members", json={"name": "Smuggled In"}),
        "A adding a member to B's team",
    )


def test_organizer_a_cannot_rewrite_organizer_bs_player(world: World) -> None:
    """Renaming somebody else's player is defacement, and the phone number field
    makes it worse: a player's contact number is how organizers reach them."""
    _as(world.a)
    _denied(
        client.patch(
            f"{API}/players/{world.players_b[0]}",
            json={"name": "Vandalised", "phone": "0000000000"},
        ),
        "A rewriting B's player",
    )


def test_organizer_a_cannot_delete_organizer_bs_player_photo(world: World) -> None:
    """A destructive write on somebody else's roster, with no ownership check."""
    _as(world.a)
    _denied(
        client.delete(f"{API}/players/{world.players_b[0]}/photo"),
        "A deleting B's player photo",
    )


# --------------------------------------------------------------------------- #
# 6-8. Roles are granted, never taken
# --------------------------------------------------------------------------- #
def _signup(username: str, wanted: Optional[str]) -> dict:
    body = {
        "full_name": "Signing Up", "username": username,
        "mobile_no": str(next(_MOBILES)), "password": "secret1",
    }
    if wanted is not None:
        body["role"] = wanted
    res = client.post(f"{API}/auth/register", json=body)
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.parametrize("wanted", ["organizer", "umpire", "commentator", "player", "team_owner", "admin"])
def test_signup_creates_a_general_user_whatever_role_the_form_asked_for(
    _isolated_authorization_stores: Stores, wanted: str
) -> None:
    """If the sign-up form could set the role, anybody could register as an
    organizer and start running (and deleting) competitions before a human ever
    looked at them."""
    out = _signup(f"applicant_{wanted}", wanted)
    assert out["role"] == Roles.GENERAL_USER, f"asked for {wanted}, got {out['role']}"
    stored = _isolated_authorization_stores.users.get_by_id(out["id"])
    assert stored.role == Roles.GENERAL_USER, "and the stored record agrees"


_SPEC: dict = {}


def _openapi() -> dict:
    """The live route table. Cached — building it costs seconds."""
    if not _SPEC:
        res = client.get("/openapi.json")
        assert res.status_code == 200, res.text
        _SPEC.update(res.json())
    return _SPEC


def _role_writing_paths() -> list[tuple[str, str]]:
    """Every mutating operation in the live OpenAPI document that is about
    changing an *account's* role — i.e. every endpoint a self-promotion attempt
    would plausibly aim at.

    Path parameters are stripped before matching, so ``{staff_role}`` in
    ``/tournaments/{id}/staff/{staff_role}/{user_id}`` is not mistaken for one:
    that names a job on one competition, not the role on an account.
    """
    out: list[tuple[str, str]] = []
    for path, ops in _openapi()["paths"].items():
        literal = re.sub(r"\{[^}]*\}", "", path).lower()
        segments = {s for chunk in literal.split("/") for s in chunk.split("-")}
        if "role" not in segments and "roles" not in segments:
            continue
        for method in ops:
            if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
                out.append((method.upper(), path))
    return out


def test_no_role_changing_endpoint_lives_outside_the_admin_area() -> None:
    """Enumerated from the live OpenAPI document rather than a hand-written
    list, so a new self-service role endpoint added tomorrow fails this test the
    day it ships."""
    found = _role_writing_paths()
    assert found, "sanity: there should be at least one role endpoint to check"
    strays = [(m, p) for m, p in found if not p.startswith(f"{API}/admin/")]
    assert strays == [], f"role-changing endpoints outside /admin: {strays}"


def test_a_user_cannot_promote_themselves_through_any_role_endpoint(world: World) -> None:
    """Every plausible promotion route, tried as the victim's own account: the
    role-request queue, the direct role assignment, and the organizer
    appointment. A 200 on any of them is a total compromise — organizer is one
    role assignment away from every tournament on the platform."""
    me = world.general
    _as(me)
    attempts = [
        ("POST", f"{API}/admin/role-requests/{me.id}/approve", None),
        ("POST", f"{API}/admin/role-requests/{me.id}/reject", None),
        ("PUT", f"{API}/admin/users/{me.id}/role", {"role": Roles.ADMIN}),
        ("PUT", f"{API}/admin/users/{me.id}/role", {"role": Roles.ORGANIZER}),
        ("POST", f"{API}/admin/organizers", {"user_id": me.id}),
        ("PATCH", f"{API}/admin/organizers/{me.id}", {"is_active": True}),
    ]
    for method, url, body in attempts:
        res = client.request(method, url, json=body) if body else client.request(method, url)
        _denied(res, f"{method} {url} as the target user")
    assert world.stores.users.get_by_id(me.id).role == Roles.GENERAL_USER


def test_a_user_cannot_promote_themselves_by_smuggling_a_role_into_a_profile_write(
    world: World,
) -> None:
    """The other shape of the attack: not a role endpoint, but a role field
    posted to an endpoint the user *is* allowed to call."""
    me = _as(world.general)
    for url, body in (
        (f"{API}/auth/profile", {
            "address": "1 Test Road", "pincode": "211001", "city": "Prayagraj",
            "district": "Prayagraj", "state": "UP", "region": "North",
            "role": Roles.ADMIN, "is_active": True,
        }),
        (f"{API}/auth/email", {"email": "nobody@example.com", "role": Roles.ADMIN}),
    ):
        res = client.request("POST" if url.endswith("profile") else "PATCH", url, json=body)
        assert res.status_code < 500, f"{url} crashed on an unexpected field: {res.text[:200]}"
    assert world.stores.users.get_by_id(me.id).role == Roles.GENERAL_USER
    assert client.get(f"{API}/auth/me").json()["role"] == Roles.GENERAL_USER


def test_only_an_admin_can_assign_the_organizer_role(world: World) -> None:
    """Organizer is the role that owns competitions. Anyone who can hand it out
    can hand it to themselves."""
    target = world.general
    for actor in (world.a, world.umpire_a, world.commentator_a, world.player_user, world.general):
        _as(actor)
        _denied(_assign_role(target.id, Roles.ORGANIZER), f"{actor.role} assigning organizer")
    _anonymous()
    assert client.put(f"{API}/admin/users/{target.id}/role", json={"role": Roles.ORGANIZER}).status_code == 401

    _as(world.admin)
    granted = _assign_role(target.id, Roles.ORGANIZER)
    assert granted.status_code == 200, granted.text
    assert granted.json()["role"] == Roles.ORGANIZER
    assert world.stores.users.get_by_id(target.id).role == Roles.ORGANIZER


def test_admin_appoints_an_organizer_for_an_area(world: World) -> None:
    """The scenario's first line — an admin appoints an organizer and says where
    they work — has to be a real endpoint, not a row somebody inserted by hand."""
    _as(world.admin)
    area = client.post(f"{API}/admin/areas", json={"name": "Varanasi", "state": "UP"})
    assert area.status_code == 201, area.text
    candidate = _account(world.stores, "Chandra Verma", "organizer_c")
    made = client.post(
        f"{API}/admin/organizers",
        json={"user_id": candidate.id, "area_id": area.json()["id"]},
    )
    assert made.status_code == 201, made.text
    assert made.json()["area_name"] == "Varanasi"
    assert world.stores.users.get_by_id(candidate.id).role == Roles.ORGANIZER


def test_an_organizer_cannot_appoint_another_organizer(world: World) -> None:
    """Otherwise the first organizer becomes a second admin: appoint an ally,
    have the ally appoint you back, and the area boundary means nothing."""
    _as(world.a)
    _denied(client.post(f"{API}/admin/areas", json={"name": "Kanpur"}), "A creating an area")
    _denied(
        client.post(f"{API}/admin/organizers", json={"user_id": world.general.id}),
        "A appointing an organizer",
    )


# --------------------------------------------------------------------------- #
# 9. The capability floor: roles that create nothing, delete nothing
# --------------------------------------------------------------------------- #
_UNPRIVILEGED = ("player_user", "umpire_a", "commentator_a", "general")


@pytest.mark.parametrize("who", _UNPRIVILEGED)
def test_unprivileged_roles_cannot_create_a_tournament(world: World, who: str) -> None:
    """Running a competition is the organizer's job; a player who could create
    one could then delete its fixtures."""
    _as(getattr(world, who))
    _denied(
        client.post(
            f"{API}/tournaments",
            json={"name": "Rogue Cup", "format": "round_robin", "format_id": "t20",
                  "team_ids": world.teams_a[0:2]},
        ),
        f"{who} creating a tournament",
    )


@pytest.mark.parametrize("who", _UNPRIVILEGED)
def test_unprivileged_roles_cannot_create_a_match(world: World, who: str) -> None:
    """A match created by anybody is a scorecard nobody is accountable for."""
    _as(getattr(world, who))
    _denied(
        client.post(
            f"{API}/matches",
            json={"team_a": "X", "team_b": "Y", "format_id": "t20", "bat_first": "a"},
        ),
        f"{who} creating a match",
    )


@pytest.mark.parametrize("who", _UNPRIVILEGED)
def test_unprivileged_roles_cannot_create_a_team(world: World, who: str) -> None:
    """Teams are owned; an unowned team created by a passer-by can never be
    managed by anyone but an admin."""
    _as(getattr(world, who))
    _denied(client.post(f"{API}/teams", json={"name": "Rogue XI"}), f"{who} creating a team")


@pytest.mark.parametrize("who", _UNPRIVILEGED)
def test_unprivileged_roles_cannot_delete_anything(world: World, who: str) -> None:
    """One sweep over every destructive endpoint the role could reach."""
    _as(getattr(world, who))
    for what, url in (
        ("tournament", f"{API}/tournaments/{world.t_a}"),
        ("match", f"{API}/matches/{world.match_a}"),
        ("team", f"{API}/teams/{world.teams_a[0]}"),
        ("player", f"{API}/players/{world.players_a[0]}"),
        ("team member", f"{API}/teams/{world.teams_a[0]}/members/{world.players_a[0]}"),
        ("squad entry", f"{API}/tournaments/{world.t_a}/teams/{world.teams_a[0]}/squad/{world.players_a[0]}"),
    ):
        _denied(client.delete(url), f"{who} deleting a {what}")


# --------------------------------------------------------------------------- #
# 10-11. Access that comes from an assignment, not from a role
# --------------------------------------------------------------------------- #
def test_an_umpire_approved_for_one_match_can_score_that_match(world: World) -> None:
    """The umpire role grants no capability at all — an umpire's access comes
    entirely from being approved for a specific fixture."""
    _as(world.umpire_a)
    assert _score(world.match_a).status_code == 403, "not approved yet"
    assert client.post(f"{API}/matches/{world.match_a}/officials/request").status_code == 204

    _as(world.a)  # the organizer whose competition it is approves them
    approved = client.post(f"{API}/matches/{world.match_a}/officials/{world.umpire_a.id}/approve")
    assert approved.status_code == 204, approved.text

    _as(world.umpire_a)
    assert _score(world.match_a).status_code == 200


def test_an_umpire_approved_for_one_match_cannot_score_another(world: World) -> None:
    """The approval is per match, not per platform. An umpire standing in one
    fixture must not be able to edit the game on the next field."""
    _as(world.umpire_a)
    client.post(f"{API}/matches/{world.match_a}/officials/request")
    _as(world.a)
    assert client.post(f"{API}/matches/{world.match_a}/officials/{world.umpire_a.id}/approve").status_code == 204

    _as(world.umpire_a)
    assert _score(world.match_a).status_code == 200, "approved here"
    _denied(_score(world.match_a2), "the same umpire on a different match in the same tournament")
    _denied(_score(world.match_b), "the same umpire on another organizer's match")


def test_a_commentator_assigned_to_tournament_a_can_post_on_its_matches(world: World) -> None:
    """A commentator an organizer put on their staff is expected to talk over
    that competition's games."""
    _as(world.a)
    assert _staff(world.t_a, "commentators", world.commentator_a.id).status_code == 201
    _as(world.commentator_a)
    res = client.post(f"{API}/matches/{world.match_a}/commentary", json={"text": "Cracking shot."})
    assert res.status_code == 201, res.text


def test_a_commentator_assigned_to_tournament_a_cannot_post_on_tournament_bs_matches(
    world: World,
) -> None:
    """Commentary is published under the author's name on somebody else's live
    scorecard. An unstaffed commentator talking over B's final is defacement
    with a byline."""
    _as(world.a)
    assert _staff(world.t_a, "commentators", world.commentator_a.id).status_code == 201
    _as(world.commentator_a)
    _denied(
        client.post(f"{API}/matches/{world.match_b}/commentary", json={"text": "Not my match."}),
        "A's commentator posting on B's match",
    )


def test_an_organizer_can_put_an_umpire_and_a_commentator_on_their_tournament_staff(
    world: World,
) -> None:
    """The scenario line 'A creates Umpire A, Commentator A' has to be reachable
    from A's own session, or every assignment-scoped guard in the product is
    unreachable through the API."""
    _as(world.a)
    for kind, person in (("umpires", world.umpire_a), ("commentators", world.commentator_a)):
        res = _staff(world.t_a, kind, person.id)
        assert res.status_code == 201, f"POST staff/{kind}: {res.status_code} {res.text[:200]}"
    listed = client.get(f"{API}/tournaments/{world.t_a}/staff")
    assert listed.status_code == 200
    assert {(s["user_id"], s["staff_role"]) for s in listed.json()} == {
        (world.umpire_a.id, UMPIRE), (world.commentator_a.id, COMMENTATOR),
    }


def test_an_organizer_cannot_staff_another_organizers_tournament(world: World) -> None:
    """Staffing B's competition would let A install their own scorer inside it."""
    _as(world.a)
    _denied(_staff(world.t_b, "umpires", world.umpire_a.id), "A staffing B's tournament")
    _denied(
        _staff(world.t_b, "commentators", world.commentator_a.id),
        "A putting a commentator on B's tournament",
    )
    assert world.stores.staff.get(world.t_b, world.umpire_a.id, UMPIRE) is None


def test_an_organizer_cannot_read_another_organizers_staff_list(world: World) -> None:
    """Who officiates a competition is the organizer's business. A rival
    organizer reading it learns the whole pool of people they could poach or
    impersonate."""
    _as(world.b)
    assert _staff(world.t_b, "umpires", world.umpire_b.id).status_code == 201
    _as(world.a)
    _denied(client.get(f"{API}/tournaments/{world.t_b}/staff"), "A reading B's staff list")
    _denied(client.get(f"{API}/tournaments/{world.t_b}/players"), "A reading B's player list")


def test_staff_on_one_tournament_are_not_staff_on_another(world: World) -> None:
    """An umpire Organizer A adds must not become available to Organizer B —
    the assignment is per competition, and ``/mine/staffing`` is how each person
    sees only their own."""
    _as(world.a)
    assert _staff(world.t_a, "umpires", world.umpire_a.id).status_code == 201
    _as(world.umpire_a)
    mine = client.get(f"{API}/tournaments/mine/staffing")
    assert mine.status_code == 200
    assert [e["tournament_id"] for e in mine.json()] == [world.t_a]
    _denied(client.get(f"{API}/tournaments/{world.t_b}/staff"), "A's umpire reading B's staff")


# --------------------------------------------------------------------------- #
# 12. A player belongs to the game, not to one organizer
# --------------------------------------------------------------------------- #
def test_the_same_player_can_be_registered_in_both_organizers_tournaments(world: World) -> None:
    """Club cricketers play in several competitions in the same season. If a
    registration in Prayagraj blocked one in Lucknow, the roster would fork into
    a duplicate player per organizer and every career statistic would split."""
    shared = world.players_a[5]

    _as(world.a)
    in_a = client.post(
        f"{API}/tournaments/{world.t_a}/teams/{world.teams_a[0]}/squad", json={"player_id": shared}
    )
    assert in_a.status_code == 200, in_a.text

    _as(world.b)
    in_b = client.post(
        f"{API}/tournaments/{world.t_b}/teams/{world.teams_b[0]}/squad", json={"player_id": shared}
    )
    assert in_b.status_code == 200, in_b.text

    _anonymous()
    squads_a = client.get(f"{API}/tournaments/{world.t_a}/squads")
    squads_b = client.get(f"{API}/tournaments/{world.t_b}/squads")
    assert squads_a.status_code == 200 and squads_b.status_code == 200
    assert shared in [p["id"] for s in squads_a.json() for p in s["players"]]
    assert shared in [p["id"] for s in squads_b.json() for p in s["players"]]


def test_a_players_own_record_shows_every_tournament_they_are_registered_in(
    world: World,
) -> None:
    """A player looking at their own profile should see both competitions they
    have been entered into, without having to know which organizer to ask.

    Read from ``/players/{id}/tournaments`` rather than the tournament buckets
    in ``/history``: those are rebuilt from matches already played, and this
    player has not been fielded in either cup yet, which is exactly the case
    that used to be invisible.
    """
    _as(world.a)
    # A player nobody has fielded yet — every one of world.players_a is already
    # in an XI, and a player who has batted would prove nothing here.
    shared = _player("Bench Player")
    client.post(f"{API}/tournaments/{world.t_a}/teams/{world.teams_a[0]}/squad",
                json={"player_id": shared})
    _as(world.b)
    client.post(f"{API}/tournaments/{world.t_b}/teams/{world.teams_b[0]}/squad",
                json={"player_id": shared})

    _anonymous()
    record = client.get(f"{API}/players/{shared}/tournaments")
    assert record.status_code == 200, record.text
    rows = record.json()
    names = {r["tournament_name"] for r in rows}
    assert {"Prayagraj Cup", "Lucknow League"} <= names, f"only saw {names}"
    assert {r["team_name"] for r in rows} == {"Prayagraj Reds", "Lucknow Whites"}
    assert all(r["has_played"] is False for r in rows), "not fielded in either yet"

    # …and history still shows nothing, which is what made this hole invisible.
    history = client.get(f"{API}/players/{shared}/history")
    assert history.status_code == 200
    assert history.json()["by_tournament"] == []


def test_a_players_registrations_say_which_competitions_they_have_played_in(
    world: World,
) -> None:
    """"Entered" and "played" are different facts and the row carries both. A
    player already fielded in one cup and only entered in another must not have
    the two flattened together, or the record cannot tell a debut from a
    selection."""
    fielded = world.players_a[0]  # opened the batting in match_a
    _as(world.b)
    client.post(f"{API}/tournaments/{world.t_b}/teams/{world.teams_b[0]}/squad",
                json={"player_id": fielded})
    _as(world.a)
    client.post(f"{API}/tournaments/{world.t_a}/teams/{world.teams_a[0]}/squad",
                json={"player_id": fielded})

    _anonymous()
    rows = client.get(f"{API}/players/{fielded}/tournaments").json()
    by_name = {r["tournament_name"]: r for r in rows}
    assert by_name["Prayagraj Cup"]["has_played"] is True
    assert by_name["Prayagraj Cup"]["matches_played"] == 2  # match_a and match_a2
    assert by_name["Lucknow League"]["has_played"] is False
    assert by_name["Lucknow League"]["matches_played"] == 0


def test_a_players_registrations_are_public_and_404_for_a_stranger_id(
    world: World,
) -> None:
    """Public like the rest of a player's record — a squad list is announced,
    not confidential. An id that is not a player is a 404, not an empty list,
    so a mistyped id is not silently reported as "registered in nothing"."""
    _anonymous()
    assert client.get(f"{API}/players/{world.players_a[0]}/tournaments").status_code == 200
    assert client.get(f"{API}/players/999999/tournaments").status_code == 404


def test_a_deleted_competition_drops_out_of_its_players_registrations(
    world: World,
) -> None:
    """A registration is only meaningful while the competition exists. Once the
    organizer deletes the cup, the player's record must not keep advertising a
    tournament nobody can open."""
    _as(world.a)
    player = _player("Bench Player")
    client.post(f"{API}/tournaments/{world.t_a}/teams/{world.teams_a[0]}/squad",
                json={"player_id": player})
    _anonymous()
    assert client.get(f"{API}/players/{player}/tournaments").json() != []

    _as(world.a)
    assert client.delete(f"{API}/tournaments/{world.t_a}").status_code == 204
    _anonymous()
    assert client.get(f"{API}/players/{player}/tournaments").json() == []


# --------------------------------------------------------------------------- #
# 13-14. Admin bypasses ownership and scope
# --------------------------------------------------------------------------- #
def test_admin_can_manage_and_delete_both_tournaments(world: World) -> None:
    """The admin is the escalation path for both organizers. If admin were
    scoped like an organizer, an abandoned competition could never be cleaned
    up."""
    _as(world.admin)
    for tid in (world.t_a, world.t_b):
        assert client.patch(f"{API}/tournaments/{tid}/settings", json={"dls_enabled": True}).status_code == 200
    assert client.post(
        f"{API}/tournaments/{world.t_a}/teams/{world.teams_a[0]}/squad",
        json={"player_id": world.players_a[4]},
    ).status_code == 200
    for tid in (world.t_a, world.t_b):
        assert client.delete(f"{API}/tournaments/{tid}").status_code == 204
        assert client.get(f"{API}/tournaments/{tid}").status_code == 404


def test_admin_can_score_any_organizers_match(world: World) -> None:
    """Somebody has to be able to correct a scorecard when an organizer is
    unreachable mid-tournament."""
    _as(world.admin)
    for mid in (world.match_a, world.match_b):
        assert _score(mid, 2).status_code == 200
        assert client.put(f"{API}/matches/{mid}/balls/0", json={"action": "runs", "value": 6}).status_code == 200
        assert client.post(f"{API}/matches/{mid}/undo").status_code == 200
        assert client.delete(f"{API}/matches/{mid}").status_code == 204


# --------------------------------------------------------------------------- #
# Holes found while attacking the matrix above
# --------------------------------------------------------------------------- #
def test_a_fixture_started_match_records_its_organizer_as_its_owner(world: World) -> None:
    """Ownership is the primary authorization fact in this system; a derived
    lookup through a fixture row is the fallback. A match that only has the
    fallback is one deleted row away from belonging to nobody."""
    assert world.stores.owners.get_owner("match", world.match_a) == world.a.id


def test_an_organizers_inbox_shows_umpire_requests_on_their_tournament_fixtures(
    world: World,
) -> None:
    """The inbox exists so an organizer can approve officials without opening
    every match. For tournament cricket — the only place fixtures exist — it is
    permanently empty, and an umpire's request is silently never seen."""
    _as(world.umpire_a)
    assert client.post(f"{API}/matches/{world.match_a}/officials/request").status_code == 204

    _as(world.a)
    inbox = client.get(f"{API}/matches/officials/pending")
    assert inbox.status_code == 200
    assert [r["umpire_id"] for r in inbox.json()] == [world.umpire_a.id], (
        f"organizer's inbox was {inbox.json()}"
    )


def test_the_broadcast_control_channel_is_not_open_to_anonymous_callers(world: World) -> None:
    """The overlay is what a live audience sees. Its control endpoint is the one
    write in the whole API with no caller at all."""
    _anonymous()
    # A valid mode, so a refusal here can only be an authorization refusal —
    # an invalid one would 400 and prove nothing.
    res = client.post(f"{API}/matches/{world.match_b}/broadcast", json={"mode": "WAGON", "auto": True})
    assert res.status_code in (401, 403), (
        f"anonymous broadcast control returned {res.status_code} — {res.text[:200]}"
    )


def test_a_stranger_cannot_claim_to_have_commentated_somebody_elses_match(
    world: World,
) -> None:
    """Member records are shown in the Network directory and are how organizers
    pick officials. A tally anybody can pad is a tally nobody can trust."""
    _as(world.general)
    _denied(
        client.post(f"{API}/matches/{world.match_b}/commentate"),
        "a general user claiming credit for B's match",
    )


def test_the_can_score_flag_agrees_with_what_the_server_will_actually_allow(
    world: World,
) -> None:
    """A permission flag that disagrees with the guard is worse than no flag:
    the UI offers an action, the scorer starts a session, and the first
    delivery of the match is rejected."""
    _as(world.b)
    told = client.get(f"{API}/matches/{world.match_a}/officials")
    assert told.status_code == 200
    actual_ok = _score(world.match_a).status_code == 200
    assert told.json()["can_score"] is actual_ok, (
        f"told can_score={told.json()['can_score']}, server allowed={actual_ok}"
    )


# --------------------------------------------------------------------------- #
# 15. Deleting a match — the owner's act, not the admin's alone
# --------------------------------------------------------------------------- #
def _official_repo():
    return app.dependency_overrides[get_match_official_repo]()


def _commentary():
    return app.dependency_overrides[get_commentary_service]()


def _fielding():
    return app.dependency_overrides[get_fielding_event_service]()


def _awards():
    return app.dependency_overrides[get_award_repo]()


def _match_players():
    return app.dependency_overrides[get_match_service]().match_players


def test_the_organizer_who_started_a_match_can_delete_it(world: World) -> None:
    """The same reasoning that lets an organizer delete their own competition,
    one level down: a scorecard opened by mistake — wrong teams, wrong XI — has
    to be removable by the person who opened it, or every correction queues
    behind an admin."""
    _as(world.a)
    assert client.delete(f"{API}/matches/{world.match_a}").status_code == 204
    assert client.get(f"{API}/matches/{world.match_a}").status_code == 404


def test_a_match_with_no_ownership_row_still_belongs_to_its_competition(
    world: World,
) -> None:
    """The derived half of the rule. With the match's own ownership row gone,
    the only fact left saying whose it is, is the fixture it was started from —
    and that has to be enough for its organizer and no use to anybody else."""
    world.stores.owners.delete("match", world.match_a)

    _as(world.b)
    _denied(client.delete(f"{API}/matches/{world.match_a}"), "B deleting A's fixture match")
    _as(world.a)
    assert client.delete(f"{API}/matches/{world.match_a}").status_code == 204


def test_an_umpire_approved_to_score_a_match_still_cannot_delete_it(world: World) -> None:
    """Deleting is deliberately narrower than scoring. An umpire is invited to
    officiate one game; nothing about standing in the middle should let them
    erase the scorecard and every career statistic derived from it."""
    _as(world.umpire_a)
    assert client.post(f"{API}/matches/{world.match_a}/officials/request").status_code == 204
    _as(world.a)
    assert client.post(
        f"{API}/matches/{world.match_a}/officials/{world.umpire_a.id}/approve"
    ).status_code == 204

    _as(world.umpire_a)
    assert _score(world.match_a).status_code == 200, "approved to score"
    _denied(
        client.delete(f"{API}/matches/{world.match_a}"),
        "an approved umpire deleting the match they officiate",
    )
    assert client.get(f"{API}/matches/{world.match_a}").status_code == 200


def test_deleting_a_match_puts_its_fixture_back_on_the_schedule(world: World) -> None:
    """The sharpest thing a deleted match leaves behind. A fixture still
    pointing at it reads as permanently "live" — the derived status skips a
    match it cannot load — and ``start_fixture`` refuses it as "already
    started", so the game could never be re-scored and the cup could never
    finish.
    """
    _as(world.a)
    assert client.delete(f"{API}/matches/{world.match_a}").status_code == 204

    fixture = world.stores.tournaments.get_fixture(world.fixture_a)
    assert fixture.match_id is None
    assert fixture.status == "scheduled"

    detail = client.get(f"{API}/tournaments/{world.t_a}")
    assert detail.status_code == 200
    row = next(f for f in detail.json()["fixtures"] if f["id"] == world.fixture_a)
    assert row["match_id"] is None and row["status"] == "scheduled"

    restarted = _start(world.fixture_a, world.players_a[0:2], world.players_a[2:4])
    assert restarted.status_code == 200, restarted.text
    assert restarted.json()["status"] == "live"


def test_deleting_a_match_leaves_nothing_pointing_at_it(world: World) -> None:
    """Everything keyed on a match id goes with the match. The umpire approvals
    matter most — an approval is a standing permission to score, so one left
    behind is an authorization row pointing at nothing — but a commentary line
    with no scorecard, a fielding event still counting against a player, and an
    award on a profile that links to a 404 are all the same fault.
    """
    _as(world.a)
    assert client.post(
        f"{API}/matches/{world.match_a}/commentary", json={"text": "Edged, and gone."}
    ).status_code == 201
    assert client.post(
        f"{API}/matches/{world.match_a}/fielding",
        json={"fielder": "A Player 1", "kind": "drop"},
    ).status_code == 201
    _as(world.umpire_a)
    assert client.post(f"{API}/matches/{world.match_a}/officials/request").status_code == 204
    _awards().add_award(world.match_a, "mom", world.players_a[0], "A Player 1", "41 (28)")

    _as(world.a)
    assert client.delete(f"{API}/matches/{world.match_a}").status_code == 204

    assert client.get(f"{API}/matches/{world.match_a}").status_code == 404
    assert world.stores.owners.get_owner("match", world.match_a) is None
    assert _official_repo().list_for_match(world.match_a) == []
    assert _commentary().list(world.match_a) == []
    assert _fielding().list(world.match_a) == []
    assert _awards().awards_for_match(world.match_a) == []
    assert _awards().awards_for_player(world.players_a[0]) == []
    assert _match_players().for_match(world.match_a) == []


def test_deleting_a_match_is_written_to_the_audit_trail(world: World) -> None:
    """A deleted scorecard takes every statistic derived from it, and now that
    an organizer can do it — not only an admin — the line naming who did it is
    the only record that the game was ever played."""
    _as(world.a)
    state = client.get(f"{API}/matches/{world.match_a}")
    assert state.status_code == 200
    label = f"{state.json()['team_a']} vs {state.json()['team_b']}"

    assert client.delete(f"{API}/matches/{world.match_a}").status_code == 204

    rows = world.stores.audit.list(action="match.deleted")
    assert [(r.actor_id, r.resource_id) for r in rows] == [(world.a.id, world.match_a)]
    assert label in rows[0].detail


def test_a_refused_match_deletion_writes_no_audit_line_and_deletes_nothing(
    world: World,
) -> None:
    """The guard runs before anything is touched, so a refusal must leave the
    match, its fixture and the trail exactly as they were."""
    _as(world.b)
    _denied(client.delete(f"{API}/matches/{world.match_a}"), "B deleting A's match")

    assert client.get(f"{API}/matches/{world.match_a}").status_code == 200
    assert world.stores.tournaments.tournament_id_for_match(world.match_a) == world.t_a
    assert world.stores.audit.list(action="match.deleted") == []


# --------------------------------------------------------------------------- #
# 16. A tournament says who manages it, so the client never has to probe
# --------------------------------------------------------------------------- #
def test_the_tournament_detail_tells_its_organizer_that_it_is_theirs(world: World) -> None:
    """Without this the client cannot tell whether to offer the management
    controls, so it finds out by firing a request that 403s — a refused write on
    every visit by everybody who is not the owner."""
    _as(world.a)
    mine = client.get(f"{API}/tournaments/{world.t_a}")
    assert mine.status_code == 200
    assert mine.json()["is_manager"] is True

    theirs = client.get(f"{API}/tournaments/{world.t_b}")
    assert theirs.status_code == 200, "B's board is public — A reads it, and is told it is not theirs"
    assert theirs.json()["is_manager"] is False


def test_an_anonymous_visitor_is_told_a_tournament_is_not_theirs_rather_than_refused(
    world: World,
) -> None:
    """The board is public. Answering "can I manage this" for a signed-out
    visitor must not cost them the page."""
    _anonymous()
    res = client.get(f"{API}/tournaments/{world.t_a}")
    assert res.status_code == 200
    assert res.json()["is_manager"] is False


def test_the_admin_is_told_they_manage_every_competition(world: World) -> None:
    """Admin bypasses ownership everywhere else; the flag has to say so too, or
    the admin screen hides the controls the admin actually has."""
    _as(world.admin)
    for tid in (world.t_a, world.t_b):
        res = client.get(f"{API}/tournaments/{tid}")
        assert res.status_code == 200
        assert res.json()["is_manager"] is True


@pytest.mark.parametrize("who", ["b", "umpire_a", "commentator_a", "player_user", "general"])
def test_nobody_outside_a_competition_is_told_they_manage_it(world: World, who: str) -> None:
    """Including the staff: an umpire assigned to a tournament works inside it,
    which is not the same as running it."""
    _as(world.a)
    assert _staff(world.t_a, "umpires", world.umpire_a.id).status_code == 201
    _as(getattr(world, who))
    res = client.get(f"{API}/tournaments/{world.t_a}")
    assert res.status_code == 200
    assert res.json()["is_manager"] is False


def test_the_is_manager_flag_agrees_with_what_the_server_will_actually_allow(
    world: World,
) -> None:
    """The same rule the ``can_score`` flag is held to. A flag that disagrees
    with the guard is worse than no flag: the UI offers a button and the server
    refuses the click.
    """
    for who in ("a", "b", "admin", "umpire_a", "general"):
        _as(getattr(world, who))
        told = client.get(f"{API}/tournaments/{world.t_a}")
        assert told.status_code == 200
        write = client.patch(f"{API}/tournaments/{world.t_a}/settings", json={"dls_enabled": True})
        assert write.status_code in (200, 403), f"{who}: unexpected {write.status_code}"
        assert told.json()["is_manager"] is (write.status_code == 200), (
            f"{who} was told is_manager={told.json()['is_manager']} "
            f"and the write returned {write.status_code}"
        )


def test_a_freshly_created_tournament_comes_back_marked_as_yours(world: World) -> None:
    """The create response is the same DTO, and the client renders it straight
    into the management view — so it has to carry the same honest answer."""
    _as(world.a)
    created = client.post(
        f"{API}/tournaments",
        json={"name": "Second Cup", "format": "round_robin", "format_id": "t20",
              "team_ids": world.teams_a[0:2]},
    )
    assert created.status_code == 201, created.text
    assert created.json()["is_manager"] is True


def test_the_manager_flag_cannot_be_claimed_in_a_request(world: World) -> None:
    """It is computed from the token through ScopeService, so there is nothing
    in the request to forge — a body that asserts it changes neither the answer
    nor the refusal."""
    _as(world.a)
    _denied(
        client.patch(
            f"{API}/tournaments/{world.t_b}/settings",
            json={"dls_enabled": True, "is_manager": True, "owner_id": world.a.id},
        ),
        "A claiming to manage B's tournament in a request body",
    )
    still = client.get(f"{API}/tournaments/{world.t_b}")
    assert still.status_code == 200
    assert still.json()["is_manager"] is False


# --------------------------------------------------------------------------- #
# 17. The sweep: no action on a match is decided by a capability alone
# --------------------------------------------------------------------------- #
# Every mutating (and owner-only reading) endpoint on a match, fired at A's
# match from B's session. B is an organizer, so B holds every capability A does
# — match.create, match.score, match.commentate. Anything here that answers 200
# is an endpoint deciding access from the role instead of from ownership.
_MATCH_ACTIONS: tuple[tuple[str, str, Any], ...] = (
    ("POST", "/balls", {"action": "runs", "value": 1}),
    ("PUT", "/balls/0", {"action": "runs", "value": 6}),
    ("DELETE", "/balls/0", None),
    ("POST", "/bowler", {"bowler": "Ringer"}),
    ("POST", "/undo", None),
    ("POST", "/second-innings", None),
    ("POST", "/declare", None),
    ("POST", "/super-over", {"bat_first": "a"}),
    ("POST", "/interrupt", {"reason": "rain"}),
    ("POST", "/resume", {"overs": 5}),
    ("POST", "/interrupt/cancel", None),
    ("POST", "/abandon", {"reason": "rain"}),
    ("POST", "/revised-target", {"target": 40, "overs": 5}),
    ("POST", "/dls-suggest", {"team2_overs": 5}),
    ("PUT", "/stream", {"stream_url": "https://youtu.be/dQw4w9WgXcQ"}),
    ("POST", "/broadcast", {"mode": "WAGON", "auto": True}),
    ("POST", "/fielding", {"fielder": "Ringer", "kind": "drop"}),
    ("DELETE", "/fielding/1", None),
    ("POST", "/clips", {"url": "https://youtu.be/dQw4w9WgXcQ", "label": "Ringer"}),
    ("DELETE", "/clips/1", None),
    ("POST", "/clips/auto", {"anchor": 0}),
    ("GET", "/recording", None),
    ("POST", "/commentary", {"text": "Not my match."}),
    ("POST", "/commentate", None),
    ("", "", None),  # the match itself: DELETE /matches/{id}
)


@pytest.mark.parametrize("method,suffix,body", _MATCH_ACTIONS)
def test_no_action_on_a_match_is_open_to_another_organizer(
    world: World, method: str, suffix: str, body: Any
) -> None:
    """One sweep over every endpoint on a match, from the session of somebody
    who holds every capability the owner holds. A 200 anywhere here is an
    organizer reaching into another organizer's live game."""
    _as(world.b)
    verb = method or "DELETE"
    url = f"{API}/matches/{world.match_a}{suffix}"
    res = client.request(verb, url, json=body) if body is not None else client.request(verb, url)
    _denied(res, f"B calling {verb} {suffix or '(the match itself)'} on A's match")
