"""SQL-backed picture store (one row per kind+owner)."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import PhotoRow
from app.repositories.photo_repository import Photo


class SqlPhotoRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def set_photo(self, kind, owner_id, content_type, data) -> None:
        with self._sf() as s:
            row = s.query(PhotoRow).filter_by(kind=kind, owner_id=str(owner_id)).first()
            if row is not None:
                row.content_type = content_type
                row.data = data
            else:
                s.add(PhotoRow(kind=kind, owner_id=str(owner_id), content_type=content_type, data=data))
            s.commit()

    def get_photo(self, kind, owner_id) -> Photo | None:
        with self._sf() as s:
            row = s.query(PhotoRow).filter_by(kind=kind, owner_id=str(owner_id)).first()
            return Photo(row.content_type, bytes(row.data)) if row is not None else None

    def delete_photo(self, kind, owner_id) -> bool:
        with self._sf() as s:
            n = s.query(PhotoRow).filter_by(kind=kind, owner_id=str(owner_id)).delete()
            s.commit()
            return bool(n)

    def has_photo(self, kind, owner_id) -> bool:
        with self._sf() as s:
            return bool(s.query(PhotoRow.id).filter_by(kind=kind, owner_id=str(owner_id)).first())

    def owners_with_photos(self, kind, owner_ids) -> set[str]:
        ids = [str(x) for x in owner_ids]
        if not ids:
            return set()
        with self._sf() as s:
            rows = s.query(PhotoRow.owner_id).filter(PhotoRow.kind == kind, PhotoRow.owner_id.in_(ids)).all()
            return {r[0] for r in rows}
