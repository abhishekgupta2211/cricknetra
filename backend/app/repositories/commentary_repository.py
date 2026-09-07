"""Match commentary — live text lines posted by commentators."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CommentaryItem:
    id: str
    author_id: str
    author_name: str
    text: str
    when: str


class CommentaryRepository(Protocol):
    def add(self, match_id: str, author_id: str, author_name: str, text: str) -> CommentaryItem: ...
    def list_for(self, match_id: str, limit: int = 100) -> list[CommentaryItem]: ...
    def delete_for_match(self, match_id: str) -> None: ...  # the match is gone; so is its commentary


class InMemoryCommentaryRepository:
    def __init__(self) -> None:
        self._items: list[dict] = []
        self._seq = 0

    def add(self, match_id, author_id, author_name, text) -> CommentaryItem:
        self._seq += 1
        row = {
            "id": str(self._seq), "match_id": str(match_id), "author_id": str(author_id),
            "author_name": author_name, "text": text, "when": _now(),
        }
        self._items.append(row)
        return CommentaryItem(row["id"], row["author_id"], row["author_name"], row["text"], row["when"])

    def list_for(self, match_id, limit=100) -> list[CommentaryItem]:
        items = [r for r in reversed(self._items) if r["match_id"] == str(match_id)][:limit]
        return [CommentaryItem(r["id"], r["author_id"], r["author_name"], r["text"], r["when"]) for r in items]

    def delete_for_match(self, match_id) -> None:
        """Drop a deleted match's commentary. The lines are published under a
        commentator's name against a scorecard; once the scorecard is gone they
        are attributed to nothing."""
        self._items = [r for r in self._items if r["match_id"] != str(match_id)]
