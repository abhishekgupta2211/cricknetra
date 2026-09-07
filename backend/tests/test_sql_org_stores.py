"""The SQL twins of the organizer / staff / audit registries.

These four stores were the only ones in the system with no database
implementation: their singletons in ``deps`` were unconditionally in-memory, so
on a multi-worker Postgres deployment an organizer appointed on one process did
not exist on the next, and the audit trail — a record of who granted a role or
destroyed a competition — was lost on every restart.

Two things are checked here, and the second is the one that matters:

* **Conformance.** The SQL class satisfies the same Protocol the in-memory one
  does, method for method and parameter for parameter. A store that is missing
  a method fails at the first request that needs it, in production, on the one
  deployment shape no test covers.
* **Parity.** The same script of calls, replayed against both implementations,
  produces the same answers — the reinstate-don't-duplicate rule, the
  one-profile-per-account rule, the orderings, and the audit trail's
  newest-first read. Anything the in-memory store enforces with a dict key the
  SQL store has to enforce with a constraint, or "may this umpire open this
  tournament" is answered differently depending on which one is wired up.

SQLite stands in for Postgres, as ``test_persistence`` already does: the models
are written to run on both, and no CI runner here has a database.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401 — register tables on Base
from app.db.base import Base
from app.repositories.audit_repository import (
    AuditActions,
    AuditRepository,
    InMemoryAuditRepository,
)
from app.repositories.org_repository import InMemoryOrgRepository, OrgRepository
from app.repositories.sql_audit_repository import SqlAuditRepository
from app.repositories.sql_org_repository import SqlOrgRepository
from app.repositories.sql_tournament_staff_repository import SqlTournamentStaffRepository
from app.repositories.tournament_staff_repository import (
    COMMENTATOR,
    UMPIRE,
    InMemoryTournamentStaffRepository,
    TournamentStaffRepository,
)


@pytest.fixture()
def session_factory():
    """One shared in-memory SQLite database (StaticPool keeps a single
    connection), so a row written through one session is visible to the next."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def sql_orgs(session_factory) -> SqlOrgRepository:
    return SqlOrgRepository(session_factory)


@pytest.fixture()
def sql_staff(session_factory) -> SqlTournamentStaffRepository:
    return SqlTournamentStaffRepository(session_factory)


@pytest.fixture()
def sql_audit(session_factory) -> SqlAuditRepository:
    return SqlAuditRepository(session_factory)


# --------------------------------------------------------------------------- #
# Protocol conformance
# --------------------------------------------------------------------------- #
def _protocol_methods(protocol: type) -> list[str]:
    return sorted(
        name for name, value in vars(protocol).items()
        if callable(value) and not name.startswith("_")
    )


def _positional_names(fn: Callable[..., Any]) -> list[str]:
    return [
        p.name for p in inspect.signature(fn).parameters.values()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.name != "self"
    ]


@pytest.mark.parametrize(
    "protocol, sql_cls, memory_cls",
    [
        (OrgRepository, SqlOrgRepository, InMemoryOrgRepository),
        (
            TournamentStaffRepository,
            SqlTournamentStaffRepository,
            InMemoryTournamentStaffRepository,
        ),
        (AuditRepository, SqlAuditRepository, InMemoryAuditRepository),
    ],
)
def test_the_sql_store_satisfies_the_same_protocol_as_the_in_memory_one(
    protocol: type, sql_cls: type, memory_cls: type
) -> None:
    """Structural typing is only checked by a type checker, and a repository is
    resolved at runtime from ``settings.database_url`` — so a missing method is
    invisible until the one deployment shape that uses it. Comparing parameter
    names as well as names catches the subtler version: a method that exists but
    cannot be called the way its only caller calls it.
    """
    expected = _protocol_methods(protocol)
    assert expected, "the Protocol declares no methods — this test proves nothing"
    for name in expected:
        assert hasattr(sql_cls, name), f"{sql_cls.__name__} is missing {name}()"
        assert _positional_names(getattr(sql_cls, name)) == _positional_names(
            getattr(protocol, name)
        ), f"{sql_cls.__name__}.{name}() does not take the Protocol's arguments"
        # …and the in-memory store it has to be interchangeable with.
        assert _positional_names(getattr(sql_cls, name)) == _positional_names(
            getattr(memory_cls, name)
        ), f"{sql_cls.__name__}.{name}() has drifted from {memory_cls.__name__}"


# --------------------------------------------------------------------------- #
# Areas, organizations, organizer profiles
# --------------------------------------------------------------------------- #
def test_an_area_survives_being_written_and_read_back(sql_orgs: SqlOrgRepository) -> None:
    """The point of the whole exercise: the row is in the database, not in the
    worker that created it."""
    area = sql_orgs.add_area("Prayagraj", "UP")
    assert area.id and area.name == "Prayagraj" and area.state == "UP"
    assert sql_orgs.get_area(area.id).name == "Prayagraj"
    assert [a.name for a in sql_orgs.list_areas()] == ["Prayagraj"]

    sql_orgs.delete_area(area.id)
    assert sql_orgs.get_area(area.id) is None


def test_areas_and_organizations_come_back_in_name_order(sql_orgs: SqlOrgRepository) -> None:
    """An admin reads these as a list to pick from, so the order is part of the
    contract — and it is case-insensitive, or "agra" sorts after "Zirakpur"."""
    for name in ("Varanasi", "agra", "Prayagraj"):
        sql_orgs.add_area(name, None)
    assert [a.name for a in sql_orgs.list_areas()] == ["agra", "Prayagraj", "Varanasi"]

    area = sql_orgs.list_areas()[0]
    sql_orgs.add_organization("Zed Sports", area.id)
    sql_orgs.add_organization("Ace Sports", area.id)
    sql_orgs.add_organization("Elsewhere XI", None)
    assert [o.name for o in sql_orgs.list_organizations()] == [
        "Ace Sports", "Elsewhere XI", "Zed Sports",
    ]
    # …and filtering by area returns only that area's bodies.
    assert [o.name for o in sql_orgs.list_organizations(area.id)] == [
        "Ace Sports", "Zed Sports",
    ]


def test_an_id_that_is_not_a_number_is_a_miss_not_a_crash(sql_orgs: SqlOrgRepository) -> None:
    """Area and organization ids arrive from URLs. A 500 on a typo would turn a
    mistyped link into an error page instead of a 404."""
    assert sql_orgs.get_area("not-an-id") is None
    assert sql_orgs.get_organization("") is None
    sql_orgs.delete_area("not-an-id")  # must not raise


def test_appointing_the_same_account_twice_moves_one_profile(
    sql_orgs: SqlOrgRepository,
) -> None:
    """One profile per account, enforced by the unique index rather than by a
    dict key. Two rows would make "is this organizer suspended?" answerable two
    ways, and ScopeService reads exactly that on every organizer write."""
    prayagraj = sql_orgs.add_area("Prayagraj", "UP")
    lucknow = sql_orgs.add_area("Lucknow", "UP")

    first = sql_orgs.upsert_organizer("7", prayagraj.id, None, created_by="1")
    assert first.user_id == "7" and first.area_id == prayagraj.id and first.is_active

    moved = sql_orgs.upsert_organizer("7", lucknow.id, None, created_by="1")
    assert moved.area_id == lucknow.id
    assert len(sql_orgs.list_organizers()) == 1, "a second appointment made a second row"


def test_an_upsert_that_supplies_nothing_leaves_the_posting_alone(
    sql_orgs: SqlOrgRepository,
) -> None:
    """A PATCH that only reactivates somebody must not blank the area they work
    in — the in-memory store keeps it, so this one has to as well."""
    area = sql_orgs.add_area("Prayagraj", "UP")
    org = sql_orgs.add_organization("XYZ Sports", area.id)
    sql_orgs.upsert_organizer("7", area.id, org.id, created_by="1")

    kept = sql_orgs.upsert_organizer("7", None, None, created_by=None)
    assert kept.area_id == area.id and kept.organization_id == org.id


def test_suspending_an_organizer_keeps_the_row_and_the_posting(
    sql_orgs: SqlOrgRepository,
) -> None:
    """Suspension is not deletion: the profile stays readable so an admin can
    see who once ran what, and reactivating does not require re-typing it."""
    area = sql_orgs.add_area("Prayagraj", "UP")
    sql_orgs.upsert_organizer("7", area.id, None, created_by="1")

    suspended = sql_orgs.set_organizer_active("7", False)
    assert suspended.is_active is False
    assert sql_orgs.get_organizer("7").is_active is False
    assert sql_orgs.get_organizer("7").area_id == area.id

    # …and re-appointing them brings them back, as upsert does in memory.
    assert sql_orgs.upsert_organizer("7", None, None, None).is_active is True
    assert sql_orgs.set_organizer_active("404", True) is None, "no profile, no row"


def test_organizers_list_in_numeric_account_order(sql_orgs: SqlOrgRepository) -> None:
    """The column is a string, so the database would put "10" before "9". The
    in-memory store sorts numerically and this list is read side by side with
    it, so the two must not disagree."""
    for uid in ("10", "2", "9"):
        sql_orgs.upsert_organizer(uid, None, None, None)
    assert [o.user_id for o in sql_orgs.list_organizers()] == ["2", "9", "10"]


def test_organizers_can_be_filtered_to_one_area(sql_orgs: SqlOrgRepository) -> None:
    """An area's page counts its own organizers; an unfiltered list would show
    every organizer in the country under every city."""
    prayagraj = sql_orgs.add_area("Prayagraj", "UP")
    lucknow = sql_orgs.add_area("Lucknow", "UP")
    sql_orgs.upsert_organizer("1", prayagraj.id, None, None)
    sql_orgs.upsert_organizer("2", lucknow.id, None, None)

    assert [o.user_id for o in sql_orgs.list_organizers(prayagraj.id)] == ["1"]
    sql_orgs.delete_organizer("1")
    assert sql_orgs.get_organizer("1") is None


# --------------------------------------------------------------------------- #
# Tournament staff
# --------------------------------------------------------------------------- #
def test_re_adding_a_removed_staffer_reinstates_one_entry(
    sql_staff: SqlTournamentStaffRepository,
) -> None:
    """The (tournament, user, role) triple is the identity of a staff entry. A
    second row would let ``get`` and ``set_active`` disagree about whether
    somebody is on the staff, depending which row each found first."""
    first = sql_staff.add("1", "7", UMPIRE, added_by="2")
    sql_staff.set_active("1", "7", UMPIRE, False)

    again = sql_staff.add("1", "7", UMPIRE, added_by="2")
    assert again.id == first.id and again.is_active is True
    assert len(sql_staff.list_for_tournament("1")) == 1


def test_a_staff_entry_is_scoped_to_one_tournament(
    sql_staff: SqlTournamentStaffRepository,
) -> None:
    """An umpire Organizer A adds must not become available to Organizer B —
    the same person on two competitions is two independent entries."""
    sql_staff.add("1", "7", UMPIRE, added_by="2")
    sql_staff.add("2", "7", UMPIRE, added_by="3")

    sql_staff.remove("1", "7", UMPIRE)
    assert sql_staff.get("1", "7", UMPIRE) is None
    assert sql_staff.get("2", "7", UMPIRE) is not None, "removing from A reached into B"


def test_a_tournaments_staff_list_keeps_the_people_who_were_stood_down(
    sql_staff: SqlTournamentStaffRepository,
) -> None:
    """An organizer who suspended somebody still needs to see them, or the only
    way back is to add them again from memory. The person's *own* list is the
    opposite: it answers "what may I open", so a suspended entry is not on it."""
    sql_staff.add("1", "7", UMPIRE, added_by="2")
    sql_staff.add("1", "8", COMMENTATOR, added_by="2")
    sql_staff.set_active("1", "7", UMPIRE, False)

    assert [r.user_id for r in sql_staff.list_for_tournament("1")] == ["7", "8"]
    assert [r.user_id for r in sql_staff.list_for_tournament("1", UMPIRE)] == ["7"]
    assert sql_staff.list_for_user("7") == []
    assert [r.tournament_id for r in sql_staff.list_for_user("8")] == ["1"]
    assert sql_staff.list_for_user("8", UMPIRE) == [], "filtered to the wrong role"


def test_deleting_a_competition_takes_its_whole_staff_with_it(
    sql_staff: SqlTournamentStaffRepository,
) -> None:
    """Otherwise the entry keeps showing on somebody's dashboard as a job on a
    tournament nobody can open."""
    sql_staff.add("1", "7", UMPIRE, added_by="2")
    sql_staff.add("1", "8", COMMENTATOR, added_by="2")
    sql_staff.add("2", "7", UMPIRE, added_by="3")

    sql_staff.remove_tournament("1")
    assert sql_staff.list_for_tournament("1") == []
    assert [r.tournament_id for r in sql_staff.list_for_user("7")] == ["2"]


def test_setting_active_on_somebody_who_is_not_staff_reports_the_miss(
    sql_staff: SqlTournamentStaffRepository,
) -> None:
    """The service turns this None into "that person isn't an umpire on this
    tournament" — a silently created row would say the opposite."""
    assert sql_staff.set_active("1", "7", UMPIRE, True) is None
    assert sql_staff.list_for_tournament("1") == []


# --------------------------------------------------------------------------- #
# The audit trail
# --------------------------------------------------------------------------- #
def test_the_trail_reads_newest_first(sql_audit: SqlAuditRepository) -> None:
    """An audit log is read from the most recent change backwards. Ordered by
    id rather than the timestamp: a burst of writes shares a server clock tick,
    and rows written in one instant must still come back in order."""
    for i in range(5):
        sql_audit.add("1", AuditActions.ROLE_ASSIGNED, "user", str(i), f"change {i}")
    assert [r.resource_id for r in sql_audit.list()] == ["4", "3", "2", "1", "0"]
    assert [r.resource_id for r in sql_audit.list(limit=2)] == ["4", "3"]


def test_the_trail_filters_before_it_limits(sql_audit: SqlAuditRepository) -> None:
    """A narrow query must return its own newest page. Limiting first and then
    filtering would show an empty trail for an action that happened, just
    because a hundred other things happened after it."""
    sql_audit.add("9", AuditActions.TOURNAMENT_DELETED, "tournament", "3", "deleted the Cup")
    for i in range(50):
        sql_audit.add("1", AuditActions.ROLE_ASSIGNED, "user", str(i), "noise")

    hits = sql_audit.list(limit=10, action=AuditActions.TOURNAMENT_DELETED)
    assert [(r.actor_id, r.resource_id, r.detail) for r in hits] == [
        ("9", "3", "deleted the Cup")
    ]
    assert [r.actor_id for r in sql_audit.list(actor_id="9")] == ["9"]
    assert len(sql_audit.list(resource_type="user", limit=100)) == 50
    assert [r.detail for r in sql_audit.list(resource_type="tournament", resource_id="3")] == [
        "deleted the Cup"
    ]


def test_an_actorless_line_is_still_recorded(sql_audit: SqlAuditRepository) -> None:
    """Not every recorded act has a signed-in actor, and a trail that refused
    those would be silent about exactly the events worth keeping."""
    rec = sql_audit.add(None, AuditActions.ACCESS_DENIED, "tournament", "3", "")
    assert rec.actor_id is None and rec.when is not None
    assert sql_audit.list()[0].actor_id is None


# --------------------------------------------------------------------------- #
# Parity — the same script against both stores
# --------------------------------------------------------------------------- #
def _staff_script(repo) -> list:
    """Every observable answer the staff Protocol gives, in one sequence."""
    repo.add("1", "7", UMPIRE, added_by="2")
    repo.add("1", "8", COMMENTATOR, added_by="2")
    repo.add("2", "7", UMPIRE, added_by="3")
    repo.set_active("1", "8", COMMENTATOR, False)
    repo.add("1", "7", UMPIRE, added_by="2")  # re-add: reinstate, don't duplicate
    return [
        [(r.tournament_id, r.user_id, r.staff_role, r.is_active, r.added_by)
         for r in repo.list_for_tournament("1")],
        [(r.tournament_id, r.staff_role) for r in repo.list_for_user("7")],
        [(r.tournament_id, r.staff_role) for r in repo.list_for_user("8")],
        repo.get("1", "9", UMPIRE),
        repo.set_active("9", "9", UMPIRE, True),
    ]


def _audit_script(repo) -> list:
    repo.add("1", AuditActions.ROLE_ASSIGNED, "user", "5", "general_user -> umpire")
    repo.add(None, AuditActions.ACCESS_DENIED, "tournament", "3", "")
    repo.add("2", AuditActions.TOURNAMENT_DELETED, "tournament", "3", "deleted the Cup")
    return [
        [(r.actor_id, r.action, r.resource_type, r.resource_id, r.detail) for r in repo.list()],
        [r.action for r in repo.list(limit=1)],
        [r.action for r in repo.list(actor_id="1")],
        [r.action for r in repo.list(resource_type="tournament", resource_id="3")],
    ]


def _org_script(repo) -> list:
    area = repo.add_area("Prayagraj", "UP")
    other = repo.add_area("agra", None)
    org = repo.add_organization("XYZ Sports", area.id)
    repo.upsert_organizer("2", area.id, org.id, created_by="1")
    repo.upsert_organizer("10", other.id, None, created_by="1")
    repo.upsert_organizer("2", None, None, created_by=None)  # must not blank the posting
    repo.set_organizer_active("10", False)
    return [
        [(a.name, a.state) for a in repo.list_areas()],
        [(o.name, o.area_id == area.id) for o in repo.list_organizations()],
        [(o.user_id, o.area_id == area.id, o.organization_id == org.id, o.is_active,
          o.created_by) for o in repo.list_organizers()],
        [o.user_id for o in repo.list_organizers(area.id)],
        repo.get_organizer("404"),
    ]


@pytest.mark.parametrize(
    "script, memory_cls, sql_fixture",
    [
        (_org_script, InMemoryOrgRepository, "sql_orgs"),
        (_staff_script, InMemoryTournamentStaffRepository, "sql_staff"),
        (_audit_script, InMemoryAuditRepository, "sql_audit"),
    ],
)
def test_the_sql_store_answers_exactly_as_the_in_memory_one_does(
    script, memory_cls: type, sql_fixture: str, request: pytest.FixtureRequest
) -> None:
    """Same calls, same answers. Which store is wired up is decided by an
    environment variable, so any difference here is a behaviour change nobody
    asked for that only shows up in production.
    """
    assert script(memory_cls()) == script(request.getfixturevalue(sql_fixture))


# --------------------------------------------------------------------------- #
# Wiring — which store the app actually picks
# --------------------------------------------------------------------------- #
def test_the_new_stores_are_chosen_from_settings_like_every_other_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hole this closes. These three singletons had no ``database_url``
    branch at all — unlike every other repository in ``deps`` — so a Postgres
    deployment silently ran them in memory. Writing the SQL classes fixes
    nothing until the factory can reach them.
    """
    from app.api import deps
    from app.core.config import settings

    monkeypatch.setattr(settings, "database_url", "postgresql+psycopg://unused/db")
    # Stand in for the engine: choosing the store must not open a connection,
    # and nothing here calls through to one.
    monkeypatch.setattr(deps, "_sql_sessionmaker", lambda: None)
    for name in ("_org_repo", "_staff_repo", "_audit_repo"):
        monkeypatch.setattr(deps, name, None)

    assert isinstance(deps._org_repo_singleton(), SqlOrgRepository)
    assert isinstance(deps._staff_repo_singleton(), SqlTournamentStaffRepository)
    assert isinstance(deps._audit_repo_singleton(), SqlAuditRepository)


def test_without_a_database_url_the_new_stores_stay_in_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The local / test path is unchanged: no database configured, no database
    imported."""
    from app.api import deps
    from app.core.config import settings

    monkeypatch.setattr(settings, "database_url", None)
    for name in ("_org_repo", "_staff_repo", "_audit_repo"):
        monkeypatch.setattr(deps, name, None)

    assert isinstance(deps._org_repo_singleton(), InMemoryOrgRepository)
    assert isinstance(deps._staff_repo_singleton(), InMemoryTournamentStaffRepository)
    assert isinstance(deps._audit_repo_singleton(), InMemoryAuditRepository)
