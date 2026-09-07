"""Roster storage interface + in-memory implementation (players, teams, members)."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Optional, Protocol


@dataclass
class PlayerRecord:
    id: str
    name: str
    phone: Optional[str] = None
    batting_style: Optional[str] = None
    bowling_style: Optional[str] = None
    user_id: Optional[str] = None  # the user account that claimed this player (None = unclaimed)


@dataclass
class MemberRecord:
    player_id: str
    name: str
    is_captain: bool = False


@dataclass
class TeamRecord:
    id: str
    name: str
    location: Optional[str] = None
    members: list[MemberRecord] = field(default_factory=list)


class RosterRepository(Protocol):
    # players
    def add_player(self, name: str, phone: Optional[str], batting_style: Optional[str], bowling_style: Optional[str]) -> PlayerRecord: ...
    def get_player(self, player_id: str) -> Optional[PlayerRecord]: ...
    def list_players(self) -> list[PlayerRecord]: ...
    def update_player(self, player_id: str, name: Optional[str] = None, phone: Optional[str] = None, batting_style: Optional[str] = None, bowling_style: Optional[str] = None) -> Optional[PlayerRecord]: ...
    def delete_player(self, player_id: str) -> None: ...
    def claim_player(self, player_id: str, user_id: str) -> Optional[PlayerRecord]: ...
    def players_for_user(self, user_id: str) -> list[PlayerRecord]: ...
    def unclaimed_by_phone(self, phone: str) -> list[PlayerRecord]: ...
    # teams
    def add_team(self, name: str, location: Optional[str]) -> TeamRecord: ...
    def get_team(self, team_id: str) -> Optional[TeamRecord]: ...
    def list_teams(self) -> list[TeamRecord]: ...
    def delete_team(self, team_id: str) -> None: ...
    def add_member(self, team_id: str, player_id: str, is_captain: bool) -> bool: ...
    def remove_member(self, team_id: str, player_id: str) -> None: ...


class InMemoryRosterRepository:
    def __init__(self) -> None:
        self._players: dict[str, PlayerRecord] = {}
        self._teams: dict[str, TeamRecord] = {}
        self._pids = count(1)
        self._tids = count(1)

    # players
    def add_player(self, name, phone, batting_style, bowling_style) -> PlayerRecord:
        pid = str(next(self._pids))
        rec = PlayerRecord(pid, name, phone, batting_style, bowling_style)
        self._players[pid] = rec
        return rec

    def get_player(self, player_id) -> Optional[PlayerRecord]:
        return self._players.get(player_id)

    def list_players(self) -> list[PlayerRecord]:
        return list(self._players.values())

    def update_player(self, player_id, name=None, phone=None, batting_style=None, bowling_style=None) -> Optional[PlayerRecord]:
        rec = self._players.get(player_id)
        if rec is None:
            return None
        if name is not None:
            rec.name = name
            for team in self._teams.values():
                for m in team.members:
                    if m.player_id == player_id:
                        m.name = name
        if phone is not None:
            rec.phone = phone
        if batting_style is not None:
            rec.batting_style = batting_style
        if bowling_style is not None:
            rec.bowling_style = bowling_style
        return rec

    def delete_player(self, player_id) -> None:
        self._players.pop(player_id, None)
        for team in self._teams.values():
            team.members = [m for m in team.members if m.player_id != player_id]

    def claim_player(self, player_id, user_id) -> Optional[PlayerRecord]:
        rec = self._players.get(player_id)
        if rec is not None:
            rec.user_id = user_id
        return rec

    def players_for_user(self, user_id) -> list[PlayerRecord]:
        return [r for r in self._players.values() if r.user_id == user_id]

    def unclaimed_by_phone(self, phone) -> list[PlayerRecord]:
        return [r for r in self._players.values() if r.user_id is None and r.phone and r.phone == phone]

    # teams
    def add_team(self, name, location) -> TeamRecord:
        tid = str(next(self._tids))
        rec = TeamRecord(tid, name, location, [])
        self._teams[tid] = rec
        return rec

    def get_team(self, team_id) -> Optional[TeamRecord]:
        return self._teams.get(team_id)

    def list_teams(self) -> list[TeamRecord]:
        return list(self._teams.values())

    def delete_team(self, team_id) -> None:
        self._teams.pop(team_id, None)

    def add_member(self, team_id, player_id, is_captain) -> bool:
        team = self._teams.get(team_id)
        player = self._players.get(player_id)
        if team is None or player is None:
            return False
        if any(m.player_id == player_id for m in team.members):
            return True  # already a member
        team.members.append(MemberRecord(player_id, player.name, is_captain))
        return True

    def remove_member(self, team_id, player_id) -> None:
        team = self._teams.get(team_id)
        if team is not None:
            team.members = [m for m in team.members if m.player_id != player_id]
