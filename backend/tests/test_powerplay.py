"""Powerplay overs (fielding-restriction ranges): model, validation, and the
live `in_powerplay` flag the scoring UI badges off."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.domain.presets import t20
from app.domain.rules import MatchRules, PowerplayRange
from app.main import app

client = TestClient(app)


# ----- domain --------------------------------------------------------------
def test_active_powerplay_helper():
    r = t20()
    assert r.is_powerplay(1) and r.is_powerplay(6)
    assert not r.is_powerplay(7)
    pp = r.active_powerplay(3)
    assert pp is not None and pp.label == "Powerplay"
    assert r.active_powerplay(7) is None


def test_powerplay_range_rejects_reversed():
    with pytest.raises(ValidationError):
        PowerplayRange(start_over=6, end_over=2)


def test_rules_reject_powerplay_beyond_innings():
    with pytest.raises(ValidationError):
        MatchRules(overs_per_innings=4, powerplays=[PowerplayRange(start_over=1, end_over=6)])


# ----- live flag through the API -------------------------------------------
def _rules_with_pp():
    return {
        "name": "PP Mini", "format_id": "ppmini",
        "overs_per_innings": 4, "balls_per_over": 6,
        "powerplays": [{"start_over": 1, "end_over": 2, "label": "Powerplay"}],
    }


def test_preset_match_lights_up_powerplay():
    mid = client.post(
        "/api/v1/matches", json={"team_a": "A", "team_b": "B", "format_id": "t20"}
    ).json()["id"]
    inn = client.get(f"/api/v1/matches/{mid}").json()["innings"][0]
    assert inn["current_over"] == 1
    assert inn["in_powerplay"] is True
    assert inn["powerplay_label"] == "Powerplay"
    client.delete(f"/api/v1/matches/{mid}")


def test_in_powerplay_turns_off_after_the_range():
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": _rules_with_pp()},
    ).json()["id"]

    # Over 1, ball 0 — inside the powerplay.
    assert client.get(f"/api/v1/matches/{mid}").json()["innings"][0]["in_powerplay"] is True

    def over(bowler):
        client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler})
        for _ in range(6):
            client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})

    over("B1")  # finish over 1 -> over 2 in progress, still powerplay (1–2)
    mid_inn = client.get(f"/api/v1/matches/{mid}").json()["innings"][0]
    assert mid_inn["current_over"] == 2 and mid_inn["in_powerplay"] is True

    over("B2")  # finish over 2 -> over 3, powerplay over
    end_inn = client.get(f"/api/v1/matches/{mid}").json()["innings"][0]
    assert end_inn["current_over"] == 3
    assert end_inn["in_powerplay"] is False
    assert end_inn["powerplay_label"] is None
    client.delete(f"/api/v1/matches/{mid}")


def test_api_rejects_powerplay_beyond_innings():
    bad = _rules_with_pp()
    bad["powerplays"][0]["end_over"] = 9  # > 4 overs
    r = client.post("/api/v1/matches", json={"team_a": "A", "team_b": "B", "rules": bad})
    assert r.status_code == 422


def test_powerplays_roundtrip_through_rule_template():
    rules = _rules_with_pp()
    rules["name"] = "Box w/ powerplay"
    tid = client.post("/api/v1/rule-templates", json=rules).json()["id"]
    got = client.get(f"/api/v1/rule-templates/{tid}").json()
    assert got["rules"]["powerplays"][0]["start_over"] == 1
    assert got["rules"]["powerplays"][0]["end_over"] == 2
    client.delete(f"/api/v1/rule-templates/{tid}")


# ----- fielding limits (per-over) ------------------------------------------
def _rules_fielding():
    return {
        "name": "Fielding", "format_id": "fld",
        "overs_per_innings": 4, "balls_per_over": 6,
        "default_fielders_outside": 4,
        "powerplays": [{"start_over": 1, "end_over": 2, "label": "Powerplay", "max_fielders_outside": 2}],
    }


def test_fielders_outside_limit_helper():
    r = t20()
    # T20 powerplay (overs 1–6) restricts the field; normal overs use the default.
    assert r.fielders_outside_limit(1) == 2
    assert r.fielders_outside_limit(6) == 2
    assert r.fielders_outside_limit(7) == r.default_fielders_outside


def test_fielders_outside_limit_surfaced_through_api():
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": _rules_fielding()},
    ).json()["id"]
    inn = client.get(f"/api/v1/matches/{mid}").json()["innings"][0]
    assert inn["in_powerplay"] is True
    assert inn["fielders_outside_limit"] == 2  # powerplay restriction

    def over(bowler):
        client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler})
        for _ in range(6):
            client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})

    over("B1")
    over("B2")  # overs 1–2 are the powerplay; now over 3 is in progress
    inn3 = client.get(f"/api/v1/matches/{mid}").json()["innings"][0]
    assert inn3["current_over"] == 3 and inn3["in_powerplay"] is False
    assert inn3["fielders_outside_limit"] == 4  # back to the normal-over default
    client.delete(f"/api/v1/matches/{mid}")


def test_advanced_rule_fields_roundtrip_through_template():
    rules = _rules_fielding()
    rules["name"] = "Advanced"
    rules["super_over_on_tie"] = True
    rules["dls_enabled"] = True
    tid = client.post("/api/v1/rule-templates", json=rules).json()["id"]
    got = client.get(f"/api/v1/rule-templates/{tid}").json()["rules"]
    assert got["super_over_on_tie"] is True
    assert got["dls_enabled"] is True
    assert got["default_fielders_outside"] == 4
    assert got["powerplays"][0]["max_fielders_outside"] == 2
    client.delete(f"/api/v1/rule-templates/{tid}")
