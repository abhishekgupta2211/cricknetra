"""SQL-backed match awards store (MoM / best batter / best bowler)."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AwardRow
from app.repositories.award_repository import AwardItem


class SqlAwardRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def add_award(self, match_id, award_type, player_key, player_name, detail="") -> None:
        with self._sf() as s:
            row = s.query(AwardRow).filter_by(match_id=str(match_id), award_type=award_type).first()
            if row is None:
                s.add(AwardRow(match_id=str(match_id), award_type=award_type,
                               player_key=str(player_key), player_name=player_name, detail=detail))
            else:                                            # upsert: refresh the winner
                row.player_key, row.player_name, row.detail = str(player_key), player_name, detail
            try:
                s.commit()
            except IntegrityError:
                s.rollback()

    def delete_for_match(self, match_id) -> None:
        """Drop a deleted match's honours — an award on a player's profile that
        points at a scorecard nobody can open."""
        with self._sf() as s:
            s.query(AwardRow).filter_by(match_id=str(match_id)).delete()
            s.commit()

    def awards_for_match(self, match_id) -> list[AwardItem]:
        with self._sf() as s:
            rows = s.query(AwardRow).filter_by(match_id=str(match_id)).order_by(AwardRow.id).all()
            return [AwardItem(r.match_id, r.award_type, r.player_key, r.player_name, r.detail,
                              r.created_at.isoformat()) for r in rows]

    def awards_for_player(self, player_key, limit=50) -> list[AwardItem]:
        with self._sf() as s:
            rows = (s.query(AwardRow).filter_by(player_key=str(player_key))
                    .order_by(AwardRow.id.desc()).limit(limit).all())
            return [AwardItem(r.match_id, r.award_type, r.player_key, r.player_name, r.detail,
                              r.created_at.isoformat()) for r in rows]
