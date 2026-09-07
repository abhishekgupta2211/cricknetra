"""Tournament squad picker: a player already in one team's squad stays visible in
the other teams' pickers but is disabled and labelled with the team holding them
('one team per player'), instead of silently disappearing.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def _login_admin(page: Page, base_url: str) -> None:
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")  # seeded admin (CRICNETRA_SEED_ADMIN)
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)


def _api(page: Page, method: str, path: str, body=None):
    return page.evaluate(
        """async ({method, path, body}) => {
            const r = await fetch('/api/v1' + path, {
                method,
                headers: {'Content-Type': 'application/json',
                          'Authorization': 'Bearer ' + localStorage.getItem('cn_token')},
                body: body ? JSON.stringify(body) : undefined,
            });
            let data = null; try { data = await r.json(); } catch (e) {}
            return {status: r.status, data};
        }""",
        {"method": method, "path": path, "body": body},
    )


def test_squad_picker_disables_taken_player_with_reason(page: Page, base_url, js_errors):
    _login_admin(page, base_url)

    p_shared = _api(page, "POST", "/players", {"name": "shared player"})["data"]["id"]  # lowercase
    _api(page, "POST", "/players", {"name": "free agent"})  # stays selectable everywhere
    alpha = _api(page, "POST", "/teams", {"name": "Alpha"})["data"]["id"]
    blasters = _api(page, "POST", "/teams", {"name": "Blasters"})["data"]["id"]
    tid = _api(page, "POST", "/tournaments",
               {"name": "Cup", "format": "round_robin", "team_ids": [alpha, blasters]})["data"]["id"]
    # register the shared player into Blasters' squad
    assert _api(page, "POST", f"/tournaments/{tid}/teams/{blasters}/squad",
                {"player_id": p_shared})["status"] in (200, 201)

    page.goto(base_url + f"/app#/tournament/{tid}")
    page.reload()

    # Alpha's custom-dropdown picker
    picker = page.locator(f'.sq-pick[data-team="{alpha}"]')
    expect(picker).to_be_visible(timeout=15000)
    picker.locator(".cdd-trigger").click()  # open

    # the shared player is a DISABLED row: "CODE - Name" on the left, squad on the right
    taken = picker.locator(".cdd-opt--off", has_text="Shared Player")
    expect(taken).to_have_count(1)
    assert taken.locator(".cdd-main").inner_text().startswith("P"), taken.inner_text()
    expect(taken.locator(".cdd-tag")).to_have_text("in BLASTERS' squad")
    assert taken.get_attribute("data-value") is None  # not selectable
    # under the "Unavailable — one team per player" group header
    expect(picker.locator(".cdd-group", has_text="Unavailable")).to_have_count(1)
    # the free agent is a normal selectable row; "Create new" is offered
    expect(picker.locator(".cdd-opt[data-value]", has_text="Free Agent")).to_have_count(1)
    expect(picker.locator(".cdd-opt--accent", has_text="Create a new player")).to_have_count(1)
    assert js_errors == [], f"unexpected JS errors: {js_errors}"


def test_team_picker_dropdown_layout_and_membership(page: Page, base_url, js_errors):
    """The team roster picker is a custom dropdown: each row shows 'CODE · Name' on
    the left and the membership tag ('in MUMBAI') pushed to the RIGHT. The tag is
    informational; picking the player and adding still works."""
    _login_admin(page, base_url)

    p_multi = _api(page, "POST", "/players", {"name": "shared star"})["data"]["id"]  # lowercase on purpose
    _api(page, "POST", "/players", {"name": "lone wolf"})  # in no team
    mumbai = _api(page, "POST", "/teams", {"name": "Mumbai"})["data"]["id"]
    chennai = _api(page, "POST", "/teams", {"name": "Chennai"})["data"]["id"]
    assert _api(page, "POST", f"/teams/{mumbai}/members", {"player_id": p_multi})["status"] in (200, 201)

    page.goto(base_url + f"/app#/team/{chennai}")
    page.reload()

    picker = page.locator("#pickPlayer")
    expect(picker).to_be_visible(timeout=15000)
    picker.locator(".cdd-trigger").click()  # open the dropdown

    row = picker.locator(".cdd-opt", has_text="Shared Star")
    expect(row).to_have_count(1)
    main, tag = row.locator(".cdd-main"), row.locator(".cdd-tag")
    assert main.inner_text().startswith("P"), main.inner_text()   # code first
    assert " - Shared Star" in main.inner_text(), main.inner_text()  # "CODE - Name" (hyphen, not ·)
    expect(tag).to_have_text("in MUMBAI")                         # team uppercased on the right
    # the tag really is at the RIGHT of the row (space-between layout): right of the
    # name, and flush to the row's right edge (within the row's padding).
    assert "space-between" in page.evaluate(
        "() => getComputedStyle(document.querySelector('#pickPlayer .cdd-opt')).justifyContent")
    mb, tb, ob = main.bounding_box(), tag.bounding_box(), row.bounding_box()
    assert tb["x"] > mb["x"] + mb["width"] - 2, (mb, tb)                       # right of the name
    assert (ob["x"] + ob["width"]) - (tb["x"] + tb["width"]) < 24, (ob, tb)    # flush to the right edge
    # a player in no team has no right-side tag
    expect(picker.locator(".cdd-opt", has_text="Lone Wolf").locator(".cdd-tag")).to_have_count(0)

    # picking the player records the value and adding it works end to end
    row.click()
    assert page.evaluate("() => document.getElementById('pickPlayer').dataset.value") == p_multi
    page.locator("#addExisting").click()
    expect(page.locator("#sqCount")).to_have_text("1", timeout=10000)
    assert js_errors == [], f"unexpected JS errors: {js_errors}"
    assert js_errors == [], f"unexpected JS errors: {js_errors}"
