"""Broadcast overlay — end-to-end in a real browser against the hermetic server.

Covers (1) the scorer-facing "Broadcast overlay" panel on the match screen exposing
a copyable /overlay/{id} URL, and (2) the transparent OBS overlay page booting and
filling its scoreboard from the live /api/v1/matches/{id}/overlay endpoint.

Signs in as the seeded admin (CRICNETRA_SEED_ADMIN) — a self-registered user is
viewer-level and can't create/score a match.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def _login_admin(page: Page, base_url: str) -> None:
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)
    assert page.evaluate("() => localStorage.getItem('cn_token')"), "expected a JWT after admin login"


def _api(page: Page, method: str, path: str, body=None):
    return page.evaluate(
        """async ({method, path, body}) => {
            const r = await fetch('/api/v1' + path, {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + localStorage.getItem('cn_token'),
                },
                body: body ? JSON.stringify(body) : undefined,
            });
            let data = null; try { data = await r.json(); } catch (e) {}
            return {status: r.status, data};
        }""",
        {"method": method, "path": path, "body": body},
    )


def _match_with_a_ball(page: Page, value: int) -> str:
    r = _api(page, "POST", "/matches",
             {"team_a": "Strikers", "team_b": "Blasters", "format_id": "t20", "bat_first": "a"})
    assert r["status"] == 201, r
    mid = r["data"]["id"]
    bowler = _api(page, "GET", f"/matches/{mid}")["data"]["available_bowlers"][0]
    assert _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": bowler})["status"] == 200
    assert _api(page, "POST", f"/matches/{mid}/balls", {"action": "runs", "value": value})["status"] == 200
    return mid


def test_overlay_url_panel_on_match_screen(page: Page, base_url, js_errors):
    _login_admin(page, base_url)
    mid = _match_with_a_ball(page, 6)

    page.goto(base_url + f"/app#/match/{mid}")
    page.reload()  # hash-only nav may not re-route; reload boots straight into the match

    ovl = page.locator("#ovlUrl")
    expect(ovl).to_be_visible(timeout=15000)
    assert ovl.input_value().endswith(f"/overlay/{mid}"), ovl.input_value()
    expect(page.locator("#ovlCopy")).to_be_visible()


def test_new_match_form_captures_venue_and_toss(page: Page, base_url, js_errors):
    _login_admin(page, base_url)
    page.goto(base_url + "/app#/new")
    page.reload()  # boot straight into the New-match screen

    page.click(".match-extra > summary")            # open the optional "Match details" block
    page.fill("#mTournament", "Summer Cup 2026")
    page.fill("#mVenue", "MA Chidambaram Stadium")
    page.select_option("#mTossWinner", "b")
    page.select_option("#mTossDecision", "bowl")
    page.click("#createBtn")                          # quick mode, default teams
    page.wait_for_url(re.compile(r"#/match/\d+"), timeout=15000)

    mid = page.url.split("/match/")[-1]
    meta = _api(page, "GET", f"/matches/{mid}")["data"]["meta"]
    assert meta["tournament"] == "Summer Cup 2026"
    assert meta["venue"] == "MA Chidambaram Stadium"
    assert meta["toss_decision"] == "bowl"
    assert "won the toss and chose to bowl" in (meta["toss_text"] or "")


def test_overlay_shows_match_info_widget(page: Page, base_url, js_errors):
    _login_admin(page, base_url)
    mid = _api(page, "POST", "/matches", {
        "team_a": "CSK", "team_b": "MI", "bat_first": "a", "format_id": "t20",
        "venue": "Wankhede", "tournament": "City League", "match_no": "7",
        "toss_winner": "a", "toss_decision": "bat",
    })["data"]["id"]
    page.goto(base_url + f"/overlay/{mid}")
    mi = page.locator("#matchinfo")
    expect(mi).to_be_visible(timeout=15000)
    expect(mi).to_contain_text("City League")
    expect(mi).to_contain_text("Wankhede")
    expect(mi).to_contain_text("won the toss")


def test_overlay_page_renders_live_scoreboard(page: Page, base_url, js_errors):
    _login_admin(page, base_url)
    mid = _match_with_a_ball(page, 4)

    # the transparent OBS overlay page boots and fills the scoreboard from live data
    page.goto(base_url + f"/overlay/{mid}")
    expect(page.locator("#mbTeam .mono")).to_be_visible(timeout=15000)
    expect(page.locator("#mainBar .mb-score")).to_contain_text("4")
    expect(page.locator("#mbTeam")).to_contain_text("Strikers")

    # transparent background is what makes it usable as an OBS browser source
    bg = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
    assert bg in ("rgba(0, 0, 0, 0)", "transparent"), bg


def test_overlay_live_partnership_widget(page: Page, base_url, js_errors):
    _login_admin(page, base_url)
    mid = _match_with_a_ball(page, 4)
    page.goto(base_url + f"/overlay/{mid}")
    expect(page.locator(".pnr-h")).to_contain_text("Partnership", timeout=15000)
    expect(page.locator("#pnr .pnr-b")).to_have_count(2)      # striker + non-striker rows
    expect(page.locator(".pnr-tot")).to_contain_text("Runs")


def test_broadcast_controller_single_source(page: Page, base_url, js_errors):
    """The operator (?control=1) cues a takeover; it cross-fades over the LIVE
    scoreboard, syncs to the server, and ESC returns to LIVE. The plain URL (what OBS
    uses) never shows the operator panel."""
    _login_admin(page, base_url)
    r = _api(page, "POST", "/matches",
             {"team_a": "Strikers", "team_b": "Blasters", "format_id": "t20", "bat_first": "a"})
    mid = r["data"]["id"]
    bowler = _api(page, "GET", f"/matches/{mid}")["data"]["available_bowlers"][0]
    _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": bowler})
    _api(page, "POST", f"/matches/{mid}/balls", {"action": "runs", "value": 4})

    # operator tab: panel visible, LIVE scoreboard visible
    page.goto(base_url + f"/overlay/{mid}?control=1")
    expect(page.locator("#bcCtl")).to_be_visible(timeout=15000)
    expect(page.locator("#dock")).to_be_visible()

    # cue WAGON → takeover panel appears, server records it
    page.click('#bcCtlBtns button[data-m="WAGON"]')
    expect(page.locator("#bcStage .bc-panel .bc-h")).to_contain_text("Wagon", timeout=8000)
    assert _api(page, "GET", f"/matches/{mid}/broadcast")["data"]["mode"] == "WAGON"

    # ESC → back to LIVE (takeover cleared)
    page.keyboard.press("Escape")
    expect(page.locator("#bcStage .bc-panel")).to_have_count(0, timeout=5000)
    assert _api(page, "GET", f"/matches/{mid}/broadcast")["data"]["mode"] == "LIVE"

    # the OBS-facing URL (no control) never renders the operator panel
    page.goto(base_url + f"/overlay/{mid}")
    expect(page.locator("#bcCtl")).to_be_hidden()


def test_notification_preferences_panel(page: Page, base_url, js_errors):
    """Settings shows a server-persisted notification-preferences panel; a toggle saves."""
    _login_admin(page, base_url)
    page.goto(base_url + "/app#/settings")
    page.reload()
    cb = page.locator("#prefList input[data-pref='match']")
    expect(cb).to_be_visible(timeout=8000)
    cb.uncheck()
    page.wait_for_timeout(700)
    assert _api(page, "GET", "/social/notifications/preferences")["data"]["match"] is False
    _api(page, "PUT", "/social/notifications/preferences", {"match": True})   # reset


def test_realtime_badge_on_followed_match_finish(page: Page, base_url, js_errors):
    """Follow a match, then finish it — the per-user SSE stream pushes the unread count
    and the header notification badge lights up with no reload."""
    _login_admin(page, base_url)
    page.set_viewport_size({"width": 1280, "height": 820})
    rules = {"name": "T20", "format_id": "t20", "players_per_side": 2, "overs_per_innings": 1, "balls_per_over": 6}
    mid = _api(page, "POST", "/matches", {
        "team_a": "A", "team_b": "B", "bat_first": "a", "rules": rules,
        "squad_a": ["a1", "a2"], "squad_b": ["b1", "b2"]})["data"]["id"]
    _api(page, "POST", f"/social/follow/entity/match/{mid}")

    page.goto(base_url + "/app")            # boots the SSE stream
    page.wait_for_timeout(600)
    _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": "b1"})
    for _ in range(6):
        _api(page, "POST", f"/matches/{mid}/balls", {"action": "runs", "value": 1})
    _api(page, "POST", f"/matches/{mid}/second-innings")
    _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": "a1"})
    for _ in range(6):
        _api(page, "POST", f"/matches/{mid}/balls", {"action": "runs", "value": 0})

    # SSE (3s tick) pushes the unread count → the header badge appears without a reload
    expect(page.locator(".app-header .js-notif-badge")).to_be_visible(timeout=15000)


def test_pitch_capture_in_scoring_pad(page: Page, base_url, js_errors):
    """Enabling 'Pitch' in the run pad opens the one-tap picker after a ball, and the
    tapped coordinate is stored + surfaces on the innings with a derived length band."""
    _login_admin(page, base_url)
    r = _api(page, "POST", "/matches",
             {"team_a": "Strikers", "team_b": "Blasters", "format_id": "t20", "bat_first": "a"})
    mid = r["data"]["id"]
    bowler = _api(page, "GET", f"/matches/{mid}")["data"]["available_bowlers"][0]
    _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": bowler})

    page.goto(base_url + f"/app#/match/{mid}")
    page.reload()
    page.check("#trackPitch")                                   # opt in to pitch tracking
    page.click('.padbtn[data-act="run"][data-v="1"]')           # score a single
    pick = page.locator("#pitchPick")
    expect(pick).to_be_visible(timeout=8000)                    # one-tap picker appears
    pick.click(position={"x": 100, "y": 150})                   # tap the pitch

    expect(page.locator("#pitchPick")).to_have_count(0, timeout=5000)   # closes after the tap
    page.wait_for_timeout(600)
    inn = _api(page, "GET", f"/matches/{mid}")["data"]["innings"][0]
    assert inn["runs"] == 1                                     # the ball still recorded normally
    assert len(inn["pitch"]) == 1 and inn["pitch"][0]["length"]  # pitch captured + derived band


def test_scoring_pad_still_works_with_tracking_off(page: Page, base_url, js_errors):
    """No regression: with both toggles off (default) a run records immediately, no popup."""
    _login_admin(page, base_url)
    r = _api(page, "POST", "/matches",
             {"team_a": "Strikers", "team_b": "Blasters", "format_id": "t20", "bat_first": "a"})
    mid = r["data"]["id"]
    _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": _api(page, "GET", f"/matches/{mid}")["data"]["available_bowlers"][0]})
    page.goto(base_url + f"/app#/match/{mid}")
    page.reload()
    # ensure toggles are off, then a run should record with no picker
    if page.locator("#trackShots").is_checked():
        page.uncheck("#trackShots")
    if page.locator("#trackPitch").is_checked():
        page.uncheck("#trackPitch")
    page.click('.padbtn[data-act="run"][data-v="4"]')
    page.wait_for_timeout(500)
    assert page.locator("#pitchPick").count() == 0 and page.locator("#wagPick").count() == 0
    assert _api(page, "GET", f"/matches/{mid}")["data"]["innings"][0]["runs"] == 4


def test_scorecard_player_name_links_to_profile(page: Page, base_url, js_errors):
    """On a from-teams match, a scorecard name is a link that jumps to the player's
    profile (where the shot analytics live)."""
    _login_admin(page, base_url)
    ta = _api(page, "POST", "/teams", {"name": "CSK"})["data"]["id"]
    tb = _api(page, "POST", "/teams", {"name": "MI"})["data"]["id"]
    pa = [_api(page, "POST", "/players", {"name": n})["data"]["id"] for n in ("Gaikwad", "Jadeja", "Dhoni")]
    pb = [_api(page, "POST", "/players", {"name": n})["data"]["id"] for n in ("Rohit", "Surya", "Bumrah")]
    mid = _api(page, "POST", "/matches", {
        "team_a": "CSK", "team_b": "MI", "bat_first": "a", "format_id": "t20",
        "squad_a": ["Gaikwad", "Jadeja", "Dhoni"], "squad_b": ["Rohit", "Surya", "Bumrah"],
        "squad_a_ids": pa, "squad_b_ids": pb, "team_a_id": ta, "team_b_id": tb,
    })["data"]["id"]
    bowler = _api(page, "GET", f"/matches/{mid}")["data"]["available_bowlers"][0]
    _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": bowler})
    _api(page, "POST", f"/matches/{mid}/balls", {"action": "runs", "value": 1})

    page.goto(base_url + f"/app#/match/{mid}")
    page.reload()
    link = page.locator("a.pl-link").first
    expect(link).to_be_visible(timeout=8000)
    link.click()
    expect(page).to_have_url(re.compile(r"#/player/\w"), timeout=8000)   # jumped to a profile


def test_match_charts_wagon_and_pitch_tabs(page: Page, base_url, js_errors):
    """The Match-charts card gains a Pitch-map tab; both Wagon and Pitch mount the
    shared interactive component from the innings shot data."""
    _login_admin(page, base_url)
    r = _api(page, "POST", "/matches",
             {"team_a": "Strikers", "team_b": "Blasters", "format_id": "t20", "bat_first": "a"})
    mid = r["data"]["id"]
    bowler = _api(page, "GET", f"/matches/{mid}")["data"]["available_bowlers"][0]
    _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": bowler})
    _api(page, "POST", f"/matches/{mid}/balls",
         {"action": "runs", "value": 4, "wagon_x": 0.6, "wagon_y": 0.4, "pitch_x": 0.2, "pitch_y": 0.4})
    _api(page, "POST", f"/matches/{mid}/balls",
         {"action": "runs", "value": 6, "wagon_x": -0.3, "wagon_y": 0.5, "pitch_x": -0.1, "pitch_y": 0.6})

    page.goto(base_url + f"/app#/match/{mid}")
    page.reload()
    page.click('.chtab[data-ch="wagon"]')
    expect(page.locator("#wagonMount .cn-wagon-shot")).to_have_count(2, timeout=8000)
    page.click('.chtab[data-ch="pitch"]')
    expect(page.locator("#pitchMount .cn-pitch-dot")).to_have_count(2, timeout=8000)


def test_analysis_overlay_renders_worm_and_tiles(page: Page, base_url, js_errors):
    _login_admin(page, base_url)
    r = _api(page, "POST", "/matches",
             {"team_a": "Strikers", "team_b": "Blasters", "format_id": "t20", "bat_first": "a"})
    mid = r["data"]["id"]
    bowler = _api(page, "GET", f"/matches/{mid}")["data"]["available_bowlers"][0]
    _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": bowler})
    for v in (4, 6, 1, 0, 4, 2):                              # one full over → worm + stats
        _api(page, "POST", f"/matches/{mid}/balls", {"action": "runs", "value": v})

    page.goto(base_url + f"/overlay/{mid}/analysis")
    expect(page.locator("#wormSvg .wline")).to_have_count(1, timeout=15000)   # animated worm path
    expect(page.locator("#crrV")).to_contain_text(".", timeout=10000)         # CRR rolled to e.g. 17.00
    expect(page.locator("#t1v")).not_to_have_text("–")                        # projected populated
    expect(page.locator("#stats .stat")).to_have_count(8)                     # stat tiles
