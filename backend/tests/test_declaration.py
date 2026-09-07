"""Declaration — close an innings early (#144)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_RULES = {
    "name": "Timed", "format_id": "timed", "overs_per_innings": 20,
    "players_per_side": 4, "balls_per_over": 6, "allow_declaration": True,
}
_NO_DECL = {**_RULES, "allow_declaration": False}


def _match(rules):
    return client.post("/api/v1/matches", json={
        "team_a": "A", "team_b": "B", "bat_first": "a", "rules": rules,
        "squad_a": ["A1", "A2", "A3", "A4"], "squad_b": ["B1", "B2", "B3", "B4"],
    }).json()["id"]


def _bowl(mid, name):
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": name})


def _ball(mid, v):
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": v})


def test_declare_closes_innings_persists_and_allows_chase():
    mid = _match(_RULES)
    _bowl(mid, "B1")
    for v in (4, 4, 1):  # A 9/0, well short of 20 overs
        _ball(mid, v)

    st = client.post(f"/api/v1/matches/{mid}/declare").json()
    assert st["innings"][0]["is_complete"] is True
    assert st["result"] is None
    assert st["can_start_second_innings"] is True

    # persists on re-read (rulebook carries declared_innings)
    st2 = client.get(f"/api/v1/matches/{mid}").json()
    assert st2["innings"][0]["is_complete"] is True
    assert st2["rules"]["declared_innings"] == 1

    # the declared innings can't be scored any more
    assert client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1}).status_code == 409

    # chase the target (10) → match completes
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _bowl(mid, "A1")
    _ball(mid, 6)
    _ball(mid, 4)
    st3 = client.get(f"/api/v1/matches/{mid}").json()
    assert st3["result"] is not None


def test_declare_requires_rule_enabled():
    mid = _match(_NO_DECL)
    _bowl(mid, "B1")
    _ball(mid, 4)
    assert client.post(f"/api/v1/matches/{mid}/declare").status_code == 409


def test_declare_already_complete_innings_conflicts():
    mid = _match(_RULES)
    _bowl(mid, "B1")
    _ball(mid, 4)
    client.post(f"/api/v1/matches/{mid}/declare")  # close it
    # declaring again (already complete) → 409
    assert client.post(f"/api/v1/matches/{mid}/declare").status_code == 409


def test_declare_unknown_match_404():
    assert client.post("/api/v1/matches/999999/declare").status_code == 404
