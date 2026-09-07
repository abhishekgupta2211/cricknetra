"""Roster service — players, teams, and team membership."""

from __future__ import annotations

from app.repositories.roster_repository import PlayerRecord, RosterRepository, TeamRecord
from app.schemas.roster import (
    AddMemberRequest,
    PlayerCreate,
    PlayerDTO,
    PlayerUpdate,
    TeamCreate,
    TeamDTO,
    TeamMemberDTO,
)


class RosterNotFound(Exception):
    """A player or team does not exist."""


class RosterError(Exception):
    """An invalid roster operation."""


class RosterService:
    def __init__(self, repo: RosterRepository) -> None:
        self.repo = repo

    # ----- players -----
    def create_player(self, req: PlayerCreate) -> PlayerDTO:
        rec = self.repo.add_player(req.name, req.phone, req.batting_style, req.bowling_style)
        return self._player_dto(rec)

    def list_players(self) -> list[PlayerDTO]:
        return [self._player_dto(r) for r in self.repo.list_players()]

    def get_player(self, player_id: str) -> PlayerDTO:
        rec = self.repo.get_player(player_id)
        if rec is None:
            raise RosterNotFound(player_id)
        return self._player_dto(rec)

    def update_player(self, player_id: str, req: PlayerUpdate) -> PlayerDTO:
        rec = self.repo.update_player(
            player_id,
            name=req.name,
            phone=req.phone,
            batting_style=req.batting_style,
            bowling_style=req.bowling_style,
        )
        if rec is None:
            raise RosterNotFound(player_id)
        return self._player_dto(rec)

    def delete_player(self, player_id: str) -> None:
        if self.repo.get_player(player_id) is None:
            raise RosterNotFound(player_id)
        self.repo.delete_player(player_id)

    # ----- claim a roster player (the unverified-stub → user-account model) -----
    def claimable(self, mobile: Optional[str]) -> list[PlayerDTO]:
        """Unclaimed roster players whose phone matches this mobile — i.e. stubs a
        team created for this person that they can now claim."""
        if not mobile:
            return []
        return [self._player_dto(r) for r in self.repo.unclaimed_by_phone(mobile)]

    def my_players(self, user_id: str) -> list[PlayerDTO]:
        return [self._player_dto(r) for r in self.repo.players_for_user(user_id)]

    def claim(self, player_id: str, *, user_id: str, mobile: Optional[str],
              is_verified: bool, is_admin: bool) -> PlayerDTO:
        rec = self.repo.get_player(player_id)
        if rec is None:
            raise RosterNotFound(player_id)
        if not is_verified:
            raise RosterError("Verify your mobile number before claiming a profile.")
        if rec.user_id is not None:
            if rec.user_id == str(user_id):
                return self._player_dto(rec)  # already yours — idempotent
            raise RosterError("This profile has already been claimed.")
        if not is_admin and (not rec.phone or rec.phone != mobile):
            raise RosterError("This profile's number doesn't match your account.")
        claimed = self.repo.claim_player(player_id, str(user_id))
        return self._player_dto(claimed)

    # ----- teams -----
    def create_team(self, req: TeamCreate) -> TeamDTO:
        return self._team_dto(self.repo.add_team(req.name, req.location))

    def list_teams(self) -> list[TeamDTO]:
        return [self._team_dto(r) for r in self.repo.list_teams()]

    def get_team(self, team_id: str) -> TeamDTO:
        rec = self.repo.get_team(team_id)
        if rec is None:
            raise RosterNotFound(team_id)
        return self._team_dto(rec)

    def delete_team(self, team_id: str) -> None:
        if self.repo.get_team(team_id) is None:
            raise RosterNotFound(team_id)
        self.repo.delete_team(team_id)

    def add_member(self, team_id: str, req: AddMemberRequest) -> TeamDTO:
        if self.repo.get_team(team_id) is None:
            raise RosterNotFound(team_id)
        player_id = req.player_id
        if player_id is None:
            if not req.name:
                raise RosterError("provide player_id or name")
            player_id = self.repo.add_player(req.name, None, None, None).id
        if not self.repo.add_member(team_id, player_id, req.is_captain):
            raise RosterError("player not found")
        return self.get_team(team_id)

    def remove_member(self, team_id: str, player_id: str) -> TeamDTO:
        if self.repo.get_team(team_id) is None:
            raise RosterNotFound(team_id)
        self.repo.remove_member(team_id, player_id)
        return self.get_team(team_id)

    # ----- mappers -----
    @staticmethod
    def _pcode(player_id: str) -> str:
        """A short, stable roster code derived from the id (e.g. 'P00012')."""
        try:
            return f"P{int(player_id):05d}"
        except (TypeError, ValueError):
            return f"P{player_id}"

    @staticmethod
    def _player_dto(r: PlayerRecord) -> PlayerDTO:
        return PlayerDTO(
            id=r.id, name=r.name, code=RosterService._pcode(r.id), phone=r.phone,
            batting_style=r.batting_style, bowling_style=r.bowling_style,
            claimed_by=r.user_id,
        )

    @staticmethod
    def _team_dto(r: TeamRecord) -> TeamDTO:
        return TeamDTO(
            id=r.id, name=r.name, location=r.location,
            members=[
                TeamMemberDTO(
                    player_id=m.player_id, name=m.name,
                    code=RosterService._pcode(m.player_id), is_captain=m.is_captain,
                )
                for m in r.members
            ],
        )
