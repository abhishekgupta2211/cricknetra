"""SQL-backed match repository (event-sourced persistence).

We store the match setup + the append-only ball log. Loading a match rebuilds the
`MatchEngine` by replaying its events — the same mechanism the engine uses for
UNDO — so the database never stores derived state that could drift.

`save()` diffs the engine's in-memory event list against what's persisted:
append new deliveries, truncate on undo. O(changes), not O(match).
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import BallEventRow, MatchRow
from app.domain.engine import MatchEngine
from app.domain.events import BallEvent
from app.domain.rules import MatchRules
from app.repositories.match_repository import MatchSummaryRow


def _rebuild_engine(row: MatchRow, events_by_innings: dict[int, list[BallEvent]]) -> MatchEngine:
    rules = MatchRules.model_validate(row.rules)
    match = MatchEngine(
        rules,
        row.team_a,
        row.team_b,
        list(row.squad_a),
        list(row.squad_b),
        bat_first=row.bat_first,
    )
    match.innings1.load_events(events_by_innings.get(1, []))
    # re-apply a declaration so a declared innings stays complete (and lets the
    # chase start). Innings 1 must be marked before start_second_innings().
    if rules.declared_innings == 1:
        match.innings1.declare()
    if row.second_innings_started:
        match.start_second_innings()
        match.innings2.load_events(events_by_innings.get(2, []))  # type: ignore[union-attr]
        if rules.declared_innings == 2:
            match.innings2.declare()
    # replay any super-over rounds recorded on the rulebook into innings 3, 4, ...
    n = 3
    for rnd in rules.super_over_rounds:
        match._make_super_first(rnd.bat_first)
        match.super_overs[-1].first.load_events(events_by_innings.get(n, []))
        if rnd.second_started:
            match._make_super_second()
            match.super_overs[-1].second.load_events(events_by_innings.get(n + 1, []))  # type: ignore[union-attr]
        n += 2
    if row.pending_bowler:
        match.current.set_bowler(row.pending_bowler)
    return match


class SqlMatchRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    @staticmethod
    def _to_int(match_id: str) -> Optional[int]:
        try:
            return int(match_id)
        except (TypeError, ValueError):
            return None

    def add(self, match: MatchEngine) -> str:
        with self._sf() as s:
            row = MatchRow(
                team_a=match.team_a,
                team_b=match.team_b,
                bat_first=match.bat_first,
                format_id=match.rules.format_id,
                rules=match.rules.model_dump(mode="json"),
                squad_a=list(match.squad_a),
                squad_b=list(match.squad_b),
                second_innings_started=match.innings2 is not None,
                pending_bowler=match.current.staged_bowler,
                result=match.result,
                status="complete" if match.result else "in_progress",
            )
            s.add(row)
            s.flush()  # assign row.id
            for innings_number, inn in self._innings(match):
                for seq, ev in enumerate(inn.events):
                    s.add(self._event_row(row.id, innings_number, seq, ev))
            s.commit()
            return str(row.id)

    def get(self, match_id: str) -> Optional[MatchEngine]:
        mid = self._to_int(match_id)
        if mid is None:
            return None
        with self._sf() as s:
            row = s.get(MatchRow, mid)
            if row is None:
                return None
            ev_rows = (
                s.query(BallEventRow)
                .filter_by(match_id=mid)
                .order_by(BallEventRow.innings_number, BallEventRow.seq)
                .all()
            )
            by_innings: dict[int, list[BallEvent]] = {}
            for er in ev_rows:
                by_innings.setdefault(er.innings_number, []).append(
                    BallEvent.model_validate(er.payload)
                )
            return _rebuild_engine(row, by_innings)

    def save(self, match_id: str, match: MatchEngine) -> None:
        mid = self._to_int(match_id)
        if mid is None:
            return
        with self._sf() as s:
            row = s.get(MatchRow, mid)
            if row is None:
                return
            row.second_innings_started = match.innings2 is not None
            row.pending_bowler = match.current.staged_bowler
            row.result = match.result
            row.status = "complete" if match.result else "in_progress"
            # rules can change mid-match (a DLS revised target/overs lives on the
            # match's own rulebook), so re-persist it in the JSON column.
            row.rules = match.rules.model_dump(mode="json")

            for innings_number, inn in self._innings(match):
                persisted = (
                    s.query(func.count(BallEventRow.id))
                    .filter_by(match_id=mid, innings_number=innings_number)
                    .scalar()
                    or 0
                )
                current = len(inn.events)
                if current > persisted:
                    # Only scoring grows the log, and it always appends — keep the
                    # cheap incremental write for the hot path.
                    for seq in range(persisted, current):
                        s.add(self._event_row(mid, innings_number, seq, inn.events[seq]))
                elif persisted:
                    # current <= persisted means a *correction*: an edit (same length,
                    # changed payload), an undo (tail trimmed), or a mid-over delete
                    # (the log re-indexes). Find the first delivery whose stored payload
                    # no longer matches and rewrite that suffix; an unchanged log (e.g. a
                    # set-bowler or DLS save) diverges nowhere and is left untouched.
                    existing = (
                        s.query(BallEventRow)
                        .filter_by(match_id=mid, innings_number=innings_number)
                        .order_by(BallEventRow.seq)
                        .all()
                    )
                    diverge = current
                    for i in range(current):
                        if existing[i].payload != inn.events[i].model_dump(mode="json"):
                            diverge = i
                            break
                    if diverge < len(existing):  # stale tail (edited/deleted) → rewrite it
                        for stale in existing[diverge:]:
                            s.delete(stale)
                        s.flush()  # drop the old rows before re-inserting those seq slots
                        for seq in range(diverge, current):
                            s.add(self._event_row(mid, innings_number, seq, inn.events[seq]))
            s.commit()

    def summaries(self) -> list[MatchSummaryRow]:
        with self._sf() as s:
            rows = s.query(MatchRow).order_by(MatchRow.id).all()
            return [
                MatchSummaryRow(
                    id=str(r.id),
                    team_a=r.team_a,
                    team_b=r.team_b,
                    status=r.status,
                    result=r.result,
                    created_at=r.created_at,
                )
                for r in rows
            ]

    def delete(self, match_id: str) -> None:
        mid = self._to_int(match_id)
        if mid is None:
            return
        with self._sf() as s:
            s.query(BallEventRow).filter_by(match_id=mid).delete(synchronize_session=False)
            row = s.get(MatchRow, mid)
            if row is not None:
                s.delete(row)
            s.commit()

    def get_stream_url(self, match_id: str) -> Optional[str]:
        mid = self._to_int(match_id)
        if mid is None:
            return None
        with self._sf() as s:
            return s.query(MatchRow.stream_url).filter_by(id=mid).scalar()

    def set_stream_url(self, match_id: str, url: Optional[str]) -> None:
        mid = self._to_int(match_id)
        if mid is None:
            return
        with self._sf() as s:
            row = s.get(MatchRow, mid)
            if row is None:
                return
            row.stream_url = url or None
            s.commit()

    def get_clips(self, match_id: str) -> list:
        mid = self._to_int(match_id)
        if mid is None:
            return []
        with self._sf() as s:
            return list(s.query(MatchRow.clips).filter_by(id=mid).scalar() or [])

    def set_clips(self, match_id: str, clips: list) -> None:
        mid = self._to_int(match_id)
        if mid is None:
            return
        with self._sf() as s:
            row = s.get(MatchRow, mid)
            if row is None:
                return
            row.clips = list(clips) or None
            s.commit()

    def get_meta(self, match_id: str) -> dict:
        mid = self._to_int(match_id)
        if mid is None:
            return {}
        with self._sf() as s:
            return dict(s.query(MatchRow.meta).filter_by(id=mid).scalar() or {})

    def set_meta(self, match_id: str, meta: dict) -> None:
        mid = self._to_int(match_id)
        if mid is None:
            return
        with self._sf() as s:
            row = s.get(MatchRow, mid)
            if row is None:
                return
            row.meta = dict(meta) or None
            s.commit()

    def data_version(self) -> str:
        """Cheap cross-process fingerprint: counts/max-ids of ball_events + matches
        plus the completed-match count. Changes on a new ball, an undo (count drops),
        a match create/delete, and a match completing — the mutations that move stats.
        Indexed aggregates, so it's far cheaper than replaying every match."""
        with self._sf() as s:
            ec, emax = s.query(
                func.count(BallEventRow.id), func.coalesce(func.max(BallEventRow.id), 0)
            ).one()
            mc, mmax, done = s.query(
                func.count(MatchRow.id),
                func.coalesce(func.max(MatchRow.id), 0),
                func.count(MatchRow.result),
            ).one()
        return f"{ec}.{emax}.{mc}.{mmax}.{done}"

    # ---- helpers ----
    @staticmethod
    def _innings(match: MatchEngine):
        yield 1, match.innings1
        if match.innings2 is not None:
            yield 2, match.innings2
        # super overs occupy stable slots: round i -> first=3+2i, second=4+2i
        n = 3
        for so in match.super_overs:
            yield n, so.first
            if so.second is not None:
                yield n + 1, so.second
            n += 2

    @staticmethod
    def _event_row(match_id: int, innings_number: int, seq: int, ev: BallEvent) -> BallEventRow:
        return BallEventRow(
            match_id=match_id,
            innings_number=innings_number,
            seq=seq,
            payload=ev.model_dump(mode="json"),
        )
