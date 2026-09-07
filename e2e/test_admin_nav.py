"""The Admin nav link is gated to admins: hidden for logged-out / non-admin users,
visible once an admin signs in.

Guards the regression where component CSS (`.side-link { display: flex }`) overrode
the `[hidden]` attribute, leaving the Admin link (and count badges) shown to everyone.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def test_admin_link_hidden_when_logged_out(page: Page, base_url):
    page.goto(base_url + "/app")
    # the link exists in the shell markup but must not be displayed
    link = page.locator(".js-admin-link").first
    expect(link).to_be_hidden()
    assert page.evaluate(
        "() => getComputedStyle(document.querySelector('.js-admin-link')).display"
    ) == "none"


def test_admin_link_visible_for_admin(page: Page, base_url):
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")  # seeded admin (CRICNETRA_SEED_ADMIN)
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)
    # the desktop sidebar (>=900px; Playwright's default viewport is 1280 wide)
    # shows the Admin link once an admin is signed in
    expect(page.locator(".js-admin-link").first).to_be_visible(timeout=10000)
