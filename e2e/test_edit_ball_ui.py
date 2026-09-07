"""Edit-a-delivery UI flow.

Drives the real ✎ "Correct this delivery" button on the ball-by-ball feed in a
headless browser, against the hermetic in-memory server, and asserts the
event-sourced score recomputes. Reproduces the user-reported "updating a
delivery doesn't work" path end to end (feed idx -> modal -> PUT -> refresh).

Signs in as the seeded admin (CRICNETRA_SEED_ADMIN), who can create/score/edit
any match — self-registration only yields a viewer-level role.
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
    token = page.evaluate("() => localStorage.getItem('cn_token')")
    assert token, "expected a JWT after admin login"


def _api(page: Page, method: str, path: str, body=None):
    """Call /api/v1 from the page with the stored bearer token."""
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


def test_edit_delivery_via_feed_ui(page: Page, base_url, js_errors):
    _login_admin(page, base_url)

    # create a match, set the opening bowler, then score two balls: a 4 and a 1 (total 5).
    r = _api(page, "POST", "/matches",
             {"team_a": "A", "team_b": "B", "format_id": "t20", "bat_first": "a"})
    assert r["status"] == 201, r
    mid = r["data"]["id"]
    bowler = _api(page, "GET", f"/matches/{mid}")["data"]["available_bowlers"][0]
    assert _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": bowler})["status"] == 200
    assert _api(page, "POST", f"/matches/{mid}/balls", {"action": "runs", "value": 4})["status"] == 200
    assert _api(page, "POST", f"/matches/{mid}/balls", {"action": "runs", "value": 1})["status"] == 200

    # open the match screen in the SPA
    page.goto(base_url + f"/app#/match/{mid}")
    page.reload()  # hash-only nav may not re-route; reload boots straight into the match

    # the ball feed renders ✎ edit buttons for the live innings. Target the FIRST
    # delivery (idx 0, the 4) explicitly — the feed renders newest-first, so .first
    # in the DOM would be the most recent ball.
    expect(page.locator(".bbl-edit").first).to_be_visible(timeout=15000)
    edit_btn = page.locator('.bbl-edit[data-idx="0"]')
    expect(edit_btn).to_have_count(1)

    # click ✎ -> the correction modal opens
    edit_btn.click()
    expect(page.get_by_text("Correct this delivery")).to_be_visible(timeout=5000)

    # change the first ball 4 -> 6 (total should go 5 -> 7)
    page.locator(".modal").get_by_role("button", name="6", exact=True).click()

    # the user gets clear positive feedback...
    expect(page.locator("#toast")).to_contain_text("Delivery updated", timeout=5000)
    # ...the visible scoreboard re-renders with the corrected total (5 -> 7)...
    expect(page.locator(".score__runs").first).to_have_text("7/0", timeout=5000)
    # ...and it's actually persisted server-side (survives a fresh fetch / reload)
    runs = _api(page, "GET", f"/matches/{mid}")["data"]["innings"][0]["runs"]
    assert runs == 7, f"expected 7 runs after editing 4->6, got {runs}"
    assert js_errors == [], f"unexpected JS errors during edit: {js_errors}"


def test_no_ball_with_runs_off_bat_via_pad(page: Page, base_url, js_errors):
    """Tapping Nb opens the run chooser; picking 4 records a no-ball hit for four
    (1 penalty + 4 = 5), not just the penalty."""
    _login_admin(page, base_url)

    r = _api(page, "POST", "/matches",
             {"team_a": "A", "team_b": "B", "format_id": "t20", "bat_first": "a"})
    assert r["status"] == 201, r
    mid = r["data"]["id"]
    bowler = _api(page, "GET", f"/matches/{mid}")["data"]["available_bowlers"][0]
    assert _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": bowler})["status"] == 200

    page.goto(base_url + f"/app#/match/{mid}")
    page.reload()

    # tap the Nb pad button -> the run chooser opens
    nb = page.locator('.padbtn[data-act="noball"]')
    expect(nb).to_be_visible(timeout=15000)
    nb.click()
    expect(page.get_by_text("No-ball + runs off the bat")).to_be_visible(timeout=5000)

    # batter hit it for four
    page.locator(".modal").get_by_role("button", name="4", exact=True).click()

    # scoreboard shows 5/0 (1 penalty + 4), and it's still ball 0.0 (no-ball isn't legal)
    expect(page.locator(".score__runs").first).to_have_text("5/0", timeout=5000)
    data = _api(page, "GET", f"/matches/{mid}")["data"]["innings"][0]
    assert data["runs"] == 5 and data["legal_balls"] == 0, data
    assert data["batters"][0]["fours"] == 1, "the four off the no-ball should reach the batter"
    assert js_errors == [], f"unexpected JS errors during no-ball: {js_errors}"


def test_over_change_bowler_picker(page: Page, base_url, js_errors):
    """After an over the picker appears, never offers the bowler who just bowled,
    and stays available to change the choice until the first ball — so the scorer
    can never get trapped by a consecutive-overs error."""
    _login_admin(page, base_url)

    r = _api(page, "POST", "/matches",
             {"team_a": "A", "team_b": "B", "format_id": "t20", "bat_first": "a"})
    assert r["status"] == 201, r
    mid = r["data"]["id"]
    b0 = _api(page, "GET", f"/matches/{mid}")["data"]["available_bowlers"][0]
    assert _api(page, "POST", f"/matches/{mid}/bowler", {"bowler": b0})["status"] == 200
    for _ in range(6):  # bowl a full over
        assert _api(page, "POST", f"/matches/{mid}/balls", {"action": "runs", "value": 1})["status"] == 200

    page.goto(base_url + f"/app#/match/{mid}")
    page.reload()

    # the picker is shown and does NOT offer the bowler who just bowled
    sel = page.locator("#bowlerSel")
    expect(sel).to_be_visible(timeout=15000)
    options = sel.locator("option").all_inner_texts()
    assert b0 not in options, f"previous bowler {b0!r} should not be offered, got {options}"
    assert len(options) >= 1

    # pick an eligible bowler and start the over -> the run pad appears, and the
    # picker is still there (the choice can be changed until the first ball)
    page.select_option("#bowlerSel", options[0])
    page.click("#bowlerBtn")
    expect(page.locator('.padbtn[data-act="run"]').first).to_be_visible(timeout=10000)
    expect(page.locator("#bowlerSel")).to_be_visible()  # still changeable

    # bowl the first ball -> the picker goes away, scoring continues normally
    page.locator('.padbtn[data-act="run"][data-v="1"]').click()
    expect(page.locator("#bowlerSel")).to_have_count(0, timeout=10000)
    st = _api(page, "GET", f"/matches/{mid}")["data"]
    assert st["over_pending"] is False and st["innings"][0]["legal_balls"] == 7
    assert js_errors == [], f"unexpected JS errors during over change: {js_errors}"
