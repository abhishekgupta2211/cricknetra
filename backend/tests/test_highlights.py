"""Auto highlights reel (Option B) — key moments derived from the ball log."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _new_match() -> str:
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "Alpha", "team_b": "Bravo", "format_id": "t20", "bat_first": "a"},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Bravo 1"})
    return mid


def _six(mid: str, over: list[int]) -> None:
    """Hit a six; if the over just ended, bring on the alternating bowler."""
    st = client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 6}).json()
    if st.get("awaiting_bowler"):
        over[0] += 1
        client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": f"Bravo {1 + over[0] % 2}"})


def test_highlights_capture_boundaries_and_wickets():
    mid = _new_match()
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 6})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 1})   # not notable
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "wicket", "dismissal": "bowled"})

    hl = client.get(f"/api/v1/matches/{mid}/highlights").json()
    kinds = [h["kind"] for h in hl]
    assert "six" in kinds and "four" in kinds and "wicket" in kinds
    assert "dot" not in kinds and "run" not in kinds  # singles/dots are never highlights

    six = next(h for h in hl if h["kind"] == "six")
    assert six["over_ball"] and six["title"] == "SIX" and six["team"] == "Alpha"
    assert any(h["kind"] == "innings" for h in hl)  # an innings summary line is always present


def test_highlights_include_fifty_milestone():
    mid = _new_match()
    over = [0]
    for _ in range(15):  # 15 sixes → the opener crosses fifty despite strike rotation
        _six(mid, over)
    hl = client.get(f"/api/v1/matches/{mid}/highlights").json()
    fifties = [h for h in hl if h["kind"] in ("fifty", "hundred")]
    assert fifties, [h["kind"] for h in hl]
    assert "Alpha" in fifties[0]["text"]


def test_highlights_missing_match_is_404():
    assert client.get("/api/v1/matches/999999/highlights").status_code == 404
