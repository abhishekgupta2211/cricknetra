"""Per-tournament team squads.

Records which players are registered to which team **within a tournament**. A
player can be in only one team per tournament (enforced by the service + a unique
DB constraint), but is free across different tournaments.
"""

from __future__ import annotations

from typing import Optional, Protocol


class TournamentSquadRepository(Protocol):
    def team_of(self, tournament_id: str, player_id: str) -> Optional[str]: ...
    def add(self, tournament_id: str, team_id: str, player_id: str) -> None: ...
    def remove(self, tournament_id: str, team_id: str, player_id: str) -> None: ...
    def list_team(self, tournament_id: str, team_id: str) -> list[str]: ...
    def list_tournament(self, tournament_id: str) -> list[tuple[str, str]]: ...  # (team_id, player_id)
    def list_for_player(self, player_id: str) -> list[tuple[str, str]]: ...  # (tournament_id, team_id)
    def delete_tournament(self, tournament_id: str) -> None: ...


class InMemoryTournamentSquadRepository:
    def __init__(self) -> None:
        self._rows: list[tuple[str, str, str]] = []  # (tournament_id, team_id, player_id)

    def team_of(self, tournament_id, player_id) -> Optional[str]:
        for (t, team, p) in self._rows:
            if t == str(tournament_id) and p == str(player_id):
                return team
        return None

    def add(self, tournament_id, team_id, player_id) -> None:
        if self.team_of(tournament_id, player_id) is None:
            self._rows.append((str(tournament_id), str(team_id), str(player_id)))

    def remove(self, tournament_id, team_id, player_id) -> None:
        self._rows = [
            r for r in self._rows
            if not (r[0] == str(tournament_id) and r[1] == str(team_id) and r[2] == str(player_id))
        ]

    def list_team(self, tournament_id, team_id) -> list[str]:
        return [p for (t, team, p) in self._rows if t == str(tournament_id) and team == str(team_id)]

    def list_tournament(self, tournament_id) -> list[tuple[str, str]]:
        return [(team, p) for (t, team, p) in self._rows if t == str(tournament_id)]

    def list_for_player(self, player_id) -> list[tuple[str, str]]:
        """The other direction: every competition this player is registered in.

        Needed because a registration is a fact about the player as much as
        about the tournament, and reading it the long way round — every
        tournament, then every squad in it — does not scale past a season.
        """
        return [(t, team) for (t, team, p) in self._rows if p == str(player_id)]

    def delete_tournament(self, tournament_id) -> None:
        self._rows = [r for r in self._rows if r[0] != str(tournament_id)]
