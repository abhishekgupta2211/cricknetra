"""Public, server-rendered pages.

Two families share this router:
  * the **marketing site** (/, /contact, /tips, /tools) — static content built on
    ``site_base.html`` + ``landing.css``;
  * the **directories & shareable pages** (/live-matches, /tournaments, /m/{id},
    /t/{id}) — server-rendered from the same services the API uses.

All registered before the StaticFiles mount in ``main.py``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_commentary_service, get_match_service, get_tournament_service
from app.schemas.match import MatchStateDTO
from app.schemas.tournament import TournamentDetailDTO
from app.services.commentary_service import CommentaryService
from app.services.match_service import MatchNotFound, MatchService
from app.services.tournament_service import TournamentNotFound, TournamentService

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

public_router = APIRouter(tags=["public"])


# ----------------------------------------------------------------- helpers ---
def _initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def _color(name: str) -> str:
    """Stable green-ish logo colour derived from the name."""
    h = sum(ord(c) for c in (name or "x")) % 360
    return f"hsl({h}, 45%, 42%)"


def _match_card(st: MatchStateDTO) -> dict:
    by_team = {inn.batting_team: inn for inn in st.innings}
    current_bat = st.innings[st.current_innings - 1].batting_team if st.innings else None
    live = st.result is None
    rows = []
    for team in (st.team_a, st.team_b):
        inn = by_team.get(team)
        if inn is not None:
            rows.append(
                {
                    "team": team, "batted": True,
                    "score": f"{inn.runs}/{inn.wickets}", "overs": inn.overs_str,
                    "hl": live and team == current_bat,
                }
            )
        else:
            rows.append({"team": team, "batted": False, "score": None, "overs": None, "hl": False})
    if live:
        cur = st.innings[st.current_innings - 1]
        note = cur.result_note or f"{cur.batting_team} batting"
    else:
        note = st.result
    return {
        "id": st.id, "format": st.rules_name or st.format_id, "live": live,
        "status_label": "Live" if live else "Result", "rows": rows, "note": note,
        "streaming": st.stream is not None,  # has a bring-your-own live-stream attached
    }


def _tournament_card(d: TournamentDetailDTO) -> dict:
    fmt = "Knockout" if d.format == "knockout" else "League"
    started = any(f.status in ("live", "completed") for f in d.fixtures)
    if d.format == "knockout":
        done = d.champion is not None
    else:
        done = bool(d.fixtures) and all(f.status == "completed" for f in d.fixtures)
    status = "Completed" if done else ("Ongoing" if started else "Upcoming")
    note = None
    if d.champion:
        note = f"🏆 {d.champion.name}"
    elif d.format == "round_robin" and d.standings and started:
        note = f"Leader: {d.standings[0].name}"
    return {
        "id": d.id, "name": d.name, "fmt": fmt, "teams": len(d.teams),
        "status": status, "note": note, "initials": _initials(d.name), "color": _color(d.name),
    }


def _page(request: Request, name: str, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name=name, context=ctx)


def _not_found(request: Request, what: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="notfound.html",
        context={"what": what, "title": "Not found", "desc": "", "app_link": "/app"},
        status_code=404,
    )


# -------------------------------------------------------- marketing pages ---
@public_router.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing(request: Request):
    return _page(request, "landing.html", active="home")


@public_router.get("/contact", response_class=HTMLResponse, include_in_schema=False)
def contact(request: Request):
    return _page(request, "contact.html", active="contact")


@public_router.get("/tips", response_class=HTMLResponse, include_in_schema=False)
def tips(request: Request):
    return _page(request, "tips.html", active="tips")


@public_router.get("/tools", response_class=HTMLResponse, include_in_schema=False)
def tools(request: Request):
    return _page(request, "tools.html", active="tools")


@public_router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    return _page(request, "login.html")


@public_router.get("/register", response_class=HTMLResponse, include_in_schema=False)
def register_page(request: Request):
    return _page(request, "register.html")


# ----------------------------------------------------------- directories ---
@public_router.get("/live-matches", response_class=HTMLResponse, include_in_schema=False)
def public_live_matches(request: Request, svc: MatchService = Depends(get_match_service)):
    cards, live_count = [], 0
    for s in svc.list_summaries():
        try:
            st = svc.get_state(s.id)
        except MatchNotFound:
            continue
        card = _match_card(st)
        if card["live"]:
            live_count += 1
        cards.append(card)
    cards.sort(key=lambda c: 0 if c["live"] else 1)
    return _page(request, "live_matches.html", cards=cards, live_count=live_count, active="live")


@public_router.get("/tournaments", response_class=HTMLResponse, include_in_schema=False)
def public_tournaments(request: Request, svc: TournamentService = Depends(get_tournament_service)):
    cards, ongoing = [], 0
    for t in svc.list():
        try:
            d = svc.get_detail(t.id)
        except TournamentNotFound:
            continue
        card = _tournament_card(d)
        if card["status"] == "Ongoing":
            ongoing += 1
        cards.append(card)
    order = {"Ongoing": 0, "Upcoming": 1, "Completed": 2}
    cards.sort(key=lambda c: order.get(c["status"], 3))
    return _page(request, "tournaments_public.html", cards=cards, ongoing_count=ongoing, active="tournaments")


@public_router.get("/highlights", response_class=HTMLResponse, include_in_schema=False)
def public_highlights(request: Request, svc: MatchService = Depends(get_match_service)):
    """Gallery of every highlight clip (bring-your-own links + auto-cut videos)
    attached to any match, grouped by match — live matches first, most clips first."""
    groups, clip_total = [], 0
    for s in svc.list_summaries():
        try:
            st = svc.get_state(s.id)
        except MatchNotFound:
            continue
        if not st.clips:
            continue
        card = _match_card(st)
        groups.append(
            {
                "id": st.id, "title": f"{st.team_a} vs {st.team_b}",
                "format": card["format"], "live": card["live"],
                "status_label": card["status_label"], "note": card["note"],
                "clips": st.clips,
            }
        )
        clip_total += len(st.clips)
    groups.sort(key=lambda g: (0 if g["live"] else 1, -len(g["clips"])))
    return _page(
        request, "highlights.html", groups=groups, clip_total=clip_total,
        match_count=len(groups), active="highlights",
    )


def _round_label(fmt: str, rnd: int, total_rounds: int) -> str:
    if fmt == "knockout":
        depth = total_rounds - rnd
        return {0: "Final", 1: "Semi-final", 2: "Quarter-final"}.get(depth, f"Round {rnd}")
    return f"Round {rnd}"


def _fixture_card(f, msvc: MatchService, fmt: str, total_rounds: int) -> dict:
    """A match card for one tournament fixture (with scores if it has started)."""
    label = _round_label(fmt, f.round, total_rounds)
    state = None
    if f.match_id:
        try:
            state = msvc.get_state(f.match_id)
        except MatchNotFound:
            state = None
    if state is not None:
        base = _match_card(state)
        return {
            "id": f.match_id, "status": "live" if base["live"] else "completed",
            "badge": base["status_label"], "rows": base["rows"], "note": base["note"],
            "round_label": label,
        }
    # not started yet — or a bye
    is_bye = f.team_b is None
    rows = [
        {"team": f.team_a.name if f.team_a else "TBD", "batted": False, "score": None, "overs": None, "hl": False},
        {"team": "bye" if is_bye else (f.team_b.name if f.team_b else "TBD"), "batted": False, "score": None, "overs": None, "hl": False},
    ]
    completed = is_bye and f.status == "completed"
    return {
        "id": None, "status": "completed" if completed else "upcoming",
        "badge": "Bye" if is_bye else "Upcoming", "rows": rows,
        "note": (f.result or "Advances on a bye") if is_bye else "Yet to start",
        "round_label": label,
    }


# ------------------------------------------------- shareable detail pages ---
def _shots_payload(state) -> list[dict]:
    """Per-innings wagon + pitch shots as plain dicts — JSON-safe for the wagon/pitch
    components rendered on the public match page and the PDF scorecard."""
    return [
        {
            "batting": inn.batting_team, "bowling": inn.bowling_team,
            "striker": inn.striker, "bowler": inn.bowler, "max_overs": inn.max_overs,
            "wagon": [w.model_dump() for w in inn.wagon],
            "pitch": [p.model_dump() for p in inn.pitch],
        }
        for inn in state.innings
    ]


@public_router.get("/m/{match_id}", response_class=HTMLResponse, include_in_schema=False)
def public_match(
    match_id: str,
    request: Request,
    svc: MatchService = Depends(get_match_service),
    comm: CommentaryService = Depends(get_commentary_service),
):
    try:
        state = svc.get_state(match_id)
    except MatchNotFound:
        return _not_found(request, "match")
    rows = _match_card(state)["rows"]
    inn = state.innings[state.current_innings - 1]
    title = f"{state.team_a} vs {state.team_b}"
    desc = state.result or f"{inn.batting_team} {inn.runs}/{inn.wickets} ({inn.overs_str} ov)"
    return _page(
        request, "match.html", m=state, rows=rows, title=title, desc=desc,
        commentary=comm.list(match_id, limit=50),
        ball_feed=list(reversed(svc.commentary_feed(match_id))),  # newest delivery first
        highlights=svc.highlights(match_id),
        clips=svc.list_clips(match_id),
        shots=_shots_payload(state),
        app_link=f"/app#/match/{match_id}", active="live",
    )


@public_router.get("/scorecard/{match_id}", response_class=HTMLResponse, include_in_schema=False)
def scorecard_pdf(
    match_id: str,
    request: Request,
    svc: MatchService = Depends(get_match_service),
):
    """Premium, print-ready scorecard report (its own standalone page). Opened with
    ?print=1 from the app's 'Download PDF'."""
    try:
        report = svc.scorecard_report(match_id)
    except MatchNotFound:
        return _not_found(request, "match")
    live_url = str(request.url_for("public_match", match_id=match_id))
    import segno

    qr_svg = segno.make(live_url, error="m").svg_inline(scale=3, border=0, dark="#111111")
    return _page(
        request, "scorecard_pdf.html", qr_svg=qr_svg, live_url=live_url,
        shots=_shots_payload(report["m"]), **report,
    )


@public_router.get("/overlay/{match_id}", response_class=HTMLResponse, include_in_schema=False)
def overlay_page(
    match_id: str,
    request: Request,
    svc: MatchService = Depends(get_match_service),
):
    """Broadcast scoreboard overlay for live streaming — a transparent, self-contained
    page for OBS Studio / Streamlabs / vMix browser sources. Pulls live data from
    /api/v1/matches/{id}/overlay (poll + SSE). Config via query: ?theme=light,
    ?ticker=0, ?winprob=0, ?compact=1."""
    try:
        svc.get_state(match_id)  # 404 early if the id is wrong
    except MatchNotFound:
        return _not_found(request, "match")
    return _page(request, "overlay.html", match_id=match_id)


@public_router.get("/overlay/{match_id}/analysis", response_class=HTMLResponse, include_in_schema=False)
def overlay_analysis_page(
    match_id: str,
    request: Request,
    svc: MatchService = Depends(get_match_service),
):
    """The analysis OBS scene — an animated worm graph, projected score, run-rate and
    per-innings breakdown. A separate transparent page (add as another OBS scene)."""
    try:
        svc.get_state(match_id)
    except MatchNotFound:
        return _not_found(request, "match")
    return _page(request, "analysis.html", match_id=match_id)


@public_router.get("/t/{tournament_id}", response_class=HTMLResponse, include_in_schema=False)
def public_tournament(
    tournament_id: str,
    request: Request,
    tsvc: TournamentService = Depends(get_tournament_service),
    msvc: MatchService = Depends(get_match_service),
):
    try:
        detail = tsvc.get_detail(tournament_id)
    except TournamentNotFound:
        return _not_found(request, "tournament")

    total_rounds = max((f.round for f in detail.fixtures), default=1)
    cards = [_fixture_card(f, msvc, detail.format, total_rounds) for f in detail.fixtures]
    counts = {s: sum(1 for c in cards if c["status"] == s) for s in ("live", "upcoming", "completed")}
    all_done = bool(cards) and counts["completed"] == len(cards)
    status = (
        "Completed" if (detail.champion or all_done)
        else ("Ongoing" if (counts["live"] or counts["completed"]) else "Upcoming")
    )
    fmt = "Knockout" if detail.format == "knockout" else "League"
    meta = {
        "initials": _initials(detail.name), "color": _color(detail.name), "fmt": fmt,
        "total_matches": len(detail.fixtures), "total_teams": len(detail.teams), "status": status,
    }
    desc = f"{fmt} · {len(detail.teams)} teams"
    if detail.champion:
        desc += f" · 🏆 {detail.champion.name}"

    rounds: dict[int, list] = {}
    for f in detail.fixtures:
        rounds.setdefault(f.round, []).append(f)
    rounds_list = [(rnd, _round_label(detail.format, rnd, total_rounds), rounds[rnd]) for rnd in sorted(rounds)]

    return _page(
        request, "tournament.html", t=detail, cards=cards, counts=counts, meta=meta,
        rounds=rounds_list, title=detail.name, desc=desc,
        app_link=f"/app#/tournament/{tournament_id}", active="tournaments",
    )
