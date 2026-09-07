"""Storage for saved rulebooks. In-memory + SQL, same Protocol as everything else."""

from __future__ import annotations

from itertools import count
from typing import Optional, Protocol

from app.domain.rules import MatchRules


class RuleTemplateRepository(Protocol):
    def add(self, rules: MatchRules) -> str: ...
    def get(self, template_id: str) -> Optional[MatchRules]: ...
    def list(self) -> list[tuple[str, MatchRules]]: ...
    def delete(self, template_id: str) -> None: ...


class InMemoryRuleTemplateRepository:
    def __init__(self) -> None:
        self._store: dict[str, MatchRules] = {}
        self._ids = count(1)

    def add(self, rules: MatchRules) -> str:
        template_id = str(next(self._ids))
        self._store[template_id] = rules
        return template_id

    def get(self, template_id: str) -> Optional[MatchRules]:
        return self._store.get(template_id)

    def list(self) -> list[tuple[str, MatchRules]]:
        return list(self._store.items())

    def delete(self, template_id: str) -> None:
        self._store.pop(template_id, None)
