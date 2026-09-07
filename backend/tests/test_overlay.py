"""Broadcast overlay: the /api/v1/matches/{id}/overlay payload and the transparent
/overlay/{id} page (OBS/vMix browser source) reflect real live data."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

RULES = {"name": "T20", "format_id": "t20", "players_per_side": 3, "overs_per_innings": 2, "balls_per_over": 6}


def _new_match() -> str:
    return client.post(
        "/api/v1/matches",
        json={"team_a": "Chennai", "team_b": "Mumbai", "bat_first": "a", "rules": RULES,
              "squad_a": ["Gaikwad", "Jadeja", "Dhoni"], "squad_b": ["Rohit", "Surya", "Bumrah"]},
    ).json()["id"]


def _bowl(mid: str, bowler: str, balls: list[dict]) -> None:
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler})
    for b in balls:
        client.post(f"/api/v1/matches/{mid}/balls", json=b)


def test_overlay_payload_reflects_live_state():
    mid = _new_match()
    _bowl(mid, "Bumrah", [
        {"action": "runs", "value": 6}, {"action": "runs", "value": 4},
        {"action": "runs", "value": 0}, {"action": "runs", "value": 1},
    ])
    d = client.get(f"/api/v1/matches/{mid}/overlay").json()

    assert d["batting"] == "Chennai" and d["bowling"] == "Mumbai"
    assert d["runs"] == 11 and d["wickets"] == 0
    assert d["status"] == "live" and d["complete"] is False
    # current batters + bowler cards
    assert d["striker"] is not None and d["non_striker"] is not None
    assert d["bowler"]["name"] == "Bumrah" and d["bowler"]["wickets"] == 0
    # recent-ball badges are colour-coded tokens, newest last
    tokens = [b["t"] for b in d["recent"]]
    classes = [b["cls"] for b in d["recent"]]
    assert tokens == ["6", "4", "0", "1"]
    assert "six" in classes and "four" in classes and "dot" in classes and "run" in classes
    # partnership, phase, ticker, and a monotonic ball counter
    assert d["partnership"]["runs"] == 11
    assert d["phase"]["key"] in {"pp", "middle", "death"}
    assert d["ticker"] and isinstance(d["ticker"], list)
    assert d["seq"] == 4
    client.delete(f"/api/v1/matches/{mid}")


def test_overlay_wicket_event_carries_dismissal():
    mid = _new_match()
    _bowl(mid, "Bumrah", [{"action": "runs", "value": 2}, {"action": "wicket", "dismissal": "bowled"}])
    d = client.get(f"/api/v1/matches/{mid}/overlay").json()
    assert d["wickets"] == 1
    assert d["recent"][-1] == {"t": "W", "cls": "wkt"}
    lb = d["last_ball"]
    assert lb["kind"] == "wicket" and lb["out_batter"] and "OUT" in lb["text"].upper()
    client.delete(f"/api/v1/matches/{mid}")


def test_overlay_chase_has_target_need_and_winprob():
    mid = _new_match()
    _bowl(mid, "Bumrah", [{"action": "runs", "value": 6}] * 6)   # over 1
    _bowl(mid, "Surya", [{"action": "runs", "value": 4}] * 6)    # over 2 (diff bowler) -> innings ends
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _bowl(mid, "Jadeja", [{"action": "runs", "value": 1}])
    d = client.get(f"/api/v1/matches/{mid}/overlay").json()

    assert d["innings_no"] == 2
    assert d["target"] == 61                       # 60 scored + 1
    assert d["need"] is not None and d["balls_left"] is not None
    assert d["rrr"] is not None
    assert isinstance(d["win_prob"], int) and 0 <= d["win_prob"] <= 100
    client.delete(f"/api/v1/matches/{mid}")


def test_overlay_page_renders_transparent_and_self_contained():
    mid = _new_match()
    r = client.get(f"/overlay/{mid}")
    assert r.status_code == 200
    html = r.text
    # the OBS-facing page must be self-contained + transparent
    assert 'data-mid="' + mid + '"' in html
    assert "background:transparent" in html
    assert 'id="mainBar"' in html and 'id="batCards"' in html and 'id="bowlCard"' in html
    assert 'id="ticker"' in html and 'id="fx"' in html
    # it drives itself from the live endpoints
    assert f"/api/v1/matches/" in html and "/overlay" in html
    assert "/stream" in html                       # SSE trigger
    client.delete(f"/api/v1/matches/{mid}")


def test_overlay_emits_logo_and_photo_urls_for_linked_match():
    """A match created 'from teams' (real team + player ids) exposes team-logo and
    player-photo endpoint URLs on the overlay — the page falls back to a monogram if
    a given image 404s."""
    ta = client.post("/api/v1/teams", json={"name": "CSK"}).json()
    tb = client.post("/api/v1/teams", json={"name": "MI"}).json()
    pa = [client.post("/api/v1/players", json={"name": n}).json()["id"] for n in ("Gaikwad", "Jadeja", "Dhoni")]
    pb = [client.post("/api/v1/players", json={"name": n}).json()["id"] for n in ("Rohit", "Surya", "Bumrah")]
    mid = client.post("/api/v1/matches", json={
        "team_a": "CSK", "team_b": "MI", "bat_first": "a", "rules": RULES,
        "squad_a": ["Gaikwad", "Jadeja", "Dhoni"], "squad_b": ["Rohit", "Surya", "Bumrah"],
        "squad_a_ids": pa, "squad_b_ids": pb, "team_a_id": ta["id"], "team_b_id": tb["id"],
    }).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Bumrah"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})

    ov = client.get(f"/api/v1/matches/{mid}/overlay").json()
    assert ov["batting_logo"] == f"/api/v1/teams/{ta['id']}/photo"
    assert ov["bowling_logo"] == f"/api/v1/teams/{tb['id']}/photo"
    assert ov["striker"]["photo"] == f"/api/v1/players/{pa[0]}/photo"
    assert ov["bowler"]["photo"] == f"/api/v1/players/{pb[2]}/photo"   # Bumrah

    client.delete(f"/api/v1/matches/{mid}")
    for p in pa + pb:
        client.delete(f"/api/v1/players/{p}")
    client.delete(f"/api/v1/teams/{ta['id']}")
    client.delete(f"/api/v1/teams/{tb['id']}")


def test_overlay_404_for_missing_match():
    assert client.get("/api/v1/matches/99999999/overlay").status_code == 404
    assert client.get("/overlay/99999999").status_code == 404
