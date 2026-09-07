"""Community / social — follow, activity feed, notifications. All require a
signed-in user (it's *your* graph, feed and inbox)."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_active_user, get_social_service
from app.core.security import decode_access_token
from app.repositories.user_repository import UserRecord
from app.schemas.social import (
    ActivityDTO, EntityFollowState, FollowState, NotificationDTO, NotificationPrefs,
    PushRotateRequest, PushSubscribeRequest, PushUnsubscribeRequest, VapidKey,
)
from app.services.social_service import SocialError, SocialService

router = APIRouter(prefix="/social", tags=["social"])


@router.post("/follow/{user_id}", response_model=FollowState)
def follow(
    user_id: str,
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    try:
        return svc.follow(me, user_id)
    except SocialError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/follow/{user_id}", response_model=FollowState)
def unfollow(
    user_id: str,
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    return svc.unfollow(me, user_id)


@router.get("/following", response_model=list[str])
def my_following(
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    return svc.following_ids(me.id)


@router.get("/feed", response_model=list[ActivityDTO])
def feed(
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    return svc.feed(me.id)


@router.get("/notifications", response_model=list[NotificationDTO])
def notifications(
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    return svc.notifications(me.id)


@router.get("/notifications/unread")
def unread(
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    return {"count": svc.unread(me.id)}


@router.post("/notifications/read", status_code=204)
def mark_read(
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    svc.mark_read(me.id)


@router.delete("/notifications/{notification_id}", status_code=204)
def delete_notification(
    notification_id: str,
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    # idempotent: deleting an already-gone (or not-yours) notification is a no-op 204
    svc.delete_notification(me.id, notification_id)


@router.post("/notifications/{notification_id}/click", status_code=204)
def click_notification(
    notification_id: str,
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    # engagement tracking: records the click for CTR (idempotent, scoped to the owner)
    svc.mark_clicked(me.id, notification_id)


# ----- entity follow (team / player / tournament / match / club / academy) -----
@router.post("/follow/entity/{entity_type}/{entity_id}", response_model=EntityFollowState)
def follow_entity(
    entity_type: str, entity_id: str,
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    try:
        return svc.follow_entity(me, entity_type, entity_id)
    except SocialError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/follow/entity/{entity_type}/{entity_id}", response_model=EntityFollowState)
def unfollow_entity(
    entity_type: str, entity_id: str,
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    return svc.unfollow_entity(me, entity_type, entity_id)


@router.get("/follow/entity/{entity_type}/{entity_id}", response_model=EntityFollowState)
def entity_follow_state(
    entity_type: str, entity_id: str,
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    return svc.entity_follow_state(me.id, entity_type, entity_id)


@router.get("/following/entities")
def my_followed_entities(
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    return svc.followed_entities(me.id)


# ----- preferences -----
@router.get("/notifications/preferences", response_model=NotificationPrefs)
def get_prefs(
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    return svc.get_prefs(me.id)


@router.put("/notifications/preferences", response_model=NotificationPrefs)
def set_prefs(
    prefs: NotificationPrefs,
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    return svc.set_prefs(me.id, prefs.model_dump())


# ----- web push (browser notifications) -----
@router.get("/push/vapid-key", response_model=VapidKey)
def push_vapid_key(svc: SocialService = Depends(get_social_service)):
    """Public app-server key the browser passes to pushManager.subscribe()."""
    return svc.push_config()


@router.post("/push/subscribe", status_code=204)
def push_subscribe(
    body: PushSubscribeRequest,
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    svc.add_push_subscription(me.id, body.endpoint, body.keys.p256dh, body.keys.auth, body.platform)


@router.post("/push/unsubscribe", status_code=204)
def push_unsubscribe(
    body: PushUnsubscribeRequest,
    me: UserRecord = Depends(get_current_active_user),
    svc: SocialService = Depends(get_social_service),
):
    # idempotent: dropping an already-gone / not-yours subscription is a no-op 204
    svc.remove_push_subscription(me.id, body.endpoint)


@router.post("/push/rotate", status_code=204, include_in_schema=False)
def push_rotate(body: PushRotateRequest, svc: SocialService = Depends(get_social_service)):
    """Called by the SW when the browser rotates a subscription. Unauthenticated:
    the (secret) old endpoint proves ownership; only a known subscription rotates."""
    svc.rotate_push_subscription(body.old_endpoint, body.endpoint, body.keys.p256dh,
                                 body.keys.auth, body.platform)


# ----- realtime (per-user SSE) -----
@router.get("/notifications/stream", include_in_schema=False)
async def notifications_stream(
    request: Request,
    token: str = "",
    svc: SocialService = Depends(get_social_service),
):
    """Per-user realtime notification stream. EventSource can't send an Authorization
    header, so the access token arrives as ?token=. Emits {unread, latest} on change."""
    try:
        payload = decode_access_token(token)
    except Exception:
        payload = None
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="invalid or missing token")
    user_id = str(payload["sub"])
    once = request.query_params.get("once") == "1"

    async def gen():
        last = None
        ticks = 0
        while True:
            if await request.is_disconnected():
                break
            version = await run_in_threadpool(svc.notification_version, user_id)
            if version != last:
                last = version
                yield "data: " + json.dumps({"unread": version[0], "latest": version[1]}) + "\n\n"
            elif ticks % 6 == 0:
                yield ": keep-alive\n\n"
            if once:
                break
            ticks += 1
            await asyncio.sleep(3.0)

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )