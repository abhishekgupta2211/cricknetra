"""Modals must never push their action buttons off-screen.

The start-fixture modal lists two full XIs (22 chips) plus a bats-first toggle, so
its sheet easily grows taller than the viewport. The sheet is inside a fixed
overlay, so anything past the viewport edge is clipped and unreachable — the
Cancel / "Start & score" buttons must stay on screen."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

SEED = """async () => {
  const t = localStorage.getItem('cn_token');
  const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
  const post = (u, b) => fetch(u, {method: 'POST', headers: H, body: JSON.stringify(b)}).then(r => r.json());
  const mkTeam = async (name, names) => {
    const team = await post('/api/v1/teams', {name});
    for (const n of names) await post('/api/v1/teams/' + team.id + '/members', {name: n});
    return team.id;
  };
  const dc = ['Faf du Plessis', 'Jake Fraser-McGurk', 'KL Rahul', 'Abishek Porel', 'Tristan Stubbs',
              'Axar Patel', 'Ashutosh Sharma', 'Mitchell Starc', 'Kuldeep Yadav', 'Mohit Sharma', 'Mukesh Kumar'];
  const rcb = ['Virat Kohli', 'Phil Salt', 'Rajat Patidar', 'Liam Livingstone', 'Jitesh Sharma',
               'Tim David', 'Krunal Pandya', 'Bhuvneshwar Kumar', 'Josh Hazlewood', 'Yash Dayal', 'Suyash Sharma'];
  const a = await mkTeam('Delhi Capitals', dc);
  const b = await mkTeam('Royal Challengers Bengaluru', rcb);
  const tn = await post('/api/v1/tournaments',
    {name: 'IPL 2026', format: 'round_robin', format_id: 't20', team_ids: [a, b]});
  return String(tn.id);
}"""

BOX = """() => {
  const ok = document.getElementById('sf_ok');
  const sheet = document.querySelector('.modal__sheet');
  const r = ok.getBoundingClientRect();
  const s = sheet.getBoundingClientRect();
  return {
    okTop: Math.round(r.top), okBottom: Math.round(r.bottom),
    sheetTop: Math.round(s.top), sheetBottom: Math.round(s.bottom),
    vh: window.innerHeight,
  };
}"""


def _open_modal(page: Page, base_url, tid, w, h):
    page.set_viewport_size({"width": w, "height": h})
    page.goto(base_url + f"/app?w={w}#/tournament/{tid}")
    page.wait_for_timeout(900)
    page.locator("[data-start]").first.click()
    expect(page.locator("#sf_ok")).to_be_attached(timeout=10000)
    page.wait_for_timeout(250)


def test_start_fixture_modal_actions_stay_on_screen(page: Page, base_url, js_errors):
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)
    tid = page.evaluate(SEED)

    # a short laptop and a phone — both must keep the actions reachable
    for w, h in ((1280, 700), (390, 844)):
        _open_modal(page, base_url, tid, w, h)
        m = page.evaluate(BOX)
        assert m["sheetTop"] >= -1, (w, h, m)                 # sheet not clipped off the top
        assert m["sheetBottom"] <= m["vh"] + 1, (w, h, m)     # nor off the bottom
        assert m["okBottom"] <= m["vh"] + 1, (w, h, m)        # "Start & score" on screen
        assert m["okTop"] >= 0, (w, h, m)
        # and it really works: cancel closes the modal
        page.locator("#sf_cancel").click()
        expect(page.locator("#sf_ok")).to_have_count(0, timeout=5000)
