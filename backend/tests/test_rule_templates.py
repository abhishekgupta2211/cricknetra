"""Rule-template API + rule-out scoring through the API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _ruleout_rules(players: int = 8, name: str = "My Society Box"):
    rules = client.get("/api/v1/presets/ruleout").json()
    rules["name"] = name
    rules["players_per_side"] = players
    return rules


def test_template_crud():
    rules = _ruleout_rules(players=8, name="My Society Box (8-a-side)")
    r = client.post("/api/v1/rule-templates", json=rules)
    assert r.status_code == 201
    dto = r.json()
    tid = dto["id"]
    assert dto["name"] == "My Society Box (8-a-side)"
    assert dto["rules"]["over_boundary_out"] is True
    assert dto["rules"]["players_per_side"] == 8

    assert any(t["id"] == tid for t in client.get("/api/v1/rule-templates").json())
    assert client.get(f"/api/v1/rule-templates/{tid}").json()["rules"]["players_per_side"] == 8

    assert client.delete(f"/api/v1/rule-templates/{tid}").status_code == 204
    assert client.get(f"/api/v1/rule-templates/{tid}").status_code == 404


def test_match_with_ruleout_rules_counts_boundary_as_out():
    rules = _ruleout_rules(players=8)
    r = client.post("/api/v1/matches", json={"team_a": "X", "team_b": "Y", "rules": rules})
    assert r.status_code == 201
    state = r.json()
    mid = state["id"]
    assert state["innings"][0]["max_wickets"] == 8  # 8-a-side, last-man-stands

    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Y 1"})
    r = client.post(
        f"/api/v1/matches/{mid}/balls", json={"action": "wicket", "dismissal": "boundary_out"}
    )
    assert r.status_code == 200
    inn = r.json()["innings"][0]
    assert inn["wickets"] == 1
    assert inn["runs"] == 0  # hitting it out scores nothing


def test_boundary_out_rejected_for_normal_format():
    # A standard T20 match: a boundary_out event is not a dismissal.
    r = client.post("/api/v1/matches", json={"team_a": "X", "team_b": "Y", "format_id": "t20"})
    mid = r.json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Y 1"})
    r = client.post(
        f"/api/v1/matches/{mid}/balls", json={"action": "wicket", "dismissal": "boundary_out"}
    )
    assert r.json()["innings"][0]["wickets"] == 0
