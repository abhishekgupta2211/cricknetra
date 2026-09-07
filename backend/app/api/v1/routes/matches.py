"""Match lifecycle + scoring — the core REST surface a React client drives.

Reads are public. Creating a match needs the ``match.create`` capability and
records the creator as owner; scoring needs ownership or a per-match umpire
approval; deleting needs *management* of the match — its owner, the organizer
whose competition it belongs to, or the admin — which is narrower than scoring
on purpose.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.api.deps import (
    get_activity_repo,
    get_audit_service,
    get_award_repo,
    get_clipper_service,
    get_commentary_service,
    get_current_active_user,
    get_fielding_event_service,
    get_match_official_service,
    get_match_service,
    get_notification_dispatcher,
    get_ownership_repo,
    get_scope_service,
    get_social_service,
    get_tournament_repo,
    require_capability,
    require_match_owner,
    require_match_scorer,
)
from app.core import clipper
from app.core.permissions import Caps, has_capability, is_admin
from app.domain.engine import ScoringError
from app.repositories.audit_repository import AuditActions
from app.repositories.member_activity_repository import MemberActivityRepository
from app.repositories.ownership_repository import OwnershipRepository
from app.repositories.tournament_repository import TournamentRepository
from app.repositories.user_repository import UserRecord
from app.schemas.commentary import BallFeedDTO, CommentaryCreate, CommentaryDTO, HighlightDTO
from app.schemas.fielding import FieldingEventCreate, FieldingEventDTO
from app.schemas.match import (
    AbandonRequest,
    AutoClipRequest,
    BroadcastRequest,
    ClipCreate,
    CreateMatchRequest,
    InterruptRequest,
    MatchClipDTO,
    MatchStateDTO,
    MatchSummaryDTO,
    DlsSuggestRequest,
    DlsSuggestion,
    ResumeRequest,
    RevisedTargetRequest,
    StreamUrlRequest,
    SuperOverRequest,
)
from app.schemas.scoring import BallRequest, SetBowlerRequest
from app.services import broadcast
from app.services.commentary_service import CommentaryService
from app.services.fielding_event_service import FieldingEventError, FieldingEventService
from app.services.scope_service import ScopeService
from app.services.match_service import InvalidMatchSetup, MatchNotFound, MatchService

router = APIRouter(prefix="/matches", tags=["matches"])


def _state_version(s: MatchStateDTO) -> tuple:
    """A cheap fingerprint that changes whenever the live score changes."""
    return (
        s.result,
        s.current_innings,
        s.needs_super_over,
        s.awaiting_super_second,
        s.awaiting_bowler,
        tuple((i.runs, i.wickets, i.legal_balls) for i in s.innings),
    )


@router.post("", response_model=MatchStateDTO, status_code=201)
def create_match(
    req: CreateMatchRequest,
    svc: MatchService = Depends(get_match_service),
    user: UserRecord = Depends(require_capability(Caps.CREATE_MATCH)),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    social=Depends(get_social_service),
):
    try:
        state = svc.create_match(req)
    except InvalidMatchSetup as e:
        raise HTTPException(status_code=400, detail=str(e))
    owners.set_owner("match", state.id, user.id)
    social.record(user, "match", f"started scoring {state.team_a} vs {state.team_b}", f"/m/{state.id}")
    return state


@router.get("", response_model=list[MatchSummaryDTO])
def list_matches(svc: MatchService = Depends(get_match_service)):
    return svc.list_summaries()


@router.get("/{match_id}", response_model=MatchStateDTO)
def get_match(match_id: str, svc: MatchService = Depends(get_match_service)):
    try:
        return svc.get_state(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")


@router.get("/{match_id}/overlay", include_in_schema=False)
def match_overlay(match_id: str, svc: MatchService = Depends(get_match_service)):
    """Compact live payload for the broadcast scoreboard overlay (public; polled +
    SSE-triggered by the transparent OBS/vMix page at /overlay/{id})."""
    try:
        return svc.overlay(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")


@router.get("/{match_id}/analysis", include_in_schema=False)
def match_analysis(match_id: str, svc: MatchService = Depends(get_match_service)):
    """Analytics payload for the analysis OBS scene (worm, projected, powerplay,
    per-innings stats) at /overlay/{id}/analysis. Public; a separate low-freq scene."""
    try:
        return svc.analysis(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")


@router.get("/{match_id}/broadcast", include_in_schema=False)
def get_broadcast_mode(match_id: str, svc: MatchService = Depends(get_match_service)):
    """Current broadcast presentation mode for the single OBS overlay source. Public;
    polled by every open overlay instance so they cross-fade in sync."""
    try:
        svc.get_state(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    return broadcast.get_broadcast(match_id)


@router.post("/{match_id}/broadcast", include_in_schema=False)
def set_broadcast_mode(
    match_id: str,
    body: BroadcastRequest,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    """Operator sets the mode (from the ?control=1 panel / keyboard).

    Whoever may score the match may drive its overlay. This used to take no
    authentication at all, which meant an anonymous caller could change what a
    live broadcast audience saw on any match on the platform.
    """
    try:
        svc.get_state(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    try:
        return broadcast.set_broadcast(match_id, body.mode, body.auto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{match_id}/stream", include_in_schema=False)
async def stream_match(
    match_id: str,
    request: Request,
    svc: MatchService = Depends(get_match_service),
):
    """Server-Sent Events: push a small frame whenever the live score changes.

    Public (anyone with the share link can watch). The blocking DB read runs in
    the threadpool and the loop sleeps asynchronously, so one event-loop serves
    many watchers; the stream ends when the match is decided or the client leaves.
    """
    once = request.query_params.get("once") == "1"  # emit one frame and stop (tests)

    async def gen():
        last = None
        ticks = 0
        while True:
            if await request.is_disconnected():
                break
            try:
                state = await run_in_threadpool(svc.get_state, match_id)
            except MatchNotFound:
                yield "event: gone\ndata: {}\n\n"
                break
            version = _state_version(state)
            if version != last:
                last = version
                inn = state.innings[state.current_innings - 1]
                frame = {
                    "runs": inn.runs, "wickets": inn.wickets, "overs": inn.overs_str,
                    "done": state.result is not None,
                }
                yield "data: " + json.dumps(frame) + "\n\n"
                if state.result is not None or once:
                    break  # match decided (or one-shot) — final frame sent
            elif ticks % 6 == 0:
                yield ": keep-alive\n\n"
            if once:
                break
            ticks += 1
            await asyncio.sleep(2.5)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/{match_id}/balls", response_model=MatchStateDTO)
def record_ball(
    match_id: str,
    req: BallRequest,
    svc: MatchService = Depends(get_match_service),
    dispatcher=Depends(get_notification_dispatcher),
    _user: UserRecord = Depends(require_match_scorer),
):
    try:
        state = svc.record_ball(match_id, req)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))
    dispatcher.on_match_state(state)   # milestones each ball; finish/awards once
    return state


@router.put("/{match_id}/balls/{index}", response_model=MatchStateDTO)
def edit_ball(
    match_id: str,
    index: int,
    req: BallRequest,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    """Correct an earlier delivery in the live innings (index into that innings)."""
    try:
        return svc.edit_ball(match_id, index, req)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except IndexError:
        raise HTTPException(status_code=404, detail="no such delivery")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{match_id}/balls/{index}", response_model=MatchStateDTO)
def delete_ball(
    match_id: str,
    index: int,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    """Remove an earlier delivery from the live innings and re-derive."""
    try:
        return svc.delete_ball(match_id, index)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except IndexError:
        raise HTTPException(status_code=404, detail="no such delivery")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{match_id}/bowler", response_model=MatchStateDTO)
def set_bowler(
    match_id: str,
    req: SetBowlerRequest,
    svc: MatchService = Depends(get_match_service),
    user: UserRecord = Depends(require_match_scorer),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    activity: MemberActivityRepository = Depends(get_activity_repo),
):
    try:
        state = svc.set_bowler(match_id, req.bowler)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except ScoringError as e:  # ineligible bowler (consecutive overs / over limit)
        raise HTTPException(status_code=409, detail=str(e))
    # officiating someone else's match counts as "umpired" in your records
    owner = owners.get_owner("match", match_id)
    if owner is not None and str(owner) != str(user.id):
        activity.record(user.id, "match_umpired", match_id)
    return state


@router.post("/{match_id}/commentate", status_code=204)
def commentate(
    match_id: str,
    svc: MatchService = Depends(get_match_service),
    user: UserRecord = Depends(get_current_active_user),
    activity: MemberActivityRepository = Depends(get_activity_repo),
    scope: ScopeService = Depends(get_scope_service),
):
    """Mark that you commentated this match (adds to your member records).

    Gated on actually being allowed to commentate here: this figure appears in
    the directory organizers use to pick officials, so anybody able to tick it
    on a stranger's match could pad their own record.
    """
    if not scope.can_commentate(user, match_id):
        raise HTTPException(
            status_code=403,
            detail="You're not on this match's commentary team.",
        )
    try:
        svc.get_state(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    activity.record(user.id, "match_commentated", match_id)


@router.post("/{match_id}/commentary", response_model=CommentaryDTO, status_code=201)
def post_commentary(
    match_id: str,
    req: CommentaryCreate,
    svc: MatchService = Depends(get_match_service),
    comm: CommentaryService = Depends(get_commentary_service),
    activity: MemberActivityRepository = Depends(get_activity_repo),
    user: UserRecord = Depends(require_capability(Caps.COMMENTATE)),
    scope: ScopeService = Depends(get_scope_service),
):
    """Post a live commentary line.

    A tournament match is the organizer's to staff, so holding the capability
    is not enough there: it takes the organizer, the match owner, or a
    commentator assigned to that competition. Friendlies stay open to any
    commentator, which is how they have always worked.
    """
    if not scope.can_commentate(user, match_id):
        raise HTTPException(
            status_code=403,
            detail="You're not on this tournament's commentary team.",
        )
    try:
        svc.get_state(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    item = comm.add(match_id, user.id, user.full_name or user.username, req.text)
    activity.record(user.id, "match_commentated", match_id)
    return CommentaryDTO(id=item.id, author_name=item.author_name, text=item.text, when=item.when)


@router.get("/{match_id}/commentary", response_model=list[CommentaryDTO])
def list_commentary(match_id: str, comm: CommentaryService = Depends(get_commentary_service)):
    return [
        CommentaryDTO(id=i.id, author_name=i.author_name, text=i.text, when=i.when)
        for i in comm.list(match_id)
    ]


@router.get("/{match_id}/ball-feed", response_model=list[BallFeedDTO])
def ball_feed(match_id: str, svc: MatchService = Depends(get_match_service)):
    """Auto ball-by-ball commentary, derived from the match's event log."""
    try:
        return svc.commentary_feed(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")


@router.get("/{match_id}/highlights", response_model=list[HighlightDTO])
def match_highlights(match_id: str, svc: MatchService = Depends(get_match_service)):
    """Auto key-moments reel — wickets, boundaries, milestones, result. Derived
    from the ball log (no video, no storage); public read."""
    try:
        return svc.highlights(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")


# ----- highlight clips (bring-your-own links; organizer/admin manage) --------
@router.get("/{match_id}/clips", response_model=list[MatchClipDTO])
def list_clips(match_id: str, svc: MatchService = Depends(get_match_service)):
    """A match's bring-your-own highlight clips (public read)."""
    try:
        return svc.list_clips(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")


@router.post("/{match_id}/clips", response_model=list[MatchClipDTO], status_code=201)
def add_clip(
    match_id: str,
    req: ClipCreate,
    svc: MatchService = Depends(get_match_service),
    _mgr: UserRecord = Depends(require_match_owner),  # organizer (owner) or admin only
):
    """Attach a highlight clip link (YouTube/Facebook/…). Owner/admin only."""
    try:
        return svc.add_clip(match_id, req.url, req.label)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except InvalidMatchSetup as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{match_id}/clips/{clip_id}", response_model=list[MatchClipDTO])
def remove_clip(
    match_id: str,
    clip_id: str,
    svc: MatchService = Depends(get_match_service),
    _mgr: UserRecord = Depends(require_match_owner),  # organizer (owner) or admin only
):
    """Remove a highlight clip. Owner/admin only."""
    try:
        return svc.remove_clip(match_id, clip_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")


# ----- auto-clipped video (ffmpeg): upload a recording, then auto-cut clips -----
@router.get("/{match_id}/recording")
def recording_status(
    match_id: str,
    clipsvc=Depends(get_clipper_service),
    _mgr: UserRecord = Depends(require_match_owner),
):
    """Whether this server can auto-clip and whether a recording is uploaded."""
    return {"ffmpeg_available": clipper.available(), "has_recording": clipsvc.has_recording(match_id)}


@router.post("/{match_id}/recording", status_code=201)
async def upload_recording(
    match_id: str,
    file: UploadFile = File(...),
    clipsvc=Depends(get_clipper_service),
    _mgr: UserRecord = Depends(require_match_owner),  # organizer (owner) or admin only
):
    """Upload a match recording to auto-clip from. Owner/admin only."""
    from app.services.clipper_service import RecordingError

    try:
        dur = await run_in_threadpool(clipsvc.save_recording, match_id, file.file, file.filename or "rec.mp4")
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except RecordingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return {"ok": True, "duration": round(dur, 1)}


@router.post("/{match_id}/clips/auto", response_model=list[MatchClipDTO], status_code=201)
async def generate_auto_clips(
    match_id: str,
    req: AutoClipRequest,
    clipsvc=Depends(get_clipper_service),
    _mgr: UserRecord = Depends(require_match_owner),  # organizer (owner) or admin only
):
    """Auto-cut a clip around each key moment from the uploaded recording, synced
    to the ball log. Owner/admin only. ffmpeg runs off the event loop."""
    from app.services.clipper_service import RecordingError

    try:
        return await run_in_threadpool(clipsvc.generate, match_id, req.anchor)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except RecordingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# ----- match officials (per-match umpire approval) --------------------------
@router.get("/officials/pending")
def my_pending_officials(
    user: UserRecord = Depends(get_current_active_user),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    svc: "MatchOfficialService" = Depends(get_match_official_service),
    svc_match: MatchService = Depends(get_match_service),
):
    """One inbox of every pending umpire request across the matches this user owns,
    so the organizer can approve without opening each match. (Declared before the
    `/{match_id}/officials` route so the literal path wins.)"""
    mine = {str(m) for m in owners.list_by_owner(user.id, "match")}
    if not mine:
        return []
    labels: dict[str, str] = {}
    try:
        for s in svc_match.list_summaries():
            if str(s.id) in mine:
                labels[str(s.id)] = f"{s.team_a} vs {s.team_b}"
    except Exception:  # pragma: no cover - labels are best-effort
        pass
    out = []
    for mid in mine:
        for o in svc.list_for_match(mid):
            if o.status == "pending":
                out.append({
                    "match_id": mid, "umpire_id": o.umpire_id,
                    "umpire_name": o.umpire_name, "match_label": labels.get(mid, f"Match {mid}"),
                })
    return out


@router.get("/{match_id}/officials")
def match_officials(
    match_id: str,
    user: UserRecord = Depends(get_current_active_user),
    svc: "MatchOfficialService" = Depends(get_match_official_service),
    scope: ScopeService = Depends(get_scope_service),
):
    """Viewer-aware: tells the current user if they can score this match, and (for
    the owner/admin) lists umpire requests to approve."""
    is_manager = scope.can_manage_match(user, match_id)
    my_status = svc.status_for(match_id, user.id)
    # Ask the same service the scoring guard asks. Recomputing the rule here
    # let the two drift: this said yes to any SCORE_MATCH holder while the
    # guard said no, so the app showed a scoring button that 403'd on the
    # first delivery.
    can_score = scope.can_score(user, match_id)
    officials = (
        [{"umpire_id": o.umpire_id, "umpire_name": o.umpire_name, "status": o.status} for o in svc.list_for_match(match_id)]
        if is_manager else []
    )
    return {"can_score": can_score, "is_manager": is_manager, "my_status": my_status, "officials": officials}


@router.post("/{match_id}/officials/request", status_code=204)
def request_official(
    match_id: str,
    svc_match: MatchService = Depends(get_match_service),
    svc: "MatchOfficialService" = Depends(get_match_official_service),
    user: UserRecord = Depends(get_current_active_user),
):
    """An umpire asks the match's organizer for permission to officiate."""
    try:
        svc_match.get_state(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    svc.request(user, match_id)


@router.post("/{match_id}/officials/{umpire_id}/approve", status_code=204)
def approve_official(
    match_id: str,
    umpire_id: str,
    _mgr: UserRecord = Depends(require_match_owner),
    svc: "MatchOfficialService" = Depends(get_match_official_service),
):
    svc.approve(match_id, umpire_id)


@router.delete("/{match_id}/officials/{umpire_id}", status_code=204)
def remove_official(
    match_id: str,
    umpire_id: str,
    _mgr: UserRecord = Depends(require_match_owner),
    svc: "MatchOfficialService" = Depends(get_match_official_service),
):
    svc.decline(match_id, umpire_id)


@router.put("/{match_id}/stream", response_model=MatchStateDTO)
def set_stream(
    match_id: str,
    req: StreamUrlRequest,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    """Attach (or clear, with a blank url) a bring-your-own live-stream link
    (YouTube / Facebook). Only whoever can score the match may set it."""
    try:
        return svc.set_stream(match_id, req.stream_url)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except InvalidMatchSetup as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{match_id}/undo", response_model=MatchStateDTO)
def undo(
    match_id: str,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    try:
        return svc.undo(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")


@router.post("/{match_id}/second-innings", response_model=MatchStateDTO)
def start_second_innings(
    match_id: str,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    try:
        return svc.start_second_innings(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{match_id}/revised-target", response_model=MatchStateDTO)
def set_revised_target(
    match_id: str,
    req: RevisedTargetRequest,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    """Apply a DLS-style revised target (and optional reduced overs) to the chase."""
    try:
        return svc.set_revised_target(match_id, req.target, req.overs)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{match_id}/dls-suggest", response_model=DlsSuggestion)
def dls_suggest(
    match_id: str,
    req: DlsSuggestRequest,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    """Compute a Duckworth–Lewis–Stern revised target + live par for a reduced chase."""
    try:
        return svc.dls_suggest(match_id, req.team2_overs, req.g50)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except InvalidMatchSetup as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----- DLS rain interruptions: the scorer only clicks + confirms overs -----
_DLS_REASON_TEXT = {
    "rain": "Rain", "bad_light": "Bad light", "wet_outfield": "A wet outfield",
    "ground_delay": "A ground delay", "power_failure": "A power failure", "other": "An interruption",
}


def _dls_comment(comm, match_id, user, text):
    try:
        comm.add(match_id, author_id=user.id, author_name="DLS", text=text)
    except Exception:  # commentary must never break the scoring action
        pass


@router.post("/{match_id}/interrupt", response_model=MatchStateDTO)
def interrupt_match(
    match_id: str,
    req: InterruptRequest,
    svc: MatchService = Depends(get_match_service),
    comm: CommentaryService = Depends(get_commentary_service),
    user: UserRecord = Depends(require_match_scorer),
):
    """Play stopped (rain / bad light / …). Records the stoppage; awaits resume."""
    try:
        state = svc.interrupt(match_id, req.reason, req.at)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))
    _dls_comment(comm, match_id, user, f"{_DLS_REASON_TEXT.get(req.reason, 'An interruption')} has stopped play.")
    return state


@router.post("/{match_id}/resume", response_model=MatchStateDTO)
def resume_match(
    match_id: str,
    req: ResumeRequest,
    svc: MatchService = Depends(get_match_service),
    comm: CommentaryService = Depends(get_commentary_service),
    user: UserRecord = Depends(require_match_scorer),
):
    """Play resumes with the innings cut to ``overs`` — the revised target self-computes."""
    try:
        state = svc.resume_interruption(match_id, req.overs, req.at)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))
    d = state.dls
    if d and d.revised_target is not None:
        _dls_comment(comm, match_id, user,
                     f"Play resumed. DLS revised target: {d.revised_target} runs from {req.overs} overs.")
    else:
        _dls_comment(comm, match_id, user, f"Play resumed — the innings is reduced to {req.overs} overs.")
    return state


@router.post("/{match_id}/interrupt/cancel", response_model=MatchStateDTO)
def cancel_interruption(
    match_id: str,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    """A false alarm — drop the pending interruption."""
    try:
        return svc.cancel_interruption(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{match_id}/abandon", response_model=MatchStateDTO)
def abandon_match(
    match_id: str,
    req: AbandonRequest,
    svc: MatchService = Depends(get_match_service),
    comm: CommentaryService = Depends(get_commentary_service),
    user: UserRecord = Depends(require_match_scorer),
):
    """Call the match off — decided on DLS par if the chase passed the minimum overs."""
    try:
        state = svc.abandon_match(match_id, req.reason)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))
    _dls_comment(comm, match_id, user, f"Match abandoned. {state.result or 'No result.'}")
    return state


@router.post("/{match_id}/declare", response_model=MatchStateDTO)
def declare_innings(
    match_id: str,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    """Declare the current innings closed (captain's declaration)."""
    try:
        return svc.declare(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ----- fielding events: dropped catches / runs saved / misfields ------------
@router.get("/{match_id}/fielding", response_model=list[FieldingEventDTO])
def list_fielding(
    match_id: str,
    fsvc: FieldingEventService = Depends(get_fielding_event_service),
):
    """Public read of a match's logged fielding events."""
    return fsvc.list(match_id)


@router.post("/{match_id}/fielding", response_model=FieldingEventDTO, status_code=201)
def add_fielding(
    match_id: str,
    req: FieldingEventCreate,
    svc: MatchService = Depends(get_match_service),
    fsvc: FieldingEventService = Depends(get_fielding_event_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    """Log a dropped catch / runs saved / misfield on the match (scorer only)."""
    try:
        svc.get_engine(match_id)  # 404 if the match doesn't exist
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    try:
        return fsvc.add(match_id, req)
    except FieldingEventError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/{match_id}/fielding/{event_id}", status_code=204)
def delete_fielding(
    match_id: str,
    event_id: str,
    fsvc: FieldingEventService = Depends(get_fielding_event_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    try:
        fsvc.delete(match_id, event_id)
    except FieldingEventError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/{match_id}/super-over", response_model=MatchStateDTO)
def super_over(
    match_id: str,
    req: SuperOverRequest,
    svc: MatchService = Depends(get_match_service),
    _user: UserRecord = Depends(require_match_scorer),
):
    """Start a super over on a tie (``bat_first``), or begin the reply within it."""
    try:
        return svc.super_over(match_id, req.bat_first)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    except ScoringError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{match_id}", status_code=204)
def delete_match(
    match_id: str,
    svc: MatchService = Depends(get_match_service),
    user: UserRecord = Depends(require_match_owner),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    tournaments: TournamentRepository = Depends(get_tournament_repo),
    officials: "MatchOfficialService" = Depends(get_match_official_service),
    comm: CommentaryService = Depends(get_commentary_service),
    fsvc: FieldingEventService = Depends(get_fielding_event_service),
    awards=Depends(get_award_repo),
    audit=Depends(get_audit_service),
):
    """Remove a match — whoever started it, the organizer whose competition it
    belongs to, or the admin.

    Owner-scoped rather than admin-only, for the same reason deleting a
    tournament is: an organizer who opened a scorecard by mistake has to be
    able to take it down without a support ticket. ``require_match_owner`` is
    already the guard that lets them do that to *theirs* and refuses somebody
    else's — an umpire approved to score this match is deliberately outside it,
    because scoring a game is not the same as being able to erase it.

    Everything keyed on the match id goes with it. The engine and its ball log
    go through the service (which also drops the match-player links), and the
    rows that live in their own stores are cleared here: the ownership row, the
    umpire approvals (standing permissions to score a match that no longer
    exists), the commentary, the fielding log, the awards, and — the one that
    bites hardest — the fixture's link back to the match. A fixture left
    pointing at a deleted match reads as permanently "live" and refuses to be
    started again, so the game could never be re-scored.
    """
    try:
        engine = svc.get_engine(match_id)
    except MatchNotFound:
        raise HTTPException(status_code=404, detail="match not found")
    label = f"{engine.team_a} vs {engine.team_b}"

    svc.delete(match_id)          # the engine, its ball log, and the player links
    owners.delete("match", match_id)
    tournaments.unlink_match(match_id)   # the fixture goes back on the schedule
    officials.clear_match(match_id)
    comm.delete_for_match(match_id)
    fsvc.delete_for_match(match_id)
    awards.delete_for_match(match_id)
    audit.record(user.id, AuditActions.MATCH_DELETED, "match", match_id, f"deleted {label}")
