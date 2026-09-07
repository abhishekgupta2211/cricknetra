"""SQL-backed per-match fielding-event log."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import FieldingEventRow
from app.repositories.fielding_event_repository import FieldingEventItem


def _item(r: FieldingEventRow) -> FieldingEventItem:
    return FieldingEventItem(
        str(r.id), r.match_id, r.innings, r.fielder, r.kind, r.runs,
        r.bowler, r.batter, r.note, r.over_ball, r.created_at.isoformat(),
    )


class SqlFieldingEventRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def add(self, match_id, innings, fielder, kind, runs, bowler, batter, note, over_ball) -> FieldingEventItem:
        with self._sf() as s:
            row = FieldingEventRow(
                match_id=str(match_id), innings=int(innings or 1), fielder=fielder, kind=kind,
                runs=int(runs or 0), bowler=bowler or None, batter=batter or None,
                note=note or None, over_ball=over_ball or None,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return _item(row)

    def for_match(self, match_id) -> list[FieldingEventItem]:
        with self._sf() as s:
            rows = (
                s.query(FieldingEventRow).filter_by(match_id=str(match_id))
                .order_by(FieldingEventRow.id.asc()).all()
            )
            return [_item(r) for r in rows]

    def delete_for_match(self, match_id) -> None:
        """Drop a deleted match's fielding log — these feed a player's fielding
        record, so a surviving row keeps counting against a match that is gone."""
        with self._sf() as s:
            s.query(FieldingEventRow).filter_by(match_id=str(match_id)).delete()
            s.commit()

    def delete(self, event_id, match_id) -> bool:
        try:
            eid = int(event_id)
        except (TypeError, ValueError):
            return False
        with self._sf() as s:
            n = s.query(FieldingEventRow).filter_by(id=eid, match_id=str(match_id)).delete()
            s.commit()
            return bool(n)
