"""Tournament + fixture storage (in-memory). SQL impl in sql_tournament_repository."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Optional, Protocol


@dataclass
class TournamentRecord:
    id: str
    name: str
    format: str
    rules: dict
    team_ids: list[str]
    status: str = "active"
    config: dict = field(default_factory=dict)


@dataclass
class FixtureRecord:
    id: str
    tournament_id: str
    round: int
    position: int
    team_a_id: Optional[str]
    team_b_id: Optional[str]
    match_id: Optional[str] = None
    status: str = "scheduled"
    winner_team_id: Optional[str] = None  # a team id, "tie", or None
    group: Optional[str] = None  # pool label for a group-stage fixture; None = bracket


class TournamentRepository(Protocol):
    def add(self, name: str, format: str, rules: dict, team_ids: list[str], config: Optional[dict] = None) -> TournamentRecord: ...
    def get(self, tournament_id: str) -> Optional[TournamentRecord]: ...
    def list(self) -> list[TournamentRecord]: ...
    def update_config(self, tournament_id: str, patch: dict) -> Optional[TournamentRecord]: ...
    def delete(self, tournament_id: str) -> None: ...
    def add_fixtures(self, tournament_id: str, fixtures: list[tuple]) -> list[FixtureRecord]: ...
    def fixtures(self, tournament_id: str) -> list[FixtureRecord]: ...
    def get_fixture(self, fixture_id: str) -> Optional[FixtureRecord]: ...
    def fixture_for_match(self, match_id: str) -> Optional[FixtureRecord]: ...  # reverse: match → fixture
    def tournament_id_for_match(self, match_id: str) -> Optional[str]: ...  # which competition a match belongs to
    def update_fixture(self, fixture_id: str, match_id=None, status=None, winner_team_id=None) -> Optional[FixtureRecord]: ...
    def unlink_match(self, match_id: str) -> Optional[FixtureRecord]: ...  # a deleted match's fixture goes back on the schedule


class InMemoryTournamentRepository:
    def __init__(self) -> None:
        self._t: dict[str, TournamentRecord] = {}
        self._f: dict[str, FixtureRecord] = {}
        self._tids = count(1)
        self._fids = count(1)

    def add(self, name, format, rules, team_ids, config=None) -> TournamentRecord:
        tid = str(next(self._tids))
        rec = TournamentRecord(tid, name, format, rules, [str(t) for t in team_ids], config=config or {})
        self._t[tid] = rec
        return rec

    def get(self, tournament_id) -> Optional[TournamentRecord]:
        return self._t.get(tournament_id)

    def update_config(self, tournament_id, patch) -> Optional[TournamentRecord]:
        rec = self._t.get(tournament_id)
        if rec is None:
            return None
        rec.config = {**(rec.config or {}), **patch}
        return rec

    def list(self) -> list[TournamentRecord]:
        return list(self._t.values())

    def delete(self, tournament_id) -> None:
        self._t.pop(tournament_id, None)
        for fid in [f.id for f in self._f.values() if f.tournament_id == tournament_id]:
            self._f.pop(fid, None)

    def add_fixtures(self, tournament_id, fixtures) -> list[FixtureRecord]:
        out = []
        for fx in fixtures:
            rnd, pos, a, b = fx[0], fx[1], fx[2], fx[3]
            group = fx[4] if len(fx) > 4 else None
            fid = str(next(self._fids))
            rec = FixtureRecord(
                fid, tournament_id, rnd, pos,
                str(a) if a is not None else None,
                str(b) if b is not None else None,
                group=group,
            )
            self._f[fid] = rec
            out.append(rec)
        return out

    def fixtures(self, tournament_id) -> list[FixtureRecord]:
        rows = [f for f in self._f.values() if f.tournament_id == tournament_id]
        return sorted(rows, key=lambda f: (f.round, f.position))

    def get_fixture(self, fixture_id) -> Optional[FixtureRecord]:
        return self._f.get(fixture_id)

    def fixture_for_match(self, match_id) -> Optional[FixtureRecord]:
        return next((f for f in self._f.values() if f.match_id == str(match_id)), None)

    def tournament_id_for_match(self, match_id) -> Optional[str]:
        """Which competition a match was started from, if any.

        Authorization leans on this: a match inside a tournament is the
        organizer's to run, and a friendly belongs only to whoever started it.
        """
        fixture = self.fixture_for_match(match_id)
        return fixture.tournament_id if fixture is not None else None

    def update_fixture(self, fixture_id, match_id=None, status=None, winner_team_id=None) -> Optional[FixtureRecord]:
        rec = self._f.get(fixture_id)
        if rec is None:
            return None
        if match_id is not None:
            rec.match_id = str(match_id)
        if status is not None:
            rec.status = status
        if winner_team_id is not None:
            rec.winner_team_id = str(winner_team_id)
        return rec

    def unlink_match(self, match_id) -> Optional[FixtureRecord]:
        """Put a fixture back on the schedule after its match was deleted.

        ``update_fixture`` cannot do this: it reads ``None`` as "leave alone",
        which is what a partial update needs and exactly wrong for clearing.
        A fixture left pointing at a deleted match is stuck — it reads as
        permanently "live" (the derived status skips a match it cannot load)
        and ``start_fixture`` refuses it as "already started", so the game can
        never be re-scored.
        """
        rec = self.fixture_for_match(match_id)
        if rec is None:
            return None
        rec.match_id = None
        rec.status = "scheduled"
        rec.winner_team_id = None
        return rec
