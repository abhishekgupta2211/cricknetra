"""Rule-template service — save / list / fetch / delete named rulebooks."""

from __future__ import annotations

from app.domain.rules import MatchRules
from app.repositories.rule_template_repository import RuleTemplateRepository
from app.schemas.rule_templates import RuleTemplateDTO


class RuleTemplateNotFound(Exception):
    """No rule template exists for the given id."""


class RuleTemplateService:
    def __init__(self, repo: RuleTemplateRepository) -> None:
        self.repo = repo

    def create(self, rules: MatchRules) -> RuleTemplateDTO:
        template_id = self.repo.add(rules)
        return RuleTemplateDTO(id=template_id, name=rules.name, rules=rules)

    def list(self) -> list[RuleTemplateDTO]:
        return [
            RuleTemplateDTO(id=tid, name=rules.name, rules=rules)
            for tid, rules in self.repo.list()
        ]

    def get(self, template_id: str) -> RuleTemplateDTO:
        rules = self.repo.get(template_id)
        if rules is None:
            raise RuleTemplateNotFound(template_id)
        return RuleTemplateDTO(id=template_id, name=rules.name, rules=rules)

    def delete(self, template_id: str) -> None:
        if self.repo.get(template_id) is None:
            raise RuleTemplateNotFound(template_id)
        self.repo.delete(template_id)
