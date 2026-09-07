"""\"Looking For\" board service — create / browse / close / delete posts."""

from __future__ import annotations

from typing import Optional

from app.repositories.looking_for_repository import LookingForItem, LookingForRepository
from app.repositories.user_repository import UserRecord
from app.schemas.looking_for import LookingForDTO

_KINDS = {"player", "team", "match"}


class LookingForError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _dto(item: LookingForItem, viewer_id: Optional[str]) -> LookingForDTO:
    return LookingForDTO(
        id=item.id, author_id=item.author_id, author_name=item.author_name,
        kind=item.kind, text=item.text, location=item.location, role=item.role,
        status=item.status, when=item.when,
        mine=(viewer_id is not None and str(item.author_id) == str(viewer_id)),
    )


class LookingForService:
    def __init__(self, repo: LookingForRepository) -> None:
        self.repo = repo

    def create(self, author: UserRecord, kind: str, text: str,
               location: Optional[str], role: Optional[str]) -> LookingForDTO:
        if kind not in _KINDS:
            raise LookingForError("kind must be one of: player, team, match")
        text = (text or "").strip()
        if not text:
            raise LookingForError("Post text can't be empty")
        author_name = author.full_name or author.username
        item = self.repo.create(author.id, author_name, kind, text,
                                (location or "").strip() or None, (role or "").strip() or None)
        return _dto(item, author.id)

    def list(self, viewer_id: Optional[str], kind: Optional[str] = None,
             location: Optional[str] = None) -> list[LookingForDTO]:
        if kind and kind not in _KINDS:
            kind = None
        return [_dto(i, viewer_id) for i in self.repo.list(kind=kind, location=location)]

    def mine(self, author_id: str) -> list[LookingForDTO]:
        return [_dto(i, author_id) for i in self.repo.mine(author_id)]

    def close(self, post_id: str, user: UserRecord, is_admin: bool = False) -> None:
        if not self.repo.set_status(post_id, user.id, "closed", is_admin=is_admin):
            raise LookingForError("Post not found or not yours", 404)

    def delete(self, post_id: str, user: UserRecord, is_admin: bool = False) -> None:
        if not self.repo.delete(post_id, user.id, is_admin=is_admin):
            raise LookingForError("Post not found or not yours", 404)
