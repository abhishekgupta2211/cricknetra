"""The "Looking For" board — players/teams seeking each other or a match.
Browsing and posting both require a signed-in user."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_active_user, get_looking_for_service
from app.core.permissions import is_admin
from app.repositories.user_repository import UserRecord
from app.schemas.looking_for import LookingForCreate, LookingForDTO
from app.services.looking_for_service import LookingForError, LookingForService

router = APIRouter(prefix="/looking-for", tags=["looking-for"])


@router.post("", response_model=LookingForDTO, status_code=201)
def create_post(
    req: LookingForCreate,
    me: UserRecord = Depends(get_current_active_user),
    svc: LookingForService = Depends(get_looking_for_service),
):
    try:
        return svc.create(me, req.kind, req.text, req.location, req.role)
    except LookingForError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("", response_model=list[LookingForDTO])
def list_posts(
    kind: Optional[str] = Query(default=None, description="player | team | match"),
    location: Optional[str] = Query(default=None),
    me: UserRecord = Depends(get_current_active_user),
    svc: LookingForService = Depends(get_looking_for_service),
):
    return svc.list(me.id, kind=kind, location=location)


# Registered before /{post_id}/... routes so "mine" isn't read as a post id.
@router.get("/mine", response_model=list[LookingForDTO])
def my_posts(
    me: UserRecord = Depends(get_current_active_user),
    svc: LookingForService = Depends(get_looking_for_service),
):
    return svc.mine(me.id)


@router.post("/{post_id}/close", status_code=204)
def close_post(
    post_id: str,
    me: UserRecord = Depends(get_current_active_user),
    svc: LookingForService = Depends(get_looking_for_service),
):
    try:
        svc.close(post_id, me, is_admin=is_admin(me.role))
    except LookingForError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/{post_id}", status_code=204)
def delete_post(
    post_id: str,
    me: UserRecord = Depends(get_current_active_user),
    svc: LookingForService = Depends(get_looking_for_service),
):
    try:
        svc.delete(post_id, me, is_admin=is_admin(me.role))
    except LookingForError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
