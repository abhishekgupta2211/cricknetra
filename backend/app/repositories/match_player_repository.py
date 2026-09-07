"""Links between a match and the real players in it (for career stats)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class MatchPlayerLink:
    match_id: str
    player_id: str
    name: str  # the name this player batted/bowled under in the match
    side: str  # 'a' or 'b'
    team_id: Optional[str] = None


class MatchPlayerRepository(Protocol):
    def link(self, links: list[MatchPlayerLink]) -> None: ...
    def for_player(self, player_id: str) -> list[MatchPlayerLink]: ...
    def for_match(self, match_id: str) -> list[MatchPlayerLink]: ...
    def for_team(self, team_id: str) -> list[MatchPlayerLink]: ...
    def delete_for_match(self, match_id: str) -> None: ...


class InMemoryMatchPlayerRepository:
    def __init__(self) -> None:
        self._links: list[MatchPlayerLink] = []

    def link(self, links: list[MatchPlayerLink]) -> None:
        self._links.extend(links)

    def for_player(self, player_id: str) -> list[MatchPlayerLink]:
        return [link for link in self._links if link.player_id == player_id]

    def for_match(self, match_id: str) -> list[MatchPlayerLink]:
        return [link for link in self._links if link.match_id == match_id]

    def for_team(self, team_id: str) -> list[MatchPlayerLink]:
        return [link for link in self._links if link.team_id == team_id]

    def delete_for_match(self, match_id: str) -> None:
        self._links = [link for link in self._links if link.match_id != match_id]
