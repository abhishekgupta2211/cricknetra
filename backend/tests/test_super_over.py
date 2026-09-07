"""Super over — a one-over-per-side eliminator that breaks a tied match.

Each super-over innings is all out at 2 wickets (a 3-player, 1-over rulebook),
reuses the normal scoring endpoints, and is replayed from the event log like any
other innings. A tied super over forces another.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

TIE_RULES = {
    "name": "SO test", "format_id": "so",
    "players_per_side": 4, "overs_per_innings": 1, "balls_per_over": 6,
    "super_over_on_tie": True,
}


def _bowl(mid: str, bowler: str, values) -> None:
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler})
    for v in values:
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": v})


def _tied_match() -> str:
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": TIE_RULES},
    ).json()["id"]
    _bowl(mid, "Bx", [1, 1, 1, 1, 1, 1])  # A = 6
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _bowl(mid, "Ax", [1, 1, 1, 1, 1, 1])  # B = 6 -> scores level (tie)
    return mid


def test_a_tie_requests_a_super_over_instead_of_finishing():
    mid = _tied_match()
    st = client.get(f"/api/v1/matches/{mid}").json()
    assert st["result"] is None            # not decided yet
    assert st["needs_super_over"] is True
    client.delete(f"/api/v1/matches/{mid}")


def test_super_over_decides_the_match():
    mid = _tied_match()
    st = client.post(f"/api/v1/matches/{mid}/super-over", json={"bat_first": "a"}).json()
    assert any(i["is_super_over"] for i in st["innings"])  # a super innings appeared
    assert st["needs_super_over"] is False                # one is now in progress
    _bowl(mid, "Bz", [1, 1, 1, 1, 0, 0])                  # A super = 4
    mid_st = client.get(f"/api/v1/matches/{mid}").json()
    assert mid_st["awaiting_super_second"] is True
    client.post(f"/api/v1/matches/{mid}/super-over", json={})  # begin the reply
    _bowl(mid, "Az", [1, 1, 1, 1, 1])                     # B super = 5 -> chases it down
    final = client.get(f"/api/v1/matches/{mid}").json()
    assert final["result"] == "B won (Super Over)"
    client.delete(f"/api/v1/matches/{mid}")


def test_a_tied_super_over_forces_another():
    mid = _tied_match()
    client.post(f"/api/v1/matches/{mid}/super-over", json={"bat_first": "a"})
    _bowl(mid, "Bz", [1, 1, 0, 0, 0, 0])                  # A super = 2
    client.post(f"/api/v1/matches/{mid}/super-over", json={})
    _bowl(mid, "Az", [1, 1, 0, 0, 0, 0])                  # B super = 2 -> super over tied
    st = client.get(f"/api/v1/matches/{mid}").json()
    assert st["result"] is None and st["needs_super_over"] is True
    # second eliminator, B bats first this time
    client.post(f"/api/v1/matches/{mid}/super-over", json={"bat_first": "b"})
    _bowl(mid, "Aq", [1, 1, 1, 0, 0, 0])                  # B super2 = 3
    client.post(f"/api/v1/matches/{mid}/super-over", json={})
    _bowl(mid, "Bq", [0, 0, 0, 0, 0, 0])                  # A super2 = 0 -> B wins
    final = client.get(f"/api/v1/matches/{mid}").json()
    assert final["result"] == "B won (Super Over)"
    client.delete(f"/api/v1/matches/{mid}")


def test_super_over_rejected_when_match_is_decided():
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": TIE_RULES},
    ).json()["id"]
    _bowl(mid, "Bx", [1, 1, 1, 1, 1, 1])  # A = 6
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _bowl(mid, "Ax", [4, 4])              # B reaches 8 -> wins outright (not tied)
    r = client.post(f"/api/v1/matches/{mid}/super-over", json={"bat_first": "a"})
    assert r.status_code == 409
    client.delete(f"/api/v1/matches/{mid}")


def test_super_over_rejected_when_rule_is_off():
    rules = dict(TIE_RULES, super_over_on_tie=False)
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": rules},
    ).json()["id"]
    _bowl(mid, "Bx", [1, 1, 1, 1, 1, 1])
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _bowl(mid, "Ax", [1, 1, 1, 1, 1, 1])  # tie, but the rule is off
    st = client.get(f"/api/v1/matches/{mid}").json()
    assert st["result"] == "Match tied" and st["needs_super_over"] is False
    r = client.post(f"/api/v1/matches/{mid}/super-over", json={"bat_first": "a"})
    assert r.status_code == 409
    client.delete(f"/api/v1/matches/{mid}")
