"""Broadcast analytics: powerplay + innings summaries on the overlay payload, and the
analysis OBS scene (/overlay/{id}/analysis) with worm + projected + per-innings stats."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# 2-over innings, powerplay = over 1, 4-a-side so the innings doesn't end on wickets
RULES = {"name": "T20", "format_id": "t20", "players_per_side": 4, "overs_per_innings": 2,
         "balls_per_over": 6, "powerplays": [{"start_over": 1, "end_over": 1, "max_fielders_outside": 2}]}


def _match_after_powerplay() -> str:
    mid = client.post("/api/v1/matches", json={
        "team_a": "CSK", "team_b": "MI", "bat_first": "a", "rules": RULES,
        "squad_a": ["A1", "A2", "A3", "A4"], "squad_b": ["B1", "B2", "B3", "B4"]},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B1"})
    for v in (4, 6, 1, 0, 4, 2):   # over 1 = 17 runs, two 4s + one 6
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": v})
    return mid


def test_overlay_pp_summary_after_powerplay():
    mid = _match_after_powerplay()
    d = client.get(f"/api/v1/matches/{mid}/overlay").json()
    pp = d["pp_summary"]
    assert pp is not None and pp["complete"] is True
    assert pp["runs"] == 17 and pp["overs"] == 1
    assert pp["fours"] == 2 and pp["sixes"] == 1 and pp["boundaries"] == 3
    assert pp["run_rate"] == 17.0
    isum = d["innings_summary"]
    assert isum["boundaries"] == 3 and isum["sixes"] == 1
    assert isum["top_bat"] is not None
    client.delete(f"/api/v1/matches/{mid}")


def test_pp_summary_absent_before_powerplay_completes():
    mid = client.post("/api/v1/matches", json={
        "team_a": "CSK", "team_b": "MI", "bat_first": "a", "rules": RULES,
        "squad_a": ["A1", "A2", "A3", "A4"], "squad_b": ["B1", "B2", "B3", "B4"]},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B1"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})  # PP not done
    assert client.get(f"/api/v1/matches/{mid}/overlay").json()["pp_summary"] is None
    client.delete(f"/api/v1/matches/{mid}")


def test_analysis_endpoint_has_worm_projected_and_powerplay():
    mid = _match_after_powerplay()
    a = client.get(f"/api/v1/matches/{mid}/analysis").json()
    assert a["crr"] == 17.0
    assert a["projected"] == 34            # crr 17 * 2 overs
    assert a["innings"] and a["innings"][0]["worm"] == [17]     # cumulative per over
    assert a["innings"][0]["powerplay"]["runs"] == 17
    assert a["innings"][0]["boundaries"] == 3
    client.delete(f"/api/v1/matches/{mid}")


def test_analysis_page_renders_self_contained():
    mid = _match_after_powerplay()
    r = client.get(f"/overlay/{mid}/analysis")
    assert r.status_code == 200
    html = r.text
    assert 'data-mid="' + mid + '"' in html
    assert "background:transparent" in html
    assert 'id="wormSvg"' in html                 # the worm graph
    assert f"/api/v1/matches/" in html and "/analysis" in html   # drives itself from the endpoint
    client.delete(f"/api/v1/matches/{mid}")


def test_analysis_includes_wagon_and_pitch():
    mid = client.post("/api/v1/matches", json={
        "team_a": "CSK", "team_b": "MI", "bat_first": "a", "rules": RULES,
        "squad_a": ["A1", "A2", "A3", "A4"], "squad_b": ["B1", "B2", "B3", "B4"]},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B1"})
    client.post(f"/api/v1/matches/{mid}/balls", json={
        "action": "runs", "value": 4, "wagon_x": 0.5, "wagon_y": 0.4, "pitch_x": 0.3, "pitch_y": 0.4})
    a = client.get(f"/api/v1/matches/{mid}/analysis").json()
    assert len(a["wagon"]) == 1 and a["wagon"][0]["zone"]
    assert len(a["pitch"]) == 1 and a["pitch"][0]["length"] == "Good Length"
    assert a["pp_overs"] == 1                       # first powerplay end-over from RULES
    client.delete(f"/api/v1/matches/{mid}")


def test_analysis_404_for_missing_match():
    assert client.get("/api/v1/matches/99999999/analysis").status_code == 404
    assert client.get("/overlay/99999999/analysis").status_code == 404
