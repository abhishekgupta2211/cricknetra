"""Grounds + coaching academies directory. Browsing is public; adding needs the
team-create capability (organizers/admins); deleting is admin-only."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_venue_service, require_admin, require_capability
from app.core.permissions import Caps
from app.repositories.user_repository import UserRecord
from app.schemas.venue import VenueCreate, VenueDTO
from app.services.venue_service import VenueError, VenueService

router = APIRouter(prefix="/venues", tags=["venues"])


@router.get("", response_model=list[VenueDTO])
def list_venues(
    kind: Optional[str] = Query(default=None, description="ground | academy"),
    location: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    svc: VenueService = Depends(get_venue_service),
):
    return svc.list(kind=kind, location=location, q=q)


@router.post("", response_model=VenueDTO, status_code=201)
def create_venue(
    req: VenueCreate,
    user: UserRecord = Depends(require_capability(Caps.CREATE_TEAM)),
    svc: VenueService = Depends(get_venue_service),
):
    try:
        return svc.create(user, req)
    except VenueError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/{venue_id}", response_model=VenueDTO)
def get_venue(venue_id: str, svc: VenueService = Depends(get_venue_service)):
    dto = svc.get(venue_id)
    if dto is None:
        raise HTTPException(status_code=404, detail="venue not found")
    return dto


@router.delete("/{venue_id}", status_code=204)
def delete_venue(
    venue_id: str,
    _user: UserRecord = Depends(require_admin),
    svc: VenueService = Depends(get_venue_service),
):
    try:
        svc.delete(venue_id)
    except VenueError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
