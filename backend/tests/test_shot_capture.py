"""Shot capture: optional wagon (batting) + pitch (bowling) coordinates ride any
delivery, persist through the event log, and surface on the innings DTO with derived
zone / length / line / outcome."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

RULES = {"name": "T20", "format_id": "t20", "players_per_side": 3, "overs_per_innings": 2, "balls_per_over": 6}


def _new_match() -> str:
    mid = client.post("/api/v1/matches", json={
        "team_a": "CSK", "team_b": "MI", "bat_first": "a", "rules": RULES,
        "squad_a": ["Gaikwad", "Jadeja", "Dhoni"], "squad_b": ["Rohit", "Surya", "Bumrah"]},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Bumrah"})
    return mid


def _innings0(mid: str) -> dict:
    return client.get(f"/api/v1/matches/{mid}").json()["innings"][0]


def test_wagon_and_pitch_captured_on_a_run():
    mid = _new_match()
    client.post(f"/api/v1/matches/{mid}/balls", json={
        "action": "runs", "value": 4, "wagon_x": 0.6, "wagon_y": 0.5,
        "pitch_x": 0.3, "pitch_y": 0.4, "speed": 140.0})
    inn = _innings0(mid)

    assert len(inn["wagon"]) == 1
    w = inn["wagon"][0]
    assert w["runs"] == 4 and w["bowler"] == "Bumrah" and w["wicket"] is False
    assert w["ball"] == "0.1" and w["zone"]        # zone derived, non-empty

    assert len(inn["pitch"]) == 1
    p = inn["pitch"][0]
    assert p["runs"] == 4 and p["outcome"] == "four"
    assert p["length"] == "Good Length" and p["line"] == "Off Stump"
    assert p["speed"] == 140.0 and p["bowler"] == "Bumrah"
    client.delete(f"/api/v1/matches/{mid}")


def test_wagon_and_pitch_captured_on_a_caught_wicket():
    mid = _new_match()
    client.post(f"/api/v1/matches/{mid}/balls", json={
        "action": "wicket", "dismissal": "caught", "fielder": "Kohli", "value": 0,
        "wagon_x": 0.4, "wagon_y": -0.3, "pitch_x": 0.5, "pitch_y": 0.7})
    inn = _innings0(mid)

    assert len(inn["wagon"]) == 1 and inn["wagon"][0]["wicket"] is True   # captured on the dismissal ball
    assert len(inn["pitch"]) == 1 and inn["pitch"][0]["outcome"] == "wicket"
    client.delete(f"/api/v1/matches/{mid}")


def test_pitch_captured_on_a_wide_but_no_wagon():
    mid = _new_match()
    client.post(f"/api/v1/matches/{mid}/balls", json={
        "action": "wide", "value": 0, "pitch_x": -0.7, "pitch_y": 0.3})
    inn = _innings0(mid)
    assert len(inn["wagon"]) == 0                       # wagon is an off-bat-only projection
    assert len(inn["pitch"]) == 1 and inn["pitch"][0]["line"] == "Down Leg"
    client.delete(f"/api/v1/matches/{mid}")


def test_coords_survive_an_edit_replay():
    """Editing an earlier ball rewrites its event payload — the coordinates must
    persist through the replay, not get dropped."""
    mid = _new_match()
    client.post(f"/api/v1/matches/{mid}/balls", json={
        "action": "runs", "value": 2, "wagon_x": -0.2, "wagon_y": 0.6, "pitch_x": -0.1, "pitch_y": 0.45})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})
    # edit ball 0 to a four, keeping fresh coordinates
    client.put(f"/api/v1/matches/{mid}/balls/0", json={
        "action": "runs", "value": 4, "wagon_x": 0.7, "wagon_y": 0.2, "pitch_x": 0.6, "pitch_y": 0.15})
    inn = _innings0(mid)
    w0 = inn["wagon"][0]
    assert w0["runs"] == 4 and abs(w0["x"] - 0.7) < 1e-6
    assert inn["pitch"][0]["length"] == "Full" and inn["pitch"][0]["line"] == "Outside Off"
    client.delete(f"/api/v1/matches/{mid}")


def test_public_match_and_pdf_embed_shots():
    mid = _new_match()
    client.post(f"/api/v1/matches/{mid}/balls", json={
        "action": "runs", "value": 4, "wagon_x": 0.5, "wagon_y": 0.4, "pitch_x": 0.2, "pitch_y": 0.4})

    page = client.get(f"/m/{mid}")                     # public match page
    assert page.status_code == 200
    assert "/js/analytics.js" in page.text and "sc-shots" in page.text
    assert '"wagon"' in page.text and '"pitch"' in page.text   # serialized shot data embedded

    pdf = client.get(f"/scorecard/{mid}")              # print scorecard
    assert pdf.status_code == 200
    assert "/js/analytics.js" in pdf.text and "sc-shots-pdf" in pdf.text
    client.delete(f"/api/v1/matches/{mid}")


def test_no_coords_leaves_lists_empty():
    mid = _new_match()
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})
    inn = _innings0(mid)
    assert inn["wagon"] == [] and inn["pitch"] == []    # optional — nothing forced
    client.delete(f"/api/v1/matches/{mid}")
