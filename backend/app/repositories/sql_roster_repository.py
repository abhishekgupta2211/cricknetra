"""SQL-backed roster repository."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import PlayerRow, TeamMemberRow, TeamRow
from app.repositories.roster_repository import MemberRecord, PlayerRecord, TeamRecord


def _pint(value: str) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class SqlRosterRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    # ----- players -----
    def add_player(self, name, phone, batting_style, bowling_style) -> PlayerRecord:
        with self._sf() as s:
            row = PlayerRow(name=name, phone=phone, batting_style=batting_style, bowling_style=bowling_style)
            s.add(row)
            s.flush()
            rec = PlayerRecord(str(row.id), row.name, row.phone, row.batting_style, row.bowling_style, row.user_id)
            s.commit()
            return rec

    def get_player(self, player_id) -> Optional[PlayerRecord]:
        pid = _pint(player_id)
        if pid is None:
            return None
        with self._sf() as s:
            row = s.get(PlayerRow, pid)
            if row is None:
                return None
            return PlayerRecord(str(row.id), row.name, row.phone, row.batting_style, row.bowling_style, row.user_id)

    def list_players(self) -> list[PlayerRecord]:
        with self._sf() as s:
            rows = s.query(PlayerRow).order_by(PlayerRow.name).all()
            return [PlayerRecord(str(r.id), r.name, r.phone, r.batting_style, r.bowling_style, r.user_id) for r in rows]

    def update_player(self, player_id, name=None, phone=None, batting_style=None, bowling_style=None) -> Optional[PlayerRecord]:
        pid = _pint(player_id)
        if pid is None:
            return None
        with self._sf() as s:
            row = s.get(PlayerRow, pid)
            if row is None:
                return None
            if name is not None:
                row.name = name
            if phone is not None:
                row.phone = phone
            if batting_style is not None:
                row.batting_style = batting_style
            if bowling_style is not None:
                row.bowling_style = bowling_style
            rec = PlayerRecord(str(row.id), row.name, row.phone, row.batting_style, row.bowling_style, row.user_id)
            s.commit()
            return rec

    def delete_player(self, player_id) -> None:
        pid = _pint(player_id)
        if pid is None:
            return
        with self._sf() as s:
            s.query(TeamMemberRow).filter_by(player_id=pid).delete(synchronize_session=False)
            row = s.get(PlayerRow, pid)
            if row is not None:
                s.delete(row)
            s.commit()

    def claim_player(self, player_id, user_id) -> Optional[PlayerRecord]:
        pid = _pint(player_id)
        if pid is None:
            return None
        with self._sf() as s:
            row = s.get(PlayerRow, pid)
            if row is None:
                return None
            row.user_id = str(user_id)
            rec = PlayerRecord(str(row.id), row.name, row.phone, row.batting_style, row.bowling_style, row.user_id)
            s.commit()
            return rec

    def players_for_user(self, user_id) -> list[PlayerRecord]:
        with self._sf() as s:
            rows = s.query(PlayerRow).filter(PlayerRow.user_id == str(user_id)).order_by(PlayerRow.name).all()
            return [PlayerRecord(str(r.id), r.name, r.phone, r.batting_style, r.bowling_style, r.user_id) for r in rows]

    def unclaimed_by_phone(self, phone) -> list[PlayerRecord]:
        if not phone:
            return []
        with self._sf() as s:
            rows = s.query(PlayerRow).filter(
                PlayerRow.user_id.is_(None), PlayerRow.phone == phone
            ).order_by(PlayerRow.name).all()
            return [PlayerRecord(str(r.id), r.name, r.phone, r.batting_style, r.bowling_style, r.user_id) for r in rows]

    # ----- teams -----
    def add_team(self, name, location) -> TeamRecord:
        with self._sf() as s:
            row = TeamRow(name=name, location=location)
            s.add(row)
            s.flush()
            rec = TeamRecord(str(row.id), row.name, row.location, [])
            s.commit()
            return rec

    def _members(self, s: Session, team_id: int) -> list[MemberRecord]:
        rows = (
            s.query(TeamMemberRow, PlayerRow)
            .join(PlayerRow, TeamMemberRow.player_id == PlayerRow.id)
            .filter(TeamMemberRow.team_id == team_id)
            .order_by(TeamMemberRow.sort_order, TeamMemberRow.id)
            .all()
        )
        return [MemberRecord(str(p.id), p.name, bool(m.is_captain)) for m, p in rows]

    def get_team(self, team_id) -> Optional[TeamRecord]:
        tid = _pint(team_id)
        if tid is None:
            return None
        with self._sf() as s:
            row = s.get(TeamRow, tid)
            if row is None:
                return None
            return TeamRecord(str(row.id), row.name, row.location, self._members(s, tid))

    def list_teams(self) -> list[TeamRecord]:
        with self._sf() as s:
            rows = s.query(TeamRow).order_by(TeamRow.name).all()
            return [TeamRecord(str(r.id), r.name, r.location, self._members(s, r.id)) for r in rows]

    def delete_team(self, team_id) -> None:
        tid = _pint(team_id)
        if tid is None:
            return
        with self._sf() as s:
            s.query(TeamMemberRow).filter_by(team_id=tid).delete(synchronize_session=False)
            row = s.get(TeamRow, tid)
            if row is not None:
                s.delete(row)
            s.commit()

    def add_member(self, team_id, player_id, is_captain) -> bool:
        tid, pid = _pint(team_id), _pint(player_id)
        if tid is None or pid is None:
            return False
        with self._sf() as s:
            if s.get(TeamRow, tid) is None or s.get(PlayerRow, pid) is None:
                return False
            exists = s.query(TeamMemberRow).filter_by(team_id=tid, player_id=pid).first()
            if exists is None:
                order = s.query(func.count(TeamMemberRow.id)).filter_by(team_id=tid).scalar() or 0
                s.add(TeamMemberRow(team_id=tid, player_id=pid, is_captain=is_captain, sort_order=order))
                s.commit()
            return True

    def remove_member(self, team_id, player_id) -> None:
        tid, pid = _pint(team_id), _pint(player_id)
        if tid is None or pid is None:
            return
        with self._sf() as s:
            s.query(TeamMemberRow).filter_by(team_id=tid, player_id=pid).delete(synchronize_session=False)
            s.commit()
