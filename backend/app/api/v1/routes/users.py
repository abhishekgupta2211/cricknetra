"""Network directory — browse registered members by role, with their records.

Requires sign-in (it includes contact numbers, so it's members-only). Returns
safe fields via PublicUserDTO; the password hash is never exposed.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.api.deps import (
    get_activity_repo,
    get_current_active_user,
    get_ownership_repo,
    get_photo_service,
    get_user_repo,
    member_records,
)
from app.repositories.member_activity_repository import MemberActivityRepository
from app.repositories.ownership_repository import OwnershipRepository
from app.repositories.user_repository import UserRecord, UserRepository
from app.schemas.user import PublicUserDTO
from app.services.photo_service import PhotoService

router = APIRouter(prefix="/users", tags=["users"])


def _location(repo: UserRepository, user_id: str) -> Optional[str]:
    profile = repo.get_profile(user_id)
    if profile is None:
        return None
    parts = [p for p in (profile.city, profile.region or profile.state) if p]
    return ", ".join(parts) or None


@router.get("", response_model=list[PublicUserDTO])
def list_directory(
    role: Optional[str] = Query(default=None, description="filter: player|umpire|commentator|organizer|team_owner|admin|general_user"),
    repo: UserRepository = Depends(get_user_repo),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    activity: MemberActivityRepository = Depends(get_activity_repo),
    photos: PhotoService = Depends(get_photo_service),
    _user: UserRecord = Depends(get_current_active_user),
):
    users = repo.list_users(role)
    have = photos.present("user", [u.id for u in users])
    return [
        PublicUserDTO(
            id=u.id, full_name=u.full_name, username=u.username, role=u.role,
            role_code=u.role_code, user_code=u.user_code, mobile_no=u.mobile_no,
            is_verified=u.is_verified, location=_location(repo, u.id),
            records=member_records(u.id, owners, activity), has_photo=u.id in have,
        )
        for u in users
    ]


@router.get("/{user_id}/photo")
def get_user_photo(user_id: str, photos: PhotoService = Depends(get_photo_service)):
    photo = photos.get("user", user_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="no photo")
    return Response(content=photo.data, media_type=photo.content_type, headers={"Cache-Control": "no-cache"})
