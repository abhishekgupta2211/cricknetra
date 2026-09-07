"""Match commentary — post and list live commentary lines."""

from __future__ import annotations

from app.repositories.commentary_repository import CommentaryItem, CommentaryRepository


class CommentaryError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class CommentaryService:
    def __init__(self, repo: CommentaryRepository) -> None:
        self.repo = repo

    def add(self, match_id: str, author_id: str, author_name: str, text: str) -> CommentaryItem:
        text = (text or "").strip()
        if not text:
            raise CommentaryError("Commentary can't be empty")
        return self.repo.add(match_id, author_id, author_name, text[:280])

    def list(self, match_id: str, limit: int = 100) -> list[CommentaryItem]:
        return self.repo.list_for(match_id, limit)

    def delete_for_match(self, match_id: str) -> None:
        """Drop every line on a match that has been deleted, so no commentary
        outlives the scorecard it was written against."""
        self.repo.delete_for_match(match_id)
