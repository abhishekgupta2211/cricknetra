"""Offline-first scoring core — optimistic projection (the tally) + the queue
persisting in IndexedDB across reloads. Exercised in a real browser via the
window.__cnOffline hook, so it needs no server-side match (which would require an
admin/scorer). The online send path is unchanged and covered by the smoke tests."""

from __future__ import annotations

from playwright.sync_api import Page

SNAP = {
    "id": "offline-test-1",
    "team_a": "A", "team_b": "B", "current_innings": 1,
    "rules": {"balls_per_over": 6, "wide": {"run_penalty": 1}, "no_ball": {"run_penalty": 1}},
    "innings": [{
        "batting_team": "A", "bowling_team": "B", "runs": 10, "wickets": 1, "legal_balls": 6,
        "overs_str": "1.0", "this_over": [], "striker": "x", "non_striker": "y", "run_rate": 10.0,
    }],
}


def test_offline_projection_tally(page: Page, base_url):
    page.goto(base_url + "/app")
    page.wait_for_function("() => window.__cnOffline")
    res = page.evaluate(
        """(snap) => {
            const q = [
              {kind:'ball', payload:{action:'runs', value:4}},
              {kind:'ball', payload:{action:'wide', value:0}},
              {kind:'ball', payload:{action:'runs', value:1}},
              {kind:'ball', payload:{action:'wicket'}},
            ];
            const inn = window.__cnOffline.project(snap, q).innings[0];
            return {runs: inn.runs, wickets: inn.wickets, legal: inn.legal_balls,
                    pending: window.__cnOffline.project(snap, q)._pending};
        }""", SNAP)
    # 10 +4 +1(wide penalty) +1 +0(wicket) = 16; wkts 1->2; legal 6 + 3 legal balls = 9
    assert res == {"runs": 16, "wickets": 2, "legal": 9, "pending": 4}


def test_offline_queue_persists_across_reload(page: Page, base_url):
    page.goto(base_url + "/app")
    page.wait_for_function("() => window.__cnOffline")
    page.evaluate(
        """async (snap) => {
            await window.__cnOffline.db.put({id: snap.id, snapshot: snap, queue: [], canScore: true});
            await window.__cnOffline.score(snap.id, {kind:'ball', payload:{action:'runs', value:4}});
            await window.__cnOffline.score(snap.id, {kind:'ball', payload:{action:'runs', value:6}});
        }""", SNAP)
    assert page.evaluate("(id) => window.__cnOffline.pending(id)", SNAP["id"]) == 2

    page.reload()  # IndexedDB must survive a reload (this is the whole point)
    page.wait_for_function("() => window.__cnOffline")
    assert page.evaluate("(id) => window.__cnOffline.pending(id)", SNAP["id"]) == 2


def test_offline_undo_pops_last_queued(page: Page, base_url):
    page.goto(base_url + "/app")
    page.wait_for_function("() => window.__cnOffline")
    final = page.evaluate(
        """async (snap) => {
            const id = 'offline-undo-1';
            await window.__cnOffline.db.put({id, snapshot: snap, queue: [], canScore: true});
            await window.__cnOffline.score(id, {kind:'ball', payload:{action:'runs', value:4}});
            await window.__cnOffline.score(id, {kind:'ball', payload:{action:'runs', value:2}});
            await window.__cnOffline.score(id, {kind:'undo'});
            return window.__cnOffline.pending(id);
        }""", SNAP)
    assert final == 1
