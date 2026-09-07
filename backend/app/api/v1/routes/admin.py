"""Admin-only endpoints — currently the elevated-role approval queue."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_role_service, get_social_service, require_admin
from app.repositories.user_repository import UserRecord
from app.schemas.social import AnnouncementCreate, AnnouncementResult, CampaignAnalyticsDTO
from app.schemas.user import RoleRequestDTO
from app.services.role_service import RoleError, RoleService
from app.services.social_service import SocialError, SocialService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/role-requests", response_model=list[RoleRequestDTO])
def list_role_requests(
    _admin: UserRecord = Depends(require_admin),
    svc: RoleService = Depends(get_role_service),
):
    return svc.list_pending()


@router.post("/role-requests/{user_id}/approve")
def approve_role(
    user_id: str,
    _admin: UserRecord = Depends(require_admin),
    svc: RoleService = Depends(get_role_service),
):
    try:
        return svc.approve(user_id)
    except RoleError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/role-requests/{user_id}/reject", status_code=204)
def reject_role(
    user_id: str,
    _admin: UserRecord = Depends(require_admin),
    svc: RoleService = Depends(get_role_service),
):
    try:
        svc.reject(user_id)
    except RoleError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# ----- broadcast announcements + engagement analytics -----
@router.post("/announcements", response_model=AnnouncementResult, status_code=201)
def create_announcement(
    body: AnnouncementCreate,
    admin: UserRecord = Depends(require_admin),
    social: SocialService = Depends(get_social_service),
):
    """Broadcast an announcement to every user (respecting each user's category opt-out)."""
    try:
        return social.broadcast(admin, title=body.title, text=body.text,
                                category=body.category, link=body.link)
    except SocialError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/announcements/analytics", response_model=list[CampaignAnalyticsDTO])
def announcement_analytics(
    _admin: UserRecord = Depends(require_admin),
    social: SocialService = Depends(get_social_service),
):
    """Per-campaign engagement funnel: delivered / opened / clicked + open-rate + CTR."""
    return social.announcement_analytics()
