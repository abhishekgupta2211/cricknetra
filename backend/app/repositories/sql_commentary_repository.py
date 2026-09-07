"""SQL-backed match commentary."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import CommentaryRow
from app.repositories.commentary_repository import CommentaryItem


def _to_item(row: CommentaryRow) -> CommentaryItem:
    return CommentaryItem(
        id=str(row.id), author_id=row.author_id, author_name=row.author_name,
        text=row.text, when=(row.created_at.isoformat() if row.created_at else ""),
    )


class SqlCommentaryRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def add(self, match_id, author_id, author_name, text) -> CommentaryItem:
        with self._sf() as s:
            row = CommentaryRow(
                match_id=str(match_id), author_id=str(author_id),
                author_name=author_name, text=text,
            )
            s.add(row)
            s.flush()
            s.refresh(row)
            item = _to_item(row)
            s.commit()
            return item

    def delete_for_match(self, match_id) -> None:
        """Drop a deleted match's commentary — lines published against a
        scorecard that no longer exists."""
        with self._sf() as s:
            s.query(CommentaryRow).filter_by(match_id=str(match_id)).delete()
            s.commit()

    def list_for(self, match_id, limit=100) -> list[CommentaryItem]:
        with self._sf() as s:
            rows = (
                s.query(CommentaryRow)
                .filter_by(match_id=str(match_id))
                .order_by(CommentaryRow.id.desc())
                .limit(limit)
                .all()
            )
            return [_to_item(r) for r in rows]
