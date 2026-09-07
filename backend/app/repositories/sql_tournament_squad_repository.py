"""SQL-backed per-tournament squad repository."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import TournamentSquadRow


def _pint(value: str) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class SqlTournamentSquadRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def team_of(self, tournament_id, player_id) -> Optional[str]:
        ti, pi = _pint(tournament_id), _pint(player_id)
        if ti is None or pi is None:
            return None
        with self._sf() as s:
            row = s.query(TournamentSquadRow).filter_by(tournament_id=ti, player_id=pi).first()
            return str(row.team_id) if row else None

    def add(self, tournament_id, team_id, player_id) -> None:
        ti, tm, pi = _pint(tournament_id), _pint(team_id), _pint(player_id)
        if ti is None or tm is None or pi is None:
            return
        with self._sf() as s:
            if s.query(TournamentSquadRow.id).filter_by(tournament_id=ti, player_id=pi).first():
                return
            s.add(TournamentSquadRow(tournament_id=ti, team_id=tm, player_id=pi))
            try:
                s.commit()
            except IntegrityError:  # raced — already registered, fine
                s.rollback()

    def remove(self, tournament_id, team_id, player_id) -> None:
        ti, tm, pi = _pint(tournament_id), _pint(team_id), _pint(player_id)
        with self._sf() as s:
            s.query(TournamentSquadRow).filter_by(
                tournament_id=ti, team_id=tm, player_id=pi
            ).delete()
            s.commit()

    def list_team(self, tournament_id, team_id) -> list[str]:
        ti, tm = _pint(tournament_id), _pint(team_id)
        with self._sf() as s:
            rows = s.query(TournamentSquadRow.player_id).filter_by(tournament_id=ti, team_id=tm).all()
            return [str(r[0]) for r in rows]

    def list_tournament(self, tournament_id) -> list[tuple[str, str]]:
        ti = _pint(tournament_id)
        with self._sf() as s:
            rows = s.query(TournamentSquadRow).filter_by(tournament_id=ti).all()
            return [(str(r.team_id), str(r.player_id)) for r in rows]

    def list_for_player(self, player_id) -> list[tuple[str, str]]:
        """Every competition this player is registered in, newest first — the
        reverse of ``list_tournament``, indexed by ``player_id``."""
        pi = _pint(player_id)
        if pi is None:
            return []
        with self._sf() as s:
            rows = (
                s.query(TournamentSquadRow)
                .filter_by(player_id=pi)
                .order_by(TournamentSquadRow.tournament_id.desc())
                .all()
            )
            return [(str(r.tournament_id), str(r.team_id)) for r in rows]

    def delete_tournament(self, tournament_id) -> None:
        ti = _pint(tournament_id)
        with self._sf() as s:
            s.query(TournamentSquadRow).filter_by(tournament_id=ti).delete()
            s.commit()
