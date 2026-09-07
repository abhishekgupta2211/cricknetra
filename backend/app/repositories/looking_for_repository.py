"""The "Looking For" board — players seeking teams, teams seeking players, or
either seeking a match (in-memory + SQL impls)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LookingForItem:
    id: str
    author_id: str
    author_name: str
    kind: str  # player | team | match
    text: str
    location: Optional[str]
    role: Optional[str]
    status: str  # open | closed
    when: str


class LookingForRepository(Protocol):
    def create(self, author_id: str, author_name: str, kind: str, text: str,
               location: Optional[str], role: Optional[str]) -> LookingForItem: ...
    def list(self, kind: Optional[str] = None, location: Optional[str] = None,
             limit: int = 100) -> list[LookingForItem]: ...
    def get(self, post_id: str) -> Optional[LookingForItem]: ...
    def mine(self, author_id: str) -> list[LookingForItem]: ...
    def set_status(self, post_id: str, author_id: str, status: str, is_admin: bool = False) -> bool: ...
    def delete(self, post_id: str, author_id: str, is_admin: bool = False) -> bool: ...


class InMemoryLookingForRepository:
    def __init__(self) -> None:
        self._posts: list[dict] = []
        self._seq = 0

    def _item(self, p: dict) -> LookingForItem:
        return LookingForItem(p["id"], p["author_id"], p["author_name"], p["kind"],
                              p["text"], p["location"], p["role"], p["status"], p["when"])

    def create(self, author_id, author_name, kind, text, location, role) -> LookingForItem:
        self._seq += 1
        p = {
            "id": str(self._seq), "author_id": str(author_id), "author_name": author_name,
            "kind": kind, "text": text, "location": location or None, "role": role or None,
            "status": "open", "when": _now(),
        }
        self._posts.append(p)
        return self._item(p)

    def list(self, kind=None, location=None, limit=100) -> list[LookingForItem]:
        loc = (location or "").strip().lower()
        out = []
        for p in reversed(self._posts):  # newest first
            if p["status"] != "open":
                continue
            if kind and p["kind"] != kind:
                continue
            if loc and loc not in (p["location"] or "").lower():
                continue
            out.append(self._item(p))
            if len(out) >= limit:
                break
        return out

    def get(self, post_id) -> Optional[LookingForItem]:
        p = next((x for x in self._posts if x["id"] == str(post_id)), None)
        return self._item(p) if p else None

    def mine(self, author_id) -> list[LookingForItem]:
        return [self._item(p) for p in reversed(self._posts) if p["author_id"] == str(author_id)]

    def set_status(self, post_id, author_id, status, is_admin=False) -> bool:
        for p in self._posts:
            if p["id"] == str(post_id) and (is_admin or p["author_id"] == str(author_id)):
                p["status"] = status
                return True
        return False

    def delete(self, post_id, author_id, is_admin=False) -> bool:
        before = len(self._posts)
        self._posts = [
            p for p in self._posts
            if not (p["id"] == str(post_id) and (is_admin or p["author_id"] == str(author_id)))
        ]
        return len(self._posts) < before
