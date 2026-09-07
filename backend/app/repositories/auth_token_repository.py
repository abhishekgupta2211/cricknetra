"""Short-lived single-use tokens — mobile verification codes + password resets.

Only the hash is stored. A token is "valid" if it's unused and unexpired.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuthTokenItem:
    id: str
    user_id: str
    kind: str
    token_hash: str
    expires_at: datetime
    used_at: Optional[datetime]


class AuthTokenRepository(Protocol):
    def add(self, user_id: str, kind: str, token_hash: str, expires_at: datetime) -> str: ...
    def find_valid(self, kind: str, token_hash: str, user_id: Optional[str] = None) -> Optional[AuthTokenItem]: ...
    def mark_used(self, token_id: str) -> None: ...
    def invalidate(self, user_id: str, kind: str) -> None: ...


class InMemoryAuthTokenRepository:
    def __init__(self) -> None:
        self._rows: list[dict] = []
        self._seq = 0

    def add(self, user_id, kind, token_hash, expires_at) -> str:
        self._seq += 1
        self._rows.append({
            "id": str(self._seq), "user_id": str(user_id), "kind": kind,
            "token_hash": token_hash, "expires_at": expires_at, "used_at": None,
        })
        return str(self._seq)

    def find_valid(self, kind, token_hash, user_id=None) -> Optional[AuthTokenItem]:
        now = _now()
        for r in reversed(self._rows):
            if (r["kind"] == kind and r["token_hash"] == token_hash and r["used_at"] is None
                    and r["expires_at"] > now and (user_id is None or r["user_id"] == str(user_id))):
                return AuthTokenItem(**r)
        return None

    def mark_used(self, token_id) -> None:
        for r in self._rows:
            if r["id"] == str(token_id):
                r["used_at"] = _now()

    def invalidate(self, user_id, kind) -> None:
        now = _now()
        for r in self._rows:
            if r["user_id"] == str(user_id) and r["kind"] == kind and r["used_at"] is None:
                r["used_at"] = now
