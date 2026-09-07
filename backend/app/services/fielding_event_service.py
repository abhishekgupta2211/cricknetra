"""Fielding-event service — log/list/delete dropped catches, runs saved, misfields."""

from __future__ import annotations

from app.repositories.fielding_event_repository import FieldingEventItem, FieldingEventRepository
from app.schemas.fielding import FieldingEventCreate, FieldingEventDTO

_KINDS = {"drop", "save", "misfield"}


class FieldingEventError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _dto(i: FieldingEventItem) -> FieldingEventDTO:
    return FieldingEventDTO(
        id=i.id, match_id=i.match_id, innings=i.innings, fielder=i.fielder, kind=i.kind,
        runs=i.runs, bowler=i.bowler, batter=i.batter, note=i.note,
        over_ball=i.over_ball, when=i.when,
    )


class FieldingEventService:
    def __init__(self, repo: FieldingEventRepository) -> None:
        self.repo = repo

    def add(self, match_id: str, req: FieldingEventCreate) -> FieldingEventDTO:
        if req.kind not in _KINDS:
            raise FieldingEventError("kind must be one of: drop, save, misfield")
        fielder = (req.fielder or "").strip()
        if not fielder:
            raise FieldingEventError("a fielder is required")
        item = self.repo.add(
            match_id, req.innings, fielder, req.kind, req.runs,
            req.bowler, req.batter, req.note, req.over_ball,
        )
        return _dto(item)

    def list(self, match_id: str) -> list[FieldingEventDTO]:
        return [_dto(i) for i in self.repo.for_match(match_id)]

    def delete(self, match_id: str, event_id: str) -> None:
        if not self.repo.delete(event_id, match_id):
            raise FieldingEventError("fielding event not found", 404)

    def delete_for_match(self, match_id: str) -> None:
        """Drop the whole log for a match that has been deleted — these events
        feed a player's fielding record and must not outlive their match."""
        self.repo.delete_for_match(match_id)
