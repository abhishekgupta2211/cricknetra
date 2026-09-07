"""Match awards store — Man of the Match / best batter / best bowler, one row per
(match, award_type). Persisted so a player's profile can show honours and so each
winner is notified exactly once."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AwardItem:
    match_id: str
    award_type: str          # mom | best_bat | best_bowl
    player_key: str          # the "player" follow entity_id
    player_name: str
    detail: str = ""         # e.g. "82 (45)" / "5/24"
    when: str = ""


class AwardRepository(Protocol):
    def add_award(self, match_id: str, award_type: str, player_key: str, player_name: str,
                  detail: str = "") -> None: ...            # upsert by (match_id, award_type)
    def awards_for_match(self, match_id: str) -> list[AwardItem]: ...
    def awards_for_player(self, player_key: str, limit: int = 50) -> list[AwardItem]: ...
    def delete_for_match(self, match_id: str) -> None: ...  # the match is gone; so are its honours


class InMemoryAwardRepository:
    def __init__(self) -> None:
        self._rows: list[dict] = []

    def add_award(self, match_id, award_type, player_key, player_name, detail="") -> None:
        for r in self._rows:                                # upsert: one award of a kind per match
            if r["match_id"] == str(match_id) and r["award_type"] == award_type:
                r.update(player_key=str(player_key), player_name=player_name, detail=detail)
                return
        self._rows.append({
            "match_id": str(match_id), "award_type": award_type, "player_key": str(player_key),
            "player_name": player_name, "detail": detail, "when": _now(),
        })

    def awards_for_match(self, match_id) -> list[AwardItem]:
        return [AwardItem(**r) for r in self._rows if r["match_id"] == str(match_id)]

    def awards_for_player(self, player_key, limit=50) -> list[AwardItem]:
        rows = [r for r in reversed(self._rows) if r["player_key"] == str(player_key)][:limit]
        return [AwardItem(**r) for r in rows]

    def delete_for_match(self, match_id) -> None:
        """Drop a deleted match's honours. An award shows on a player's profile
        as a Man of the Match in a game that, once deleted, has no scorecard to
        back it up."""
        self._rows = [r for r in self._rows if r["match_id"] != str(match_id)]
