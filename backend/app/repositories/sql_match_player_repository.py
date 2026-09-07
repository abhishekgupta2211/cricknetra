"""SQL-backed match↔player links."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import MatchPlayerRow
from app.repositories.match_player_repository import MatchPlayerLink


def _pint(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_link(r: MatchPlayerRow) -> MatchPlayerLink:
    return MatchPlayerLink(
        match_id=str(r.match_id),
        player_id=str(r.player_id),
        name=r.name,
        side=r.side,
        team_id=str(r.team_id) if r.team_id is not None else None,
    )


class SqlMatchPlayerRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def link(self, links: list[MatchPlayerLink]) -> None:
        with self._sf() as s:
            for link in links:
                mid, pid = _pint(link.match_id), _pint(link.player_id)
                if mid is None or pid is None:
                    continue
                s.add(
                    MatchPlayerRow(
                        match_id=mid,
                        player_id=pid,
                        name=link.name,
                        side=link.side,
                        team_id=_pint(link.team_id) if link.team_id else None,
                    )
                )
            s.commit()

    def for_player(self, player_id: str) -> list[MatchPlayerLink]:
        pid = _pint(player_id)
        if pid is None:
            return []
        with self._sf() as s:
            return [_to_link(r) for r in s.query(MatchPlayerRow).filter_by(player_id=pid).all()]

    def for_match(self, match_id: str) -> list[MatchPlayerLink]:
        mid = _pint(match_id)
        if mid is None:
            return []
        with self._sf() as s:
            return [_to_link(r) for r in s.query(MatchPlayerRow).filter_by(match_id=mid).all()]

    def for_team(self, team_id: str) -> list[MatchPlayerLink]:
        tid = _pint(team_id)
        if tid is None:
            return []
        with self._sf() as s:
            return [_to_link(r) for r in s.query(MatchPlayerRow).filter_by(team_id=tid).all()]

    def delete_for_match(self, match_id: str) -> None:
        mid = _pint(match_id)
        if mid is None:
            return
        with self._sf() as s:
            s.query(MatchPlayerRow).filter_by(match_id=mid).delete(synchronize_session=False)
            s.commit()
