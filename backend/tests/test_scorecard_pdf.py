"""The premium printable scorecard report (/scorecard/{id}) renders real data."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

RULES = {"name": "T20", "format_id": "t20", "players_per_side": 3, "overs_per_innings": 1, "balls_per_over": 6}


def _played_match() -> str:
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "Chennai", "team_b": "Mumbai", "bat_first": "a", "rules": RULES,
              "squad_a": ["Gaikwad", "Jadeja", "Dhoni"], "squad_b": ["Rohit", "Surya", "Bumrah"]},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Bumrah"})
    for ball in ({"action": "runs", "value": 6}, {"action": "runs", "value": 4},
                 {"action": "wicket", "dismissal": "bowled"}, {"action": "runs", "value": 2},
                 {"action": "runs", "value": 1}, {"action": "runs", "value": 0}):
        client.post(f"/api/v1/matches/{mid}/balls", json=ball)
    return mid


def test_scorecard_report_renders_all_sections():
    mid = _played_match()
    r = client.get(f"/scorecard/{mid}")
    assert r.status_code == 200
    html = r.text
    assert "Match Scorecard Report" in html
    assert "Chennai" in html and "Mumbai" in html
    assert "Match Statistics" in html          # stats dashboard
    assert "Total Runs" in html and "Dot Balls" in html
    assert "Partnerships" in html
    assert "Fall of Wickets" in html
    assert "Key Moments" in html               # ball-by-ball highlights
    assert "<svg" in html and "segno" in html  # the QR code
    assert f"/m/{mid}" in html                 # QR/link points at the live scorecard
    client.delete(f"/api/v1/matches/{mid}")


def test_scorecard_report_shows_awards_when_decided():
    mid = _played_match()
    client.post(f"/api/v1/matches/{mid}/second-innings")
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Jadeja"})
    for ball in ({"action": "runs", "value": 4}, {"action": "wicket", "dismissal": "bowled"},
                 {"action": "runs", "value": 1}, {"action": "runs", "value": 0},
                 {"action": "runs", "value": 0}, {"action": "runs", "value": 0}):
        client.post(f"/api/v1/matches/{mid}/balls", json=ball)
    final = client.get(f"/api/v1/matches/{mid}").json()
    assert final["result"]                     # match decided
    r = client.get(f"/scorecard/{mid}")
    assert "Match Awards" in r.text
    assert "Man of the Match" in r.text
    client.delete(f"/api/v1/matches/{mid}")


def test_scorecard_report_404_for_missing_match():
    assert client.get("/scorecard/99999999").status_code == 404
