"""SQL-backed per-match umpire approvals."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import MatchOfficialRow
from app.repositories.match_official_repository import OfficialItem


class SqlMatchOfficialRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def request(self, match_id, umpire_id, umpire_name) -> None:
        with self._sf() as s:
            exists = s.query(MatchOfficialRow.id).filter_by(
                match_id=str(match_id), umpire_id=str(umpire_id)
            ).first()
            if exists:
                return
            s.add(MatchOfficialRow(match_id=str(match_id), umpire_id=str(umpire_id), umpire_name=umpire_name))
            try:
                s.commit()
            except IntegrityError:
                s.rollback()

    def set_status(self, match_id, umpire_id, status) -> bool:
        with self._sf() as s:
            n = s.query(MatchOfficialRow).filter_by(
                match_id=str(match_id), umpire_id=str(umpire_id)
            ).update({"status": status})
            s.commit()
            return bool(n)

    def remove(self, match_id, umpire_id) -> bool:
        with self._sf() as s:
            n = s.query(MatchOfficialRow).filter_by(
                match_id=str(match_id), umpire_id=str(umpire_id)
            ).delete()
            s.commit()
            return bool(n)

    def is_approved(self, match_id, umpire_id) -> bool:
        with self._sf() as s:
            return bool(
                s.query(MatchOfficialRow.id).filter_by(
                    match_id=str(match_id), umpire_id=str(umpire_id), status="approved"
                ).first()
            )

    def status_for(self, match_id, umpire_id) -> str:
        with self._sf() as s:
            row = s.query(MatchOfficialRow.status).filter_by(
                match_id=str(match_id), umpire_id=str(umpire_id)
            ).first()
            return row[0] if row else "none"

    def delete_for_match(self, match_id) -> None:
        """Drop every approval on a deleted match — an approval is a standing
        permission to score, and one left behind outlives its match."""
        with self._sf() as s:
            s.query(MatchOfficialRow).filter_by(match_id=str(match_id)).delete()
            s.commit()

    def list_for_match(self, match_id) -> list[OfficialItem]:
        with self._sf() as s:
            rows = (
                s.query(MatchOfficialRow)
                .filter_by(match_id=str(match_id))
                .order_by(MatchOfficialRow.id.asc())
                .all()
            )
            return [OfficialItem(r.umpire_id, r.umpire_name, r.status) for r in rows]
