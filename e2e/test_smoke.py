"""Playwright smoke tests — the marketing site, the public pages, and the SPA all
load and boot without JavaScript errors, against a hermetic in-memory server.

Run:  backend/.venv/Scripts/python -m pytest e2e
"""

from __future__ import annotations

import os
import re

import pytest
from playwright.sync_api import Page, expect


def test_server_is_hermetic_in_memory(page: Page, base_url):
    """Guard: the e2e server must be the in-memory one, never the live DB."""
    resp = page.request.get(base_url + "/api/v1/health")
    assert resp.status == 200
    assert resp.json()["checks"]["database"] == "not_configured"


def test_landing_page_loads(page: Page, base_url):
    page.goto(base_url + "/")
    expect(page).to_have_title(re.compile("CricNetra"))
    expect(page.get_by_role("link", name=re.compile("Contact")).first).to_be_visible()
    # hero "Watch live" CTA + clickable "live now" pill both route to the live directory
    watch = page.locator("a.btn-live")
    expect(watch).to_be_visible()
    assert watch.get_attribute("href") == "/live-matches"
    assert page.locator("a#heroLive").get_attribute("href") == "/live-matches"


def test_spa_boots_without_js_errors(page: Page, base_url, js_errors):
    page.goto(base_url + "/app")
    # Home renders its quick-action grid.
    expect(page.get_by_text("New match").first).to_be_visible()
    # A logged-out boot still has a Sign in chip.
    expect(page.get_by_role("link", name=re.compile("Sign in")).first).to_be_visible()
    assert js_errors == [], f"unexpected JS errors on /app: {js_errors}"


def test_login_page_renders(page: Page, base_url):
    page.goto(base_url + "/login")
    expect(page.locator("#identifier")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()
    expect(page.get_by_role("button", name=re.compile("Sign in"))).to_be_visible()


def test_register_page_renders(page: Page, base_url):
    page.goto(base_url + "/register")
    expect(page.locator("#username")).to_be_visible()
    expect(page.locator("#role")).to_be_visible()
    expect(page.get_by_text("Create your account")).to_be_visible()


@pytest.mark.parametrize(
    "path", ["/contact", "/tools", "/tips", "/live-matches", "/tournaments"]
)
def test_public_pages_load(page: Page, base_url, path):
    resp = page.goto(base_url + path)
    assert resp is not None and resp.ok, f"{path} -> {resp.status if resp else 'no response'}"
    # Every marketing page carries the CricNetra brand in its chrome.
    expect(page.get_by_text(re.compile("CricNetra")).first).to_be_visible()


def test_spa_navigation_to_teams(page: Page, base_url, js_errors):
    page.goto(base_url + "/app#/teams")
    # The Teams view renders (heading or a create-team control), empty data is fine.
    expect(page.get_by_text(re.compile("Teams", re.I)).first).to_be_visible()
    assert js_errors == [], f"unexpected JS errors navigating to Teams: {js_errors}"


def test_register_flow_signs_in(page: Page, base_url, js_errors):
    """Full browser flow: register -> auto-login -> redirected into /app with a token."""
    page.goto(base_url + "/register")
    page.fill("#full_name", "E2E Smoke User")
    page.fill("#username", "e2esmoke1")
    page.fill("#mobile_no", "9000000001")
    page.fill("#email", "e2esmoke1@example.com")
    page.fill("#password", "secret123")
    page.select_option("#role", "general_user")
    page.click("#registerForm button[type=submit]")

    page.wait_for_url(re.compile(r".*/app"), timeout=15000)
    token = page.evaluate("() => localStorage.getItem('cn_token')")
    assert token, "expected a JWT in localStorage after registration"
    assert js_errors == [], f"unexpected JS errors during register flow: {js_errors}"


def test_account_email_can_be_updated(page: Page, base_url, js_errors):
    """A signed-in user can add/change their email on the account screen."""
    page.goto(base_url + "/register")
    page.fill("#full_name", "Acct Emailer")
    page.fill("#username", "acctemail1")
    page.fill("#mobile_no", "9000000044")
    page.fill("#email", "acctemail1@example.com")
    page.fill("#password", "secret123")
    page.select_option("#role", "general_user")
    page.click("#registerForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    page.goto(base_url + "/app#/account")
    page.reload()  # hash-only goto may not re-route; reload boots straight into #/account
    # email input is pre-filled with the address chosen at signup
    expect(page.locator("#emailInput")).to_have_value("acctemail1@example.com", timeout=15000)
    # change it and save
    page.fill("#emailInput", "changed1@example.com")
    page.click("#emailSave")
    page.wait_for_timeout(800)
    email = page.evaluate(
        "async () => (await (await fetch('/api/v1/auth/me', "
        "{headers: {Authorization: 'Bearer ' + localStorage.getItem('cn_token')}})).json()).email"
    )
    assert email == "changed1@example.com", f"email not persisted, got {email!r}"
    assert js_errors == [], f"unexpected JS errors: {js_errors}"


def test_register_shows_clean_validation_error(page: Page, base_url):
    """A bad field shows a readable, field-labelled message — never the raw 422 JSON."""
    page.goto(base_url + "/register")
    page.fill("#full_name", "Bad Mobile")
    page.fill("#username", "badmob1")
    page.fill("#mobile_no", "123")  # too short
    page.fill("#email", "badmob1@example.com")
    page.fill("#password", "secret123")
    page.select_option("#role", "general_user")
    page.click("#registerForm button[type=submit]")
    err = page.locator("#authMsg")
    expect(err).to_contain_text("Mobile number", timeout=10000)
    body = err.inner_text()
    assert "value_error" not in body and "[{" not in body, f"raw JSON leaked: {body}"


def test_register_accepts_plus_prefixed_mobile(page: Page, base_url):
    """A '+91 …' number is accepted (normalised) and signs the user in."""
    page.goto(base_url + "/register")
    page.fill("#full_name", "Plus Mobile")
    page.fill("#username", "plusmob1")
    page.fill("#mobile_no", "+91 90000-12345")
    page.fill("#email", "plusmob1@example.com")
    page.fill("#password", "secret123")
    page.select_option("#role", "general_user")
    page.click("#registerForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)
    assert page.evaluate("() => localStorage.getItem('cn_token')"), "expected a token after sign-up"


def test_sidebar_brand_lockup(page: Page, base_url):
    """The sidebar brand renders the wordmark lockup: uppercase CRIC (ink) + NETRA
    (green), a green trajectory underline with a dot, and the tagline."""
    page.set_viewport_size({"width": 1280, "height": 900})  # desktop -> sidebar visible
    page.goto(base_url + "/app")
    word = page.locator(".brand-word")
    expect(word).to_be_visible(timeout=10000)
    assert word.inner_text() == "CRICNETRA", word.inner_text()  # uppercase
    netra = page.evaluate("() => getComputedStyle(document.querySelector('.brand-word .cn-hl')).color")
    crick = page.evaluate("() => getComputedStyle(document.querySelector('.brand-word')).color")
    assert netra != crick, (netra, crick)  # NETRA is a different (accent) colour from CRIC
    # the green underline + dot, and the tagline
    expect(page.locator(".brand-line")).to_have_count(1)
    dot = page.evaluate("() => getComputedStyle(document.querySelector('.brand-line'), '::after').backgroundColor")
    assert dot.startswith("rgb") and dot != "rgba(0, 0, 0, 0)", dot
    # the FULL tagline (incl. "cricket"), and it isn't clipped by the sidebar width
    sub = page.locator(".brand-sub")
    expect(sub).to_contain_text("cricket scoring", ignore_case=True)
    clipped = page.evaluate("() => { const e = document.querySelector('.brand-sub'); return e.scrollWidth > e.clientWidth + 2; }")
    assert not clipped, "tagline overflows / is clipped in the sidebar"


def test_brand_lockup_on_public_and_auth_pages(page: Page, base_url):
    """The trajectory-line + tagline lockup also appears on the marketing nav and
    the login/register hero."""
    page.set_viewport_size({"width": 1280, "height": 900})
    # marketing nav brand
    page.goto(base_url + "/")
    expect(page.locator(".brand-line").first).to_be_visible(timeout=10000)
    dot = page.evaluate("() => getComputedStyle(document.querySelector('.brand-line'), '::after').backgroundColor")
    assert dot.startswith("rgb") and dot != "rgba(0, 0, 0, 0)", dot
    expect(page.locator(".brand-tag").first).to_contain_text("cricket scoring", ignore_case=True)
    # auth (login): the top-left brand (always visible, above the form) shows the
    # lockup, and so does the hero panel
    page.goto(base_url + "/login")
    expect(page.locator(".auth-brand .brand-line")).to_be_visible(timeout=10000)
    expect(page.locator(".ab-sub")).to_contain_text("cricket scoring", ignore_case=True)
    expect(page.locator(".auth-hero-brand .brand-line")).to_be_visible()
    expect(page.locator(".auth-hero-brand small")).to_contain_text("cricket scoring", ignore_case=True)


def test_landing_mvp_card_below_team_header(page: Page, base_url):
    """The floating MVP card sits in the lower half of the phone mockup, not over
    the team-name header it used to cover."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/")
    card = page.locator(".dv-float.f1")
    expect(card).to_be_visible(timeout=10000)
    # it used to resolve to ~64px (over the header); now it's down near the bottom
    top_px = page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.dv-float.f1')).top)")
    assert top_px > 400, f"MVP card not moved down enough: top={top_px}px"
    cb = card.bounding_box()
    hb = page.locator(".dv-top").bounding_box()
    ob = page.locator("#dvOver").bounding_box()
    assert cb["y"] >= hb["y"] + hb["height"] - 20, ("over header", cb, hb)        # below the team header
    assert cb["y"] >= ob["y"] + ob["height"] - 8, ("over THIS OVER", cb, ob)      # below the "This over" chips


def test_logo_intro_animation(page: Page, base_url):
    """The brand lockup has an intro animation (wordmark rises, trajectory line
    draws, tagline fades) that settles to fully visible."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/login")
    anim = page.evaluate("""() => ({
      top: getComputedStyle(document.querySelector('.ab-top')).animationName,
      line: getComputedStyle(document.querySelector('.auth-brand .brand-line')).animationName,
      sub: getComputedStyle(document.querySelector('.ab-sub')).animationName,
    })""")
    assert "cn-rise" in anim["top"], anim
    assert "cn-draw" in anim["line"], anim
    assert "cn-fade" in anim["sub"], anim
    # once it finishes, the lockup is fully settled (visible, line undrawn-clip cleared)
    page.wait_for_timeout(1700)
    expect(page.locator(".ab-top")).to_be_visible()
    assert page.evaluate("() => getComputedStyle(document.querySelector('.ab-sub')).opacity") == "1"
    clip = page.evaluate("() => getComputedStyle(document.querySelector('.auth-brand .brand-line')).clipPath")
    assert "100%" not in clip, f"line still clipped after animation: {clip}"  # fully drawn


def test_account_chip_shows_uploaded_photo(page: Page, base_url):
    """Once a user uploads a profile picture, the top-bar account chip shows the
    photo (an <img>) instead of the initials avatar."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    res = page.evaluate("""async () => {
      const png = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAEklEQVR42mNk+M9Qz0BkYBxVSFwFAA5wBAX8T2i1AAAAAElFTkSuQmCC';
      const blob = await (await fetch(png)).blob();
      const fd = new FormData(); fd.append('file', new File([blob], 'p.png', {type: 'image/png'}));
      const t = localStorage.getItem('cn_token');
      const up = await fetch('/api/v1/auth/profile/photo', {method: 'POST', headers: {Authorization: 'Bearer ' + t}, body: fd});
      const me = await (await fetch('/api/v1/auth/me', {headers: {Authorization: 'Bearer ' + t}})).json();
      return {status: up.status, id: me.id, has_photo: me.has_photo};
    }""")
    assert res["status"] in (200, 201, 204), res
    assert res["has_photo"] is True, res

    page.reload()
    chip_img = page.locator(".js-authchip img.avatar").first
    expect(chip_img).to_be_visible(timeout=10000)  # the photo <img>, not the initials span
    src = chip_img.get_attribute("src")
    assert "/users/" in src and "/photo" in src, src


def test_venues_directory_search_by_name_and_voice(page: Page, base_url, js_errors):
    """Grounds & academies directory (#145): a venue is findable by NAME through the
    q= filter, the box uses the shared .search-row layout, and a voice mic is wired
    on wherever the browser supports speech."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    # seed a venue via the API using the admin token
    status = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const r = await fetch('/api/v1/venues', {method: 'POST',
        headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + t},
        body: JSON.stringify({name: 'Brabourne Oval', kind: 'ground', city: 'Mumbai'})});
      return r.status;
    }""")
    assert status in (200, 201), status

    page.goto(base_url + "/app#/venues")
    page.reload()  # boot straight into the venues route
    expect(page.get_by_text("Brabourne Oval").first).to_be_visible(timeout=15000)

    filt = page.locator("#v_filter")
    expect(filt).to_be_visible()
    assert "Search grounds" in (filt.get_attribute("placeholder") or "")
    assert filt.evaluate("el => !!el.closest('.search-row')")  # shared voice-search layout

    # searching by NAME (not just city) keeps it; a nonsense term hides it
    filt.fill("brabourne")
    expect(page.get_by_text("Brabourne Oval").first).to_be_visible(timeout=10000)
    filt.fill("zzq-no-such-venue")
    expect(page.get_by_text("Brabourne Oval")).to_have_count(0, timeout=10000)

    # a voice mic is attached where the browser exposes the Speech API — on the
    # directory box and tucked inside the desktop header search field
    if page.evaluate("() => !!(window.SpeechRecognition || window.webkitSpeechRecognition)"):
        expect(page.locator(".search-row .mic-btn").first).to_be_visible()
        expect(page.locator(".app-search .mic-btn")).to_be_visible()
        tucked = page.evaluate("""() => {
          const hs = document.getElementById('hdrSearch');
          const m = hs.parentElement.querySelector('.mic-btn');
          const f = hs.getBoundingClientRect(), b = m.getBoundingClientRect();
          return getComputedStyle(m).position === 'absolute'
              && b.right <= f.right + 1 && b.left > f.left + f.width / 2;  // sits inside, right-aligned
        }""")
        assert tucked, "header voice mic not tucked inside the search field"


def test_settings_theme_picker(page: Page, base_url, js_errors):
    """Settings → Theme (#149): the sidebar Settings link opens a picker of named
    palettes; choosing one applies it live via html[data-theme], persists across a
    reload (no-flash pre-paint), and the header sun/moon toggle flips light↔dark."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/app#/settings")
    page.reload()  # boot straight into the settings route

    cards = page.locator(".theme-card")
    expect(cards.first).to_be_visible(timeout=15000)
    assert cards.count() == 12, cards.count()  # 3 dark + 9 light

    accent = "() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()"
    data_theme = "() => document.documentElement.getAttribute('data-theme')"
    # default is Emerald (no attribute) with the signature green accent
    assert page.evaluate(accent) == "#2fe08a", page.evaluate(accent)

    # choosing Midnight Ocean applies live + marks the card + persists
    page.locator('.theme-card[data-theme-id="ocean"]').click()
    assert page.evaluate(data_theme) == "ocean"
    assert page.evaluate(accent) == "#34c8ff"
    expect(page.locator('.theme-card[data-theme-id="ocean"]')).to_have_class(re.compile(r"\bactive\b"))
    assert page.evaluate("() => localStorage.getItem('cn_theme')") == "ocean"

    # survives a reload (pre-paint sets the attribute before app.js runs)
    page.reload()
    expect(page.locator(".theme-card").first).to_be_visible(timeout=15000)
    assert page.evaluate(data_theme) == "ocean"

    # a light theme flips the background light
    page.locator('.theme-card[data-theme-id="sky"]').click()
    assert page.evaluate(data_theme) == "sky"
    assert page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()") == "#eef6fb"

    # header sun/moon toggle: from a light theme it restores the last dark one (ocean)
    page.locator(".app-header .js-theme").first.click()
    assert page.evaluate(data_theme) == "ocean"

    # the sidebar Settings link is present (desktop) and marked active on this route
    side = page.locator('.side-link[data-side="settings"]')
    expect(side).to_be_visible()
    expect(side).to_have_class(re.compile(r"\bactive\b"))


def test_match_bring_your_own_stream(page: Page, base_url, js_errors):
    """Live streaming Option A (#145): the owner attaches a YouTube link to a match;
    it embeds (as the official /embed/ URL) on the scoring screen and the public page.
    No video touches our servers — we only store + safely embed the link."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    # create a match + attach a YouTube watch URL through the API (admin = owner)
    mid = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const m = await (await fetch('/api/v1/matches', {method: 'POST', headers: H,
        body: JSON.stringify({team_a: 'Strikers', team_b: 'Blasters', format_id: 't20', bat_first: 'a'})})).json();
      const r = await fetch('/api/v1/matches/' + m.id + '/stream', {method: 'PUT', headers: H,
        body: JSON.stringify({stream_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'})});
      return {id: m.id, kind: (await r.json()).stream.kind};
    }""")
    assert mid["kind"] == "youtube", mid

    # scoring screen: the embed iframe points at the official YouTube embed URL
    page.goto(base_url + "/app#/match/" + str(mid["id"]))
    page.reload()
    frame = page.locator(".stream-embed iframe")
    expect(frame).to_be_visible(timeout=15000)
    assert "youtube.com/embed/dQw4w9WgXcQ" in (frame.get_attribute("src") or "")
    expect(page.locator("#streamUrl")).to_be_visible()  # owner control to change/clear it

    # shared public page embeds it too
    page.goto(base_url + "/m/" + str(mid["id"]))
    pub_frame = page.locator(".stream-embed iframe")
    expect(pub_frame).to_be_visible(timeout=10000)
    assert "youtube.com/embed/dQw4w9WgXcQ" in (pub_frame.get_attribute("src") or "")


def test_match_auto_highlights(page: Page, base_url, js_errors):
    """Auto highlights (Option B, #145): a scored match produces a key-moments reel
    (wickets/boundaries) with no video — on the scoring screen (filterable) and the
    public page's Highlights tab."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    mid = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const post = (u, b) => fetch(u, {method: 'POST', headers: H, body: JSON.stringify(b)});
      const m = await (await post('/api/v1/matches', {team_a: 'Alpha', team_b: 'Bravo', format_id: 't20', bat_first: 'a'})).json();
      await post('/api/v1/matches/' + m.id + '/bowler', {bowler: 'Bravo 1'});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 6});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 4});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'wicket', dismissal: 'bowled'});
      return m.id;
    }""")
    assert mid

    # scoring screen: the reel shows the six, four and wicket
    page.goto(base_url + "/app#/match/" + str(mid))
    page.reload()
    hl = page.locator("#hlList")
    expect(hl.locator(".hl-item.hl-six")).to_be_visible(timeout=15000)
    expect(hl.locator(".hl-item.hl-four")).to_be_visible()
    expect(hl.locator(".hl-item.hl-wicket")).to_be_visible()
    # filtering to Wickets drops the boundaries
    page.locator('.hlf[data-f="wickets"]').click()
    expect(hl.locator(".hl-item.hl-six")).to_have_count(0)
    expect(hl.locator(".hl-item.hl-wicket")).to_be_visible()

    # public page: the Highlights tab shows the same moments
    page.goto(base_url + "/m/" + str(mid))
    page.locator('.tab[data-tab="highlights"]').click()
    expect(page.locator('[data-panel="highlights"] .hl-item.hl-six')).to_be_visible(timeout=10000)


def test_innings_break_start_second_innings(page: Page, base_url, js_errors):
    """When the first innings ends, a prominent 'Start 2nd innings' action sits right
    under the scoreboard (in .match-left) instead of being buried at the bottom of the
    column — and clicking it actually transitions to innings 2."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    # A one-over match: the first innings ends after 6 legal balls, deterministically.
    mid = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const post = (u, b) => fetch(u, {method: 'POST', headers: H, body: JSON.stringify(b)});
      const m = await (await post('/api/v1/matches', {team_a: 'Alpha', team_b: 'Bravo',
        bat_first: 'a', rules: {overs_per_innings: 1}})).json();
      await post('/api/v1/matches/' + m.id + '/bowler', {bowler: 'Bravo 1'});
      for (let i = 0; i < 6; i++) await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 1});
      const st = await (await fetch('/api/v1/matches/' + m.id, {headers: {Authorization: 'Bearer ' + t}})).json();
      return {id: m.id, can: st.can_start_second_innings, inn: st.current_innings};
    }""")
    assert mid["can"] is True, mid  # first innings really is complete
    assert mid["inn"] == 1

    page.goto(base_url + "/app#/match/" + str(mid["id"]))
    page.reload()

    # The action is prominent and lives in the left (scoreboard) column, not buried.
    btn = page.locator(".match-left .ibreak #secondBtn")
    expect(btn).to_be_visible(timeout=15000)
    btn.click()

    # It really starts innings 2: the break card clears and the state advances.
    expect(page.locator(".ibreak")).to_have_count(0, timeout=10000)
    state = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const st = await (await fetch('/api/v1/matches/%s', {headers: {Authorization: 'Bearer ' + t}})).json();
      return {inn: st.current_innings, can: st.can_start_second_innings};
    }""" % mid["id"])
    assert state["inn"] == 2, state
    assert state["can"] is False


def test_admin_can_delete_content(page: Page, base_url, js_errors):
    """The Admin panel lists matches/tournaments/teams/players and deletes any of
    them (deletion is admin-only server-side; this is the admin's tool for it)."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    mid = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const m = await (await fetch('/api/v1/matches', {method: 'POST', headers: H,
        body: JSON.stringify({team_a: 'DelMe', team_b: 'Gone', bat_first: 'a'})})).json();
      return m.id;
    }""")
    assert mid

    page.on("dialog", lambda d: d.accept())  # accept the "delete?" confirm()
    page.goto(base_url + "/app#/admin")
    page.reload()

    # Matches is the default tab; delete our match by its row
    row = page.locator(f'#admList [data-row="{mid}"]')
    expect(row).to_be_visible(timeout=15000)
    row.locator(".adm-del").click()
    expect(page.locator(f'#admList [data-row="{mid}"]')).to_have_count(0, timeout=10000)

    # it's really gone on the server
    status = page.evaluate("""async (mid) => {
      const t = localStorage.getItem('cn_token');
      return (await fetch('/api/v1/matches/' + mid, {headers: {Authorization: 'Bearer ' + t}})).status;
    }""", str(mid))
    assert status == 404


def test_public_header_responsive_across_dimensions(page: Page, base_url, js_errors):
    """The marketing header must collapse to a hamburger BEFORE the 7-link nav can
    overlap the brand — checked from large desktop down to a 320px phone. Regression
    for 'Live Scores overwriting CRICNETRA' and any horizontal overflow."""
    probe = """() => {
      const q = s => document.querySelector(s);
      const R = e => e.getBoundingClientRect();
      const brand = q('.brand'), links = q('.nav-links'), burger = q('.nav-burger'), actions = q('.nav-actions');
      const inline = getComputedStyle(links).position === 'static' && getComputedStyle(links).display !== 'none';
      let overlap = false;
      if (inline) overlap = (R(brand).right > R(links).left + 1) || (R(links).right > R(actions).left + 1);
      return {
        bodyOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        burgerShown: getComputedStyle(burger).display !== 'none',
        actionsRight: Math.round(R(actions).right), inline, overlap,
      };
    }"""
    # desktop, laptop, small-laptop, tablet-landscape, the old broken zone, iPad,
    # large phone, standard phone, small phone
    for w in (1440, 1280, 1100, 1024, 820, 768, 414, 375, 320):
        page.set_viewport_size({"width": w, "height": 800})
        page.goto(base_url + "/")
        m = page.evaluate(probe)
        assert m["bodyOverflow"] <= 1, (w, m)               # no horizontal scrollbar
        assert not m["overlap"], (w, m)                     # brand never overlapped
        assert m["actionsRight"] <= w + 1, (w, m)           # actions never run off-screen
        if w <= 1024:
            assert m["burgerShown"], (w, m)                 # collapsed to a hamburger
        else:
            assert not m["burgerShown"] and m["inline"], (w, m)  # inline nav shown


def test_match_shows_partnerships_and_pdf_button(page: Page, base_url, js_errors):
    """The scorecard shows the partnership breakdown (biggest stand badged 'Best')
    plus a 'Download PDF' action that points at the public scorecard."""
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    mid = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const post = (u, b) => fetch(u, {method: 'POST', headers: H, body: JSON.stringify(b)}).then(r => r.json());
      const m = await post('/api/v1/matches', {team_a: 'Alpha', team_b: 'Bravo', bat_first: 'a'});
      await post('/api/v1/matches/' + m.id + '/bowler', {bowler: 'Bravo 1'});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 6});   // opening stand
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'wicket', dismissal: 'bowled'});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 4});   // 2nd stand
      return m.id;
    }""")

    page.goto(base_url + "/app#/match/" + str(mid))
    page.reload()
    rows = page.locator(".pnr-card .pnr-row")
    expect(rows.first).to_be_visible(timeout=15000)
    assert rows.count() >= 2                                   # 1st + open 2nd stand
    expect(page.locator(".pnr-card .pnr-best")).to_have_count(1)  # exactly one 'Best'
    pdf = page.locator("#pdfBtn")
    expect(pdf).to_be_visible()
    pdf.click()  # opens the premium scorecard report with ?print=1 in a new tab
    page.wait_for_timeout(600)
    printed = [p for p in page.context.pages if "print=1" in p.url]
    assert printed and f"/scorecard/{mid}" in printed[0].url, [p.url for p in page.context.pages]
    for p in printed:
        p.close()


def test_mobile_nav_drawer_matches_desktop_sidebar(page: Page, base_url, js_errors):
    """On phones the ☰ drawer must expose the SAME navigation as the desktop rail —
    Players, Venues, Custom rules, Leaderboards, Highlights, Network, Feed, Messages,
    Looking For, Search, Settings, Admin are otherwise unreachable from the 4-tab bar."""
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    sides_js = "els => els.filter(e => getComputedStyle(e).display !== 'none').map(e => e.dataset.side)"

    # desktop: fixed rail, no hamburger
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/app?d=1#/")
    page.wait_for_timeout(500)
    expect(page.locator("#sidebar")).to_be_visible()
    expect(page.locator("#menuBtn")).to_be_hidden()
    desktop_sides = page.locator("#sidebar .side-link").evaluate_all(sides_js)
    assert "highlights" in desktop_sides and len(desktop_sides) >= 10, desktop_sides

    # mobile: rail is off-canvas, hamburger reveals the identical nav
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/app?m=1#/")
    page.wait_for_timeout(500)
    expect(page.locator("#menuBtn")).to_be_visible()
    expect(page.locator("#sidebar")).to_be_hidden()          # closed drawer
    page.click("#menuBtn")
    expect(page.locator("#sidebar")).to_be_visible(timeout=5000)
    drawer_sides = page.locator("#sidebar .side-link").evaluate_all(sides_js)
    assert drawer_sides == desktop_sides, (drawer_sides, desktop_sides)

    # tapping a drawer link navigates and closes the drawer
    page.click('#sidebar .side-link[data-side="highlights"]')
    expect(page.locator("#sidebar")).to_be_hidden(timeout=5000)
    assert page.url.endswith("#/highlights"), page.url

    # the scrim also closes it
    page.click("#menuBtn")
    expect(page.locator("#sidebar")).to_be_visible(timeout=5000)
    page.locator("#navScrim").click(position={"x": 340, "y": 400})
    expect(page.locator("#sidebar")).to_be_hidden(timeout=5000)


def test_public_site_link_reachable_from_app_on_mobile(page: Page, base_url, js_errors):
    """You must be able to get back OUT of the app to the public site on a phone.
    The app header ("Public site ↗") and app footer links are desktop-only, so the
    nav drawer carries the link — otherwise mobile users are stuck in /app."""
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    # desktop: the header link is the way out, and the sidebar carries it too
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/app?pd=1#/")
    page.wait_for_timeout(500)
    expect(page.locator(".app-header__pub")).to_be_visible()
    expect(page.locator("#sidebar .side-pub")).to_be_visible()

    # mobile: that desktop chrome is hidden — the drawer must carry the link
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/app?pm=1#/")
    page.wait_for_timeout(600)
    expect(page.locator(".app-header__pub")).to_be_hidden()
    expect(page.locator("#appFooter")).to_be_hidden()

    page.click("#menuBtn")
    pub = page.locator("#sidebar .side-pub")
    expect(pub).to_be_visible(timeout=5000)
    assert pub.get_attribute("href") == "/", pub.get_attribute("href")
    # it must navigate in the SAME tab, not spawn a new one
    assert pub.get_attribute("target") is None, pub.get_attribute("target")
    assert page.locator(".app-header__pub").get_attribute("target") is None

    # tapping it really lands on the public site, in this same tab
    pub.click()
    page.wait_for_url(lambda u: "/app" not in u, timeout=10000)
    expect(page.locator(".nav .brand")).to_be_visible(timeout=10000)
    assert len(page.context.pages) == 1, "should not have opened a new tab"


def test_match_highlight_clips(page: Page, base_url, js_errors):
    """Bring-your-own highlight clips (Option B video, #145): the organizer/admin
    attaches a YouTube link from the in-app Highlights hub (#/highlights). It embeds
    in the hub gallery, shows READ-ONLY on the match screen (no add controls there
    anymore), and appears on the public Highlights tab. No video touches our servers."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    mid = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const m = await (await fetch('/api/v1/matches', {method: 'POST', headers: H,
        body: JSON.stringify({team_a: 'Clipper', team_b: 'Bravo', format_id: 't20', bat_first: 'a'})})).json();
      return m.id;
    }""")
    assert mid

    # the Highlights hub is reachable from the sidebar and hosts clip management now
    page.goto(base_url + "/app#/highlights")
    page.reload()
    expect(page.locator('.side-link[data-side="highlights"]')).to_be_visible(timeout=15000)
    sel = page.locator("#hlMatchSel")
    expect(sel).to_be_visible(timeout=15000)
    sel.select_option(str(mid))
    add_url = page.locator("#hlMatchClips #clipUrl")
    expect(add_url).to_be_visible(timeout=10000)
    add_url.fill("https://youtu.be/dQw4w9WgXcQ")
    page.locator("#hlMatchClips #clipLabel").fill("Last-ball six")
    page.locator("#hlMatchClips #clipAdd").click()

    # embeds in the manage panel (scoped to the selected match) + appears in the gallery
    mgmt = page.locator("#hlMatchClips .clip .stream-embed iframe").first
    expect(mgmt).to_be_visible(timeout=10000)
    assert "youtube.com/embed/dQw4w9WgXcQ" in (mgmt.get_attribute("src") or "")
    expect(page.locator(f'#hlGallery a.hl-ghead[href="#/match/{mid}"]')).to_be_visible(timeout=10000)

    # the match screen shows the clip READ-ONLY: gallery iframe present, no add control
    page.goto(base_url + "/app#/match/" + str(mid))
    page.reload()
    mclip = page.locator("#clipArea .clip .stream-embed iframe")
    expect(mclip).to_be_visible(timeout=15000)
    assert "youtube.com/embed/dQw4w9WgXcQ" in (mclip.get_attribute("src") or "")
    assert page.locator("#clipArea #clipUrl").count() == 0  # management moved to the hub

    # public page: the Highlights tab embeds the clip too
    page.goto(base_url + "/m/" + str(mid))
    page.locator('.tab[data-tab="highlights"]').click()
    pub = page.locator('[data-panel="highlights"] .clip .stream-embed iframe')
    expect(pub).to_be_visible(timeout=10000)
    assert "youtube.com/embed/dQw4w9WgXcQ" in (pub.get_attribute("src") or "")


def _ffmpeg_bin():
    import glob
    import shutil
    f = shutil.which("ffmpeg")
    if f:
        return f
    hits = glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet",
                                  "Packages", "Gyan.FFmpeg*", "*", "bin", "ffmpeg.exe"))
    return hits[0] if hits else None


def test_match_auto_clipped_video(page: Page, base_url, js_errors, tmp_path):
    """Actual auto-clipped video (Option B #1, #145): upload a match recording,
    and the server ffmpeg-cuts a clip around every key moment, synced to the ball
    log via per-ball timestamps. The clips play inline on the scoring screen."""
    import base64
    import subprocess

    ff = _ffmpeg_bin()
    if not ff:
        pytest.skip("ffmpeg not installed on this machine")
    vid = tmp_path / "rec.mp4"
    subprocess.run([ff, "-y", "-f", "lavfi", "-i", "testsrc=duration=25:size=320x240:rate=15",
                    "-c:v", "libx264", str(vid)], capture_output=True, check=True)
    b64 = base64.b64encode(vid.read_bytes()).decode()

    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    # create + score a match (six, four, wicket → three key moments)
    mid = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const post = (u, b) => fetch(u, {method: 'POST', headers: H, body: JSON.stringify(b)});
      const m = await (await post('/api/v1/matches', {team_a: 'Alpha', team_b: 'Bravo', format_id: 't20', bat_first: 'a'})).json();
      await post('/api/v1/matches/' + m.id + '/bowler', {bowler: 'Bravo 1'});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 6});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 4});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'wicket', dismissal: 'bowled'});
      return m.id;
    }""")

    # upload the recording, then auto-generate clips (anchor: first ball at 5s)
    res = page.evaluate("""async ([mid, b64]) => {
      const t = localStorage.getItem('cn_token');
      const bin = atob(b64); const arr = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      const fd = new FormData(); fd.append('file', new File([arr], 'm.mp4', {type: 'video/mp4'}));
      const up = await fetch('/api/v1/matches/' + mid + '/recording', {method: 'POST', headers: {Authorization: 'Bearer ' + t}, body: fd});
      const gen = await fetch('/api/v1/matches/' + mid + '/clips/auto', {method: 'POST',
        headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + t}, body: JSON.stringify({anchor: 5})});
      return {up: up.status, gen: gen.status, clips: await gen.json()};
    }""", [str(mid), b64])
    assert res["up"] == 201, res
    assert res["gen"] == 201, res
    assert sum(1 for c in res["clips"] if c["source"] == "auto") >= 3, res

    # the auto-cut clips play inline on the scoring screen
    page.goto(base_url + "/app#/match/" + str(mid))
    page.reload()
    clip = page.locator("#clipArea .clip video").first
    expect(clip).to_be_visible(timeout=15000)
    # and they SURVIVE scoring: mark the video, score a single, confirm the same node remains
    page.evaluate("() => document.querySelector('#clipArea .clip video').setAttribute('data-alive', '1')")
    old = page.locator(".score__runs").inner_text()
    page.locator('.padbtn[data-v="1"]').first.click()
    expect(page.locator(".score__runs")).not_to_have_text(old, timeout=10000)
    assert page.locator('#clipArea .clip video[data-alive="1"]').count() == 1  # never re-created


def test_stream_survives_scoring(page: Page, base_url, js_errors):
    """Scoring must NOT reload the live stream: the <iframe> lives in a persistent
    #streamHost, so recording a delivery re-renders the body but leaves it playing."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    mid = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const post = (u, b) => fetch(u, {method: 'POST', headers: H, body: JSON.stringify(b)});
      const m = await (await post('/api/v1/matches', {team_a: 'Alpha', team_b: 'Bravo', format_id: 't20', bat_first: 'a'})).json();
      await post('/api/v1/matches/' + m.id + '/bowler', {bowler: 'Bravo 1'});
      await fetch('/api/v1/matches/' + m.id + '/stream', {method: 'PUT', headers: H, body: JSON.stringify({stream_url: 'https://youtu.be/dQw4w9WgXcQ'})});
      return m.id;
    }""")

    page.goto(base_url + "/app#/match/" + str(mid))
    page.reload()
    frame = page.locator("#streamHost .stream-embed iframe")
    expect(frame).to_be_visible(timeout=15000)
    # tag the live iframe; if a score re-creates it, this runtime marker disappears
    page.evaluate("() => document.querySelector('#streamHost .stream-embed iframe').setAttribute('data-alive', '1')")

    # score a single through the pad → full body re-render
    page.locator('.padbtn[data-v="1"]').first.click()
    expect(page.locator(".score__runs")).to_contain_text("1/0", timeout=10000)

    # the SAME iframe is still there (marker survived) → the stream never reloaded
    assert page.locator('#streamHost .stream-embed iframe[data-alive="1"]').count() == 1
