"""Custom-rule builder API — save & reuse named rulebooks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_rule_template_service, require_admin, require_capability
from app.core.permissions import Caps
from app.domain.rules import MatchRules
from app.repositories.user_repository import UserRecord
from app.schemas.rule_templates import RuleTemplateDTO
from app.services.rule_template_service import RuleTemplateNotFound, RuleTemplateService

router = APIRouter(prefix="/rule-templates", tags=["rule-templates"])


@router.post("", response_model=RuleTemplateDTO, status_code=201)
def create_template(
    rules: MatchRules,
    svc: RuleTemplateService = Depends(get_rule_template_service),
    _user: UserRecord = Depends(require_capability(Caps.MANAGE_RULES)),
):
    """Save a custom rulebook. The body is a full MatchRules (its `name` is the title)."""
    return svc.create(rules)


@router.get("", response_model=list[RuleTemplateDTO])
def list_templates(svc: RuleTemplateService = Depends(get_rule_template_service)):
    return svc.list()


@router.get("/{template_id}", response_model=RuleTemplateDTO)
def get_template(template_id: str, svc: RuleTemplateService = Depends(get_rule_template_service)):
    try:
        return svc.get(template_id)
    except RuleTemplateNotFound:
        raise HTTPException(status_code=404, detail="rule template not found")


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: str,
    svc: RuleTemplateService = Depends(get_rule_template_service),
    _user: UserRecord = Depends(require_admin),  # deleting is admin-only
):
    try:
        svc.delete(template_id)
    except RuleTemplateNotFound:
        raise HTTPException(status_code=404, detail="rule template not found")

