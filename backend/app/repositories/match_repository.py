"""Match storage.

`MatchRepository` is the interface; implementations:
  - `InMemoryMatchRepository` — process-local, lost on restart.
  - `SqlMatchRepository` — persists the append-only ball log (see sql_*).

Services depend on the Protocol, not the implementation. Mutations are saved via
`save()` (a no-op for the in-memory store, which holds the live object).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from typing import Optional, Protocol

from app.domain.engine import MatchEngine


@dataclass
class MatchSummaryRow:
    """Lightweight match listing — no event replay needed."""

    id: str
    team_a: str
    team_b: str
    status: str
    result: Optional[str]
    created_at: Optional[datetime] = None  # when the match was created (time-scoped boards)


class MatchRepository(Protocol):
    def add(self, match: MatchEngine) -> str: ...
    def get(self, match_id: str) -> Optional[MatchEngine]: ...
    def save(self, match_id: str, match: MatchEngine) -> None: ...
    def summaries(self) -> list[MatchSummaryRow]: ...
    def delete(self, match_id: str) -> None: ...
    def get_stream_url(self, match_id: str) -> Optional[str]:
        """The match's bring-your-own live-stream link, or None."""
        ...
    def set_stream_url(self, match_id: str, url: Optional[str]) -> None:
        """Attach (url) or clear (None) the match's live-stream link."""
        ...
    def get_clips(self, match_id: str) -> list:
        """The match's bring-your-own highlight clips [{id, url, label}], or []."""
        ...
    def set_clips(self, match_id: str, clips: list) -> None:
        """Replace the match's highlight-clip list."""
        ...
    def get_meta(self, match_id: str) -> dict:
        """Display-only match metadata {venue, tournament, match_no, toss_*}, or {}."""
        ...
    def set_meta(self, match_id: str, meta: dict) -> None:
        """Replace the match's display metadata."""
        ...
    def data_version(self) -> str:
        """A cheap token that changes whenever match data changes — lets the stats
        layer cache expensive aggregates and recompute only after a mutation."""
        ...


class InMemoryMatchRepository:
    """Holds live MatchEngine objects; `save` is a no-op (same reference)."""

    def __init__(self) -> None:
        self._store: dict[str, MatchEngine] = {}
        self._created: dict[str, datetime] = {}
        self._streams: dict[str, str] = {}  # match_id -> live-stream link
        self._clips: dict[str, list] = {}   # match_id -> [{id, url, label}]
        self._meta: dict[str, dict] = {}    # match_id -> {venue, toss, tournament, ...}
        self._ids = count(1)
        self._version = 0  # bumped on every mutation; exact for this process

    def add(self, match: MatchEngine) -> str:
        match_id = str(next(self._ids))
        self._store[match_id] = match
        self._created[match_id] = datetime.now(timezone.utc)
        self._version += 1
        return match_id

    def get(self, match_id: str) -> Optional[MatchEngine]:
        return self._store.get(match_id)

    def save(self, match_id: str, match: MatchEngine) -> None:
        # The stored object is the same instance the service mutated.
        self._store[match_id] = match
        self._version += 1

    def summaries(self) -> list[MatchSummaryRow]:
        rows: list[MatchSummaryRow] = []
        for match_id, m in self._store.items():
            rows.append(
                MatchSummaryRow(
                    id=match_id,
                    team_a=m.team_a,
                    team_b=m.team_b,
                    status="complete" if m.result is not None else "in_progress",
                    result=m.result,
                    created_at=self._created.get(match_id),
                )
            )
        return rows

    def delete(self, match_id: str) -> None:
        self._store.pop(match_id, None)
        self._created.pop(match_id, None)
        self._streams.pop(match_id, None)
        self._clips.pop(match_id, None)
        self._meta.pop(match_id, None)
        self._version += 1

    def get_stream_url(self, match_id: str) -> Optional[str]:
        return self._streams.get(match_id)

    def set_stream_url(self, match_id: str, url: Optional[str]) -> None:
        if url:
            self._streams[match_id] = url
        else:
            self._streams.pop(match_id, None)

    def get_clips(self, match_id: str) -> list:
        return list(self._clips.get(match_id, []))

    def set_clips(self, match_id: str, clips: list) -> None:
        if clips:
            self._clips[match_id] = list(clips)
        else:
            self._clips.pop(match_id, None)

    def get_meta(self, match_id: str) -> dict:
        return dict(self._meta.get(match_id, {}))

    def set_meta(self, match_id: str, meta: dict) -> None:
        if meta:
            self._meta[match_id] = dict(meta)
        else:
            self._meta.pop(match_id, None)

    def data_version(self) -> str:
        return str(self._version)
