"""Member activity — records that aren't ownership (matches umpired / commentated).

`record` is idempotent per (user, kind, resource); `count` tallies a member's
records of a kind. Owned-resource counts (matches scored, teams, tournaments) come
from the ownership repository instead.
"""

from __future__ import annotations

from typing import Protocol


class MemberActivityRepository(Protocol):
    def record(self, user_id: str, kind: str, resource_id: str) -> None: ...
    def count(self, user_id: str, kind: str) -> int: ...


class InMemoryMemberActivityRepository:
    def __init__(self) -> None:
        self._acts: set[tuple[str, str, str]] = set()

    def record(self, user_id, kind, resource_id) -> None:
        self._acts.add((str(user_id), kind, str(resource_id)))

    def count(self, user_id, kind) -> int:
        return sum(1 for (u, k, _r) in self._acts if u == str(user_id) and k == kind)
