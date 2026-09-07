"""Admin: areas, organizations and organizers.

Only an admin reaches any of this. Creating an organizer is how the system gets
more than one person able to run competitions, and it is deliberately a
promotion of an account that already exists rather than a second way to create
accounts.

Every handler takes the caller from ``Depends(require_admin)`` and hands *that*
record to the service. A body may say which user to act on; it never says who is
asking, and it never says what role the asker holds.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_audit_service, get_org_service, require_admin
from app.repositories.user_repository import UserRecord
from app.schemas.org import (
    AreaCreate,
    AreaDTO,
    AuditDTO,
    OrganizationCreate,
    OrganizationDTO,
    OrganizerCreate,
    OrganizerDTO,
    OrganizerUpdate,
    RoleAssign,
)
from app.services.audit_service import AuditService
from app.services.org_service import OrgError, OrgService

router = APIRouter(prefix="/admin", tags=["admin-organizers"])


# ----------------------------------------------------------------------- areas

@router.get("/areas", response_model=list[AreaDTO])
def list_areas(
    _admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    return svc.list_areas()


@router.post("/areas", response_model=AreaDTO, status_code=201)
def create_area(
    req: AreaCreate,
    _admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    try:
        return svc.create_area(req)
    except OrgError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/areas/{area_id}", status_code=204)
def delete_area(
    area_id: str,
    _admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    try:
        svc.delete_area(area_id)
    except OrgError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# --------------------------------------------------------------- organizations

@router.get("/organizations", response_model=list[OrganizationDTO])
def list_organizations(
    area_id: Optional[str] = Query(default=None, description="only this area's bodies"),
    _admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    return svc.list_organizations(area_id)


@router.post("/organizations", response_model=OrganizationDTO, status_code=201)
def create_organization(
    req: OrganizationCreate,
    _admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    try:
        return svc.create_organization(req)
    except OrgError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/organizations/{org_id}", status_code=204)
def delete_organization(
    org_id: str,
    _admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    try:
        svc.delete_organization(org_id)
    except OrgError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# ------------------------------------------------------------------ organizers

@router.get("/organizers", response_model=list[OrganizerDTO])
def list_organizers(
    area_id: Optional[str] = Query(default=None, description="only organizers posted here"),
    _admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    return svc.list_organizers(area_id)


@router.post("/organizers", response_model=OrganizerDTO, status_code=201)
def create_organizer(
    req: OrganizerCreate,
    admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    """Promote an existing account to organizer. 404 if that account doesn't
    exist — this endpoint never creates one."""
    try:
        return svc.create_organizer(admin, req)
    except OrgError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.patch("/organizers/{user_id}", response_model=OrganizerDTO)
def update_organizer(
    user_id: str,
    req: OrganizerUpdate,
    _admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    """Move an organizer's posting, or suspend them (``is_active=false``) without
    demoting the account. Demotion is DELETE."""
    try:
        return svc.update_organizer(user_id, req)
    except OrgError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/organizers/{user_id}", status_code=204)
def deactivate_organizer(
    user_id: str,
    admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    """Stand an organizer down: the profile is deactivated and the account drops
    to ``general_user``. Their tournaments keep their owner — deleting somebody's
    competitions because they left the job would take the scorecards with them."""
    try:
        svc.deactivate_organizer(admin, user_id)
    except OrgError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# --------------------------------------------------------------------- roles

@router.put("/users/{user_id}/role")
def assign_role(
    user_id: str,
    req: RoleAssign,
    admin: UserRecord = Depends(require_admin),
    svc: OrgService = Depends(get_org_service),
):
    """The only way an account's role changes."""
    try:
        return svc.assign_role(admin, user_id, req.role)
    except OrgError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# --------------------------------------------------------------------- audit

@router.get("/audit", response_model=list[AuditDTO])
def list_audit(
    limit: int = Query(default=100, ge=1, le=500),
    action: Optional[str] = Query(default=None, description="e.g. role.assigned"),
    actor_id: Optional[str] = Query(default=None, description="who did it"),
    _admin: UserRecord = Depends(require_admin),
    svc: AuditService = Depends(get_audit_service),
):
    """Who changed what, newest first."""
    return svc.list(limit=limit, action=action, actor_id=actor_id)
