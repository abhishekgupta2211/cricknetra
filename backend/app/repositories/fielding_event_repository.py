"""Per-match fielding-event log — dropped catches, runs saved, misfields.

These aren't deliveries, so they live outside the ball log. Keyed by the fielder's
*scoring name* within a match (same way catches/run-outs are credited), so career
"drops" / "runs saved" can be folded into a player's fielding stats.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FieldingEventItem:
    id: str
    match_id: str
    innings: int
    fielder: str
    kind: str  # drop | save | misfield
    runs: int
    bowler: Optional[str]
    batter: Optional[str]
    note: Optional[str]
    over_ball: Optional[str]
    when: str


class FieldingEventRepository(Protocol):
    def add(self, match_id: str, innings: int, fielder: str, kind: str, runs: int,
            bowler: Optional[str], batter: Optional[str], note: Optional[str],
            over_ball: Optional[str]) -> FieldingEventItem: ...
    def for_match(self, match_id: str) -> list[FieldingEventItem]: ...
    def delete(self, event_id: str, match_id: str) -> bool: ...
    def delete_for_match(self, match_id: str) -> None: ...  # the match is gone; so are its events


class InMemoryFieldingEventRepository:
    def __init__(self) -> None:
        self._evts: list[dict] = []
        self._seq = 0

    def _item(self, e: dict) -> FieldingEventItem:
        return FieldingEventItem(
            e["id"], e["match_id"], e["innings"], e["fielder"], e["kind"], e["runs"],
            e["bowler"], e["batter"], e["note"], e["over_ball"], e["when"],
        )

    def add(self, match_id, innings, fielder, kind, runs, bowler, batter, note, over_ball) -> FieldingEventItem:
        self._seq += 1
        e = {
            "id": str(self._seq), "match_id": str(match_id), "innings": int(innings or 1),
            "fielder": fielder, "kind": kind, "runs": int(runs or 0),
            "bowler": bowler or None, "batter": batter or None, "note": note or None,
            "over_ball": over_ball or None, "when": _now(),
        }
        self._evts.append(e)
        return self._item(e)

    def for_match(self, match_id) -> list[FieldingEventItem]:
        return [self._item(e) for e in self._evts if e["match_id"] == str(match_id)]

    def delete(self, event_id, match_id) -> bool:
        before = len(self._evts)
        self._evts = [
            e for e in self._evts
            if not (e["id"] == str(event_id) and e["match_id"] == str(match_id))
        ]
        return len(self._evts) < before

    def delete_for_match(self, match_id) -> None:
        """Drop a deleted match's fielding log. These feed a player's fielding
        record, so a row surviving its match keeps counting a dropped catch in
        a game nobody can open."""
        self._evts = [e for e in self._evts if e["match_id"] != str(match_id)]
