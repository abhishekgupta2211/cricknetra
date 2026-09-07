"""SQL-backed tournaments + fixtures."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import FixtureRow, TournamentRow
from app.repositories.tournament_repository import FixtureRecord, TournamentRecord


def _pint(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _t_rec(r: TournamentRow) -> TournamentRecord:
    return TournamentRecord(
        id=str(r.id), name=r.name, format=r.format, rules=r.rules,
        team_ids=[str(t) for t in (r.team_ids or [])], status=r.status,
        config=r.config or {},
    )


def _f_rec(r: FixtureRow) -> FixtureRecord:
    return FixtureRecord(
        id=str(r.id), tournament_id=str(r.tournament_id), round=r.round, position=r.position,
        team_a_id=str(r.team_a_id) if r.team_a_id is not None else None,
        team_b_id=str(r.team_b_id) if r.team_b_id is not None else None,
        match_id=str(r.match_id) if r.match_id is not None else None,
        status=r.status,
        winner_team_id=str(r.winner_team_id) if r.winner_team_id is not None else None,
        group=r.group,
    )


class SqlTournamentRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def add(self, name, format, rules, team_ids, config=None) -> TournamentRecord:
        with self._sf() as s:
            row = TournamentRow(
                name=name, format=format, rules=rules,
                team_ids=[int(t) for t in team_ids], status="active",
                config=config or {},
            )
            s.add(row)
            s.flush()
            rec = _t_rec(row)
            s.commit()
            return rec

    def get(self, tournament_id) -> Optional[TournamentRecord]:
        tid = _pint(tournament_id)
        if tid is None:
            return None
        with self._sf() as s:
            row = s.get(TournamentRow, tid)
            return _t_rec(row) if row else None

    def update_config(self, tournament_id, patch) -> Optional[TournamentRecord]:
        tid = _pint(tournament_id)
        if tid is None:
            return None
        with self._sf() as s:
            row = s.get(TournamentRow, tid)
            if row is None:
                return None
            row.config = {**(row.config or {}), **patch}  # reassign so SQLAlchemy tracks the JSON change
            s.commit()
            return _t_rec(row)

    def list(self) -> list[TournamentRecord]:
        with self._sf() as s:
            return [_t_rec(r) for r in s.query(TournamentRow).order_by(TournamentRow.id.desc()).all()]

    def delete(self, tournament_id) -> None:
        tid = _pint(tournament_id)
        if tid is None:
            return
        with self._sf() as s:
            s.query(FixtureRow).filter_by(tournament_id=tid).delete(synchronize_session=False)
            row = s.get(TournamentRow, tid)
            if row is not None:
                s.delete(row)
            s.commit()

    def add_fixtures(self, tournament_id, fixtures) -> list[FixtureRecord]:
        tid = _pint(tournament_id)
        with self._sf() as s:
            rows = []
            for fx in fixtures:
                rnd, pos, a, b = fx[0], fx[1], fx[2], fx[3]
                group = fx[4] if len(fx) > 4 else None
                row = FixtureRow(
                    tournament_id=tid, round=rnd, position=pos,
                    team_a_id=_pint(a) if a is not None else None,
                    team_b_id=_pint(b) if b is not None else None,
                    group=group,
                )
                s.add(row)
                rows.append(row)
            s.flush()
            recs = [_f_rec(r) for r in rows]
            s.commit()
            return recs

    def fixtures(self, tournament_id) -> list[FixtureRecord]:
        tid = _pint(tournament_id)
        if tid is None:
            return []
        with self._sf() as s:
            rows = (
                s.query(FixtureRow).filter_by(tournament_id=tid)
                .order_by(FixtureRow.round, FixtureRow.position).all()
            )
            return [_f_rec(r) for r in rows]

    def get_fixture(self, fixture_id) -> Optional[FixtureRecord]:
        fid = _pint(fixture_id)
        if fid is None:
            return None
        with self._sf() as s:
            row = s.get(FixtureRow, fid)
            return _f_rec(row) if row else None

    def fixture_for_match(self, match_id) -> Optional[FixtureRecord]:
        mid = _pint(match_id)
        if mid is None:
            return None
        with self._sf() as s:
            row = s.query(FixtureRow).filter_by(match_id=mid).first()
            return _f_rec(row) if row else None

    def tournament_id_for_match(self, match_id) -> Optional[str]:
        """Which competition a match was started from, if any.

        Authorization leans on this: a match inside a tournament is the
        organizer's to run, and a friendly belongs only to whoever started it.
        """
        fixture = self.fixture_for_match(match_id)
        return fixture.tournament_id if fixture is not None else None

    def update_fixture(self, fixture_id, match_id=None, status=None, winner_team_id=None) -> Optional[FixtureRecord]:
        fid = _pint(fixture_id)
        if fid is None:
            return None
        with self._sf() as s:
            row = s.get(FixtureRow, fid)
            if row is None:
                return None
            if match_id is not None:
                row.match_id = _pint(match_id)
            if status is not None:
                row.status = status
            if winner_team_id is not None:
                row.winner_team_id = _pint(winner_team_id)
            rec = _f_rec(row)
            s.commit()
            return rec

    def unlink_match(self, match_id) -> Optional[FixtureRecord]:
        """Put a fixture back on the schedule after its match was deleted.

        ``update_fixture`` reads ``None`` as "leave alone", so clearing the link
        needs its own method. A fixture still pointing at a deleted match reads
        as permanently "live" and can never be started again.
        """
        mid = _pint(match_id)
        if mid is None:
            return None
        with self._sf() as s:
            row = s.query(FixtureRow).filter_by(match_id=mid).first()
            if row is None:
                return None
            row.match_id = None
            row.status = "scheduled"
            row.winner_team_id = None
            rec = _f_rec(row)
            s.commit()
            return rec
