"""SQL-backed rule-template storage."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import RuleTemplateRow
from app.domain.rules import MatchRules


class SqlRuleTemplateRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    @staticmethod
    def _to_int(template_id: str) -> Optional[int]:
        try:
            return int(template_id)
        except (TypeError, ValueError):
            return None

    def add(self, rules: MatchRules) -> str:
        with self._sf() as s:
            row = RuleTemplateRow(name=rules.name, rules=rules.model_dump(mode="json"))
            s.add(row)
            s.flush()
            template_id = str(row.id)
            s.commit()
            return template_id

    def get(self, template_id: str) -> Optional[MatchRules]:
        tid = self._to_int(template_id)
        if tid is None:
            return None
        with self._sf() as s:
            row = s.get(RuleTemplateRow, tid)
            return MatchRules.model_validate(row.rules) if row else None

    def list(self) -> list[tuple[str, MatchRules]]:
        with self._sf() as s:
            rows = s.query(RuleTemplateRow).order_by(RuleTemplateRow.id).all()
            return [(str(r.id), MatchRules.model_validate(r.rules)) for r in rows]

    def delete(self, template_id: str) -> None:
        tid = self._to_int(template_id)
        if tid is None:
            return
        with self._sf() as s:
            row = s.get(RuleTemplateRow, tid)
            if row is not None:
                s.delete(row)
                s.commit()
