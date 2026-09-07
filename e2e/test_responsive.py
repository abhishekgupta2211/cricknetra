"""Deep responsive audit — every public page must fit its viewport with no
horizontal overflow / off-screen content, from desktop down to a 320px phone.

Seeds long team/tournament names on purpose to stress text wrapping/truncation.
On failure the assertion lists the exact page, width and offending elements."""

from __future__ import annotations

import re

from playwright.sync_api import Page

WIDTHS = [
    (1440, "desktop"), (1280, "laptop"), (1024, "tablet-landscape"),
    (768, "tablet"), (414, "phone-lg"), (390, "phone"), (360, "phone-sm"), (320, "phone-xs"),
]

# Finds elements whose right/left edge pokes outside the viewport, ignoring
# intentional horizontal scrollers (overflow-x auto/scroll on the element or an
# ancestor). Returns the document overflow + the worst offenders.
AUDIT_JS = r"""() => {
  const vw = window.innerWidth;
  const docOverflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
  const inScroller = (el) => {
    let p = el;
    while (p && p !== document.body) {
      const o = getComputedStyle(p).overflowX;
      if (o === 'auto' || o === 'scroll') return true;
      p = p.parentElement;
    }
    return false;
  };
  const culprits = [];
  for (const el of document.body.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (getComputedStyle(el).visibility === 'hidden') continue;  // e.g. the closed nav drawer
    if (Math.ceil(r.right) > vw + 1 || Math.floor(r.left) < -1) {
      if (inScroller(el)) continue;
      culprits.push({
        sel: el.tagName.toLowerCase() + (el.className && el.className.toString ? '.' + el.className.toString().trim().split(/\s+/).slice(0,2).join('.') : ''),
        right: Math.round(r.right), left: Math.round(r.left), width: Math.round(r.width),
        text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 34),
      });
    }
  }
  culprits.sort((a, b) => (b.right - b.left) - (a.right - a.left));
  return { docOverflow, vw, culprits: culprits.slice(0, 5) };
}"""


def test_public_pages_fit_all_dimensions(page: Page, base_url, js_errors):
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    ids = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const post = (u, b) => fetch(u, {method: 'POST', headers: H, body: JSON.stringify(b)}).then(r => r.json());
      const ta = await post('/api/v1/teams', {name: 'Chennai Super Kings'});
      const tb = await post('/api/v1/teams', {name: 'Royal Challengers Bengaluru'});
      const m = await post('/api/v1/matches', {team_a: 'Chennai Super Kings', team_b: 'Royal Challengers Bengaluru', bat_first: 'a'});
      await post('/api/v1/matches/' + m.id + '/bowler', {bowler: 'Ravindra Jadeja'});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 4});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 6});
      const tn = await post('/api/v1/tournaments', {name: 'Indian Premier League 2026 Season', format: 'round_robin', format_id: 't20', team_ids: [ta.id, tb.id]});
      return {mid: String(m.id), tid: String(tn.id)};
    }""")

    pages = [
        "/", "/live-matches", "/tournaments", "/highlights", "/tools", "/tips",
        "/contact", "/login", "/register", f"/m/{ids['mid']}", f"/t/{ids['tid']}",
    ]
    failures = []
    for path in pages:
        for w, label in WIDTHS:
            page.set_viewport_size({"width": w, "height": 900})
            page.goto(base_url + path)
            res = page.evaluate(AUDIT_JS)
            if res["docOverflow"] > 1:
                failures.append(f"{path} @ {w}px ({label}): +{res['docOverflow']}px overflow -> {res['culprits']}")
    assert not failures, "Responsive overflow found:\n" + "\n".join(failures)


APP_WIDTHS = [(1280, "desktop"), (768, "tablet"), (414, "phone-lg"), (375, "phone"), (320, "phone-xs")]


def test_app_spa_pages_fit_all_dimensions(page: Page, base_url, js_errors):
    """The in-app SPA (behind login) must also fit every viewport — the scoring
    screen (tables + charts + pad), leaderboards, admin panel, settings, etc."""
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)

    mid = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const post = (u, b) => fetch(u, {method: 'POST', headers: H, body: JSON.stringify(b)}).then(r => r.json());
      await post('/api/v1/players', {name: 'Mahendra Singh Dhoni'});
      await post('/api/v1/teams', {name: 'Royal Challengers Bengaluru'});
      const m = await post('/api/v1/matches', {team_a: 'Chennai Super Kings', team_b: 'Royal Challengers Bengaluru', bat_first: 'a'});
      await post('/api/v1/matches/' + m.id + '/bowler', {bowler: 'Ravindra Jadeja'});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 4});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'wicket', dismissal: 'bowled'});
      return String(m.id);
    }""")

    routes = ["", "new", "teams", "players", "leaderboards", "network", "venues",
              "settings", "highlights", "admin", "tournaments", f"match/{mid}"]
    failures = []
    for route in routes:
        for w, label in APP_WIDTHS:
            page.set_viewport_size({"width": w, "height": 900})
            page.goto(base_url + f"/app?rw={w}#/{route}")
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            page.wait_for_timeout(450)
            res = page.evaluate(AUDIT_JS)
            if res["docOverflow"] > 1:
                failures.append(f"#/{route} @ {w}px ({label}): +{res['docOverflow']}px overflow -> {res['culprits']}")
    assert not failures, "App (SPA) responsive overflow found:\n" + "\n".join(failures)
