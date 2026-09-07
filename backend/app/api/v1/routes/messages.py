"""Direct 1:1 messages — all routes require a signed-in user (it's your inbox)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_active_user, get_messaging_service
from app.repositories.user_repository import UserRecord
from app.schemas.messaging import ConversationDTO, MessageDTO, SendMessageRequest, ThreadDTO
from app.services.messaging_service import MessagingError, MessagingService

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessageDTO, status_code=201)
def send_message(
    req: SendMessageRequest,
    me: UserRecord = Depends(get_current_active_user),
    svc: MessagingService = Depends(get_messaging_service),
):
    try:
        return svc.send(me, req.recipient_id, req.text)
    except MessagingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("", response_model=list[ConversationDTO])
def inbox(
    me: UserRecord = Depends(get_current_active_user),
    svc: MessagingService = Depends(get_messaging_service),
):
    return svc.conversations(me)


@router.get("/unread")
def unread(
    me: UserRecord = Depends(get_current_active_user),
    svc: MessagingService = Depends(get_messaging_service),
):
    return {"count": svc.unread_total(me.id)}


# Registered after /unread so the literal path isn't read as a user id.
@router.get("/{user_id}", response_model=ThreadDTO)
def thread(
    user_id: str,
    me: UserRecord = Depends(get_current_active_user),
    svc: MessagingService = Depends(get_messaging_service),
):
    try:
        return svc.thread(me, user_id)
    except MessagingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
