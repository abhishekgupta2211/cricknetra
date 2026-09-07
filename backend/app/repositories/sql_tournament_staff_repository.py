"""SQL-backed tournament staff — an organizer's umpires and commentators.

The durable twin of
:class:`~app.repositories.tournament_staff_repository.InMemoryTournamentStaffRepository`,
satisfying the same Protocol. Authorization reads it on every request that opens
a competition's working view, so a process-local copy meant an umpire could see
their tournament on one worker and be told they were not on it by the next.

The (tournament, user, role) triple is the identity of a staff entry here just
as it is the dict key there — enforced by a unique index rather than by a data
structure, which is the whole point of moving it into the database.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import TournamentStaffRow
from app.repositories.tournament_staff_repository import StaffRecord


def _to_record(row: TournamentStaffRow) -> StaffRecord:
    return StaffRecord(
        id=str(row.id),
        tournament_id=row.tournament_id,
        user_id=row.user_id,
        staff_role=row.staff_role,
        is_active=bool(row.is_active),
        added_by=row.added_by,
        created_at=row.created_at,
    )


class SqlTournamentStaffRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def add(
        self,
        tournament_id: str,
        user_id: str,
        staff_role: str,
        added_by: Optional[str] = None,
    ) -> StaffRecord:
        """Put somebody on the staff, or reinstate the entry they already have.

        Re-adding somebody who was removed must not create a second, conflicting
        row — ``set_active`` and ``get`` would then disagree about whether they
        are on the staff depending on which row they found first.
        """
        tid, uid = str(tournament_id), str(user_id)
        with self._sf() as s:
            row = (
                s.query(TournamentStaffRow)
                .filter_by(tournament_id=tid, user_id=uid, staff_role=staff_role)
                .first()
            )
            if row is not None:
                row.is_active = True
                s.commit()
                s.refresh(row)
                return _to_record(row)
            row = TournamentStaffRow(
                tournament_id=tid,
                user_id=uid,
                staff_role=staff_role,
                added_by=str(added_by) if added_by else None,
                is_active=True,
            )
            s.add(row)
            try:
                s.commit()
            except IntegrityError:
                # Two organizers' clicks raced; the row that landed is the entry.
                s.rollback()
                row = (
                    s.query(TournamentStaffRow)
                    .filter_by(tournament_id=tid, user_id=uid, staff_role=staff_role)
                    .first()
                )
                if row is None:  # pragma: no cover - the constraint says this cannot happen
                    raise
                return _to_record(row)
            s.refresh(row)
            return _to_record(row)

    def list_for_tournament(
        self, tournament_id: str, staff_role: Optional[str] = None
    ) -> list[StaffRecord]:
        """Everybody on this competition's staff, stood-down entries included —
        an organizer who suspended somebody still has to be able to see them."""
        with self._sf() as s:
            q = s.query(TournamentStaffRow).filter_by(tournament_id=str(tournament_id))
            if staff_role is not None:
                q = q.filter_by(staff_role=staff_role)
            return [_to_record(r) for r in q.order_by(TournamentStaffRow.id).all()]

    def list_for_user(
        self, user_id: str, staff_role: Optional[str] = None
    ) -> list[StaffRecord]:
        """The competitions this person currently works on. Active only: this
        answers "what may I open", and a suspended entry may not."""
        with self._sf() as s:
            q = s.query(TournamentStaffRow).filter_by(user_id=str(user_id), is_active=True)
            if staff_role is not None:
                q = q.filter_by(staff_role=staff_role)
            return [_to_record(r) for r in q.order_by(TournamentStaffRow.id).all()]

    def get(self, tournament_id: str, user_id: str, staff_role: str) -> Optional[StaffRecord]:
        with self._sf() as s:
            row = (
                s.query(TournamentStaffRow)
                .filter_by(
                    tournament_id=str(tournament_id), user_id=str(user_id), staff_role=staff_role
                )
                .first()
            )
            return _to_record(row) if row else None

    def set_active(
        self, tournament_id: str, user_id: str, staff_role: str, active: bool
    ) -> Optional[StaffRecord]:
        with self._sf() as s:
            row = (
                s.query(TournamentStaffRow)
                .filter_by(
                    tournament_id=str(tournament_id), user_id=str(user_id), staff_role=staff_role
                )
                .first()
            )
            if row is None:
                return None
            row.is_active = bool(active)
            s.commit()
            s.refresh(row)
            return _to_record(row)

    def remove(self, tournament_id: str, user_id: str, staff_role: str) -> None:
        with self._sf() as s:
            s.query(TournamentStaffRow).filter_by(
                tournament_id=str(tournament_id), user_id=str(user_id), staff_role=staff_role
            ).delete()
            s.commit()

    def remove_tournament(self, tournament_id: str) -> None:
        """Drop the whole staff of a competition that no longer exists, so no
        entry is left advertising a job on a tournament nobody can open."""
        with self._sf() as s:
            s.query(TournamentStaffRow).filter_by(tournament_id=str(tournament_id)).delete()
            s.commit()
