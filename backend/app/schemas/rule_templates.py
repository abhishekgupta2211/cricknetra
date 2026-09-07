"""Rule-template DTO. The create body is a full `MatchRules` (it carries `name`)."""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.rules import MatchRules


class RuleTemplateDTO(BaseModel):
    id: str
    name: str
    rules: MatchRules
