"""Public pages must reflect a score change WITHOUT the visitor reloading.

/m/{id} has a real SSE stream (live.js). The directory (/live-matches) and the
tournament page (/t/{id}) would need one connection per match, so they poll one
cheap HTML fetch and swap their [data-live-region] (live-list.js). The landing
re-polls the match list so its "N live now" pill can't go stale."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

SEED = """async () => {
  const t = localStorage.getItem('cn_token');
  const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
  const post = (u, b) => fetch(u, {method: 'POST', headers: H, body: JSON.stringify(b)}).then(r => r.json());
  // a team + its player ids (add_member returns the whole TeamDTO back)
  const mkTeam = async (name, n) => {
    const t0 = await post('/api/v1/teams', {name});
    let team = t0;
    for (let i = 1; i <= n; i++) team = await post('/api/v1/teams/' + t0.id + '/members', {name: name + ' P' + i});
    return {id: t0.id, ids: team.members.map(m => String(m.player_id))};
  };
  const a = await mkTeam('Live Alpha', 3);
  const b = await mkTeam('Live Bravo', 3);
  const tn = await post('/api/v1/tournaments',
    {name: 'Live Cup', format: 'round_robin', format_id: 't20', team_ids: [a.id, b.id]});
  const d = await (await fetch('/api/v1/tournaments/' + tn.id)).json();
  const started = await post('/api/v1/tournaments/fixtures/' + d.fixtures[0].id + '/start',
    {squad_a_ids: a.ids, squad_b_ids: b.ids, bat_first: 'a'});
  const mid = String(started.match_id);
  await post('/api/v1/matches/' + mid + '/bowler', {bowler: 'Opening Bowler'});
  await post('/api/v1/matches/' + mid + '/balls', {action: 'runs', value: 1});
  return {mid: mid, tid: String(tn.id)};
}"""


def _score(page: Page, mid: str, runs: int):
    st = page.evaluate(
        """async ([mid, runs]) => {
          const t = localStorage.getItem('cn_token');
          const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
          const r = await fetch('/api/v1/matches/' + mid + '/balls',
            {method: 'POST', headers: H, body: JSON.stringify({action: 'runs', value: runs})});
          return r.status;
        }""",
        [mid, runs],
    )
    assert st == 200, f"scoring failed: {st}"


def _login(page: Page, base_url):
    page.goto(base_url + "/login")
    page.fill("#identifier", "e2eadmin")
    page.fill("#password", "secret123")
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/app"), timeout=15000)


def test_app_home_live_cards_update_without_reload(page: Page, base_url, js_errors):
    """The in-app Home dashboard's "LIVE NOW" card must follow the score. It polls
    (home shows up to 8 live matches; 8 EventSources would blow the browser's ~6
    connections-per-origin cap — only the match view gets a real SSE)."""
    _login(page, base_url)
    mid = page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      const post = (u, b) => fetch(u, {method: 'POST', headers: H, body: JSON.stringify(b)}).then(r => r.json());
      const m = await post('/api/v1/matches', {team_a: 'Home Live A', team_b: 'Home Live B', bat_first: 'a'});
      await post('/api/v1/matches/' + m.id + '/bowler', {bowler: 'Opening Bowler'});
      await post('/api/v1/matches/' + m.id + '/balls', {action: 'runs', value: 1});
      return String(m.id);
    }""")

    # browser 1: sit on the home dashboard
    page.goto(base_url + "/app?home=1#/")
    hero = f'.live-hero[data-mid="{mid}"]'
    page.wait_for_selector(hero, timeout=15000)
    before = page.evaluate(f"() => document.querySelector('{hero}').dataset.sig")

    # browser 2: score a six elsewhere
    _score(page, mid, 6)

    # home must catch up on its own (10s poll) — no reload
    page.wait_for_function(
        f"sig => {{ const el = document.querySelector('{hero}'); return el && el.dataset.sig !== sig; }}",
        arg=before, timeout=25000,
    )
    after = page.evaluate(f"() => document.querySelector('{hero}').querySelector('.score__runs').textContent")
    assert "/" in after and after.split("/")[0].isdigit(), after
    assert int(after.split("/")[0]) >= 7, f"home score did not follow the six: {after}"
    assert page.evaluate("performance.getEntriesByType('navigation').length") == 1


def test_public_pages_update_live_without_reload(page: Page, base_url, js_errors):
    _login(page, base_url)
    ids = page.evaluate(SEED)
    mid, tid = ids["mid"], ids["tid"]

    # region text is re-read each poll (live-list swaps the node, so never hold a ref)
    grid_text = "() => (document.querySelector('[data-live-region]') || {}).textContent || ''"

    for path, label in ((f"/t/{tid}", "tournament"), ("/live-matches", "directory")):
        page.goto(base_url + path)
        page.wait_for_timeout(700)
        before = page.evaluate(grid_text)
        _score(page, mid, 6)
        # live-list polls every 12s while live; allow a margin
        page.wait_for_function(
            f"before => (document.querySelector('[data-live-region]').textContent || '') !== before",
            arg=before, timeout=25000,
        )
        after = page.evaluate(grid_text)
        assert after != before, f"{label} did not refresh itself"
        assert page.evaluate("performance.getEntriesByType('navigation').length") == 1, label

    # landing: the "N live now" pill must reflect reality (other tests share this
    # in-memory server, so compare against the API rather than a fixed number)
    page.goto(base_url + "/")
    page.wait_for_function("() => !document.getElementById('heroLive').hidden", timeout=15000)
    expected = page.evaluate("""async () => {
      const ms = await (await fetch('/api/v1/matches')).json();
      return String(ms.filter(m => !m.result && m.status !== 'complete').length);
    }""")
    assert page.locator("#liveCount").inner_text().strip() == expected

    # ...and it RE-POLLS: a match starting after page load raises the count.
    # (The old code fetched the list exactly once, so this never happened.)
    before_n = int(page.locator("#liveCount").inner_text().strip())
    page.evaluate("""async () => {
      const t = localStorage.getItem('cn_token');
      const H = {'Content-Type': 'application/json', Authorization: 'Bearer ' + t};
      await fetch('/api/v1/matches', {method: 'POST', headers: H,
        body: JSON.stringify({team_a: 'Late Start A', team_b: 'Late Start B', bat_first: 'a'})});
    }""")
    page.wait_for_function(
        "n => Number(document.getElementById('liveCount').textContent) > n",
        arg=before_n, timeout=45000,   # landing re-polls every 30s
    )
    assert page.evaluate("performance.getEntriesByType('navigation').length") == 1
