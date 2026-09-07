"""Match-impact score: the MoM carries an impact number on the overlay, and the
scorecard report exposes a top-impact list."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.match_service import MatchService

client = TestClient(app)

RULES = {"name": "T20", "format_id": "t20", "players_per_side": 3, "overs_per_innings": 1, "balls_per_over": 6}


def _completed_match() -> str:
    mid = client.post("/api/v1/matches", json={
        "team_a": "CSK", "team_b": "MI", "bat_first": "a", "rules": RULES,
        "squad_a": ["Gaikwad", "Jadeja", "Dhoni"], "squad_b": ["Rohit", "Surya", "Bumrah"]},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Bumrah"})
    for ball in ({"action": "runs", "value": 6}, {"action": "runs", "value": 4},
                 {"action": "runs", "value": 2}, {"action": "runs", "value": 1},
                 {"action": "runs", "value": 1}, {"action": "runs", "value": 0}):
        client.post(f"/api/v1/matches/{mid}/balls", json=ball)
    client.post(f"/api/v1/matches/{mid}/second-innings")
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Jadeja"})
    for ball in ({"action": "runs", "value": 1}, {"action": "wicket", "dismissal": "bowled"},
                 {"action": "runs", "value": 0}, {"action": "runs", "value": 0},
                 {"action": "runs", "value": 0}, {"action": "runs", "value": 0}):
        client.post(f"/api/v1/matches/{mid}/balls", json=ball)
    return mid


def test_mom_impact_on_overlay():
    mid = _completed_match()
    ov = client.get(f"/api/v1/matches/{mid}/overlay").json()
    assert ov["complete"] is True
    mom = ov["awards"]["man_of_the_match"]
    assert isinstance(mom["impact"], int) and mom["impact"] > 0
    client.delete(f"/api/v1/matches/{mid}")


def test_impact_table_ranks_players():
    """The impact table (a pure projection of the state) sorts sensibly and credits
    the opener who hit the boundaries."""
    from app.schemas.match import MatchStateDTO

    mid = _completed_match()
    dto = MatchStateDTO.model_validate(client.get(f"/api/v1/matches/{mid}").json())
    tbl = MatchService._impact_table(dto)
    top = sorted(tbl.values(), key=lambda s: -s["impact"])
    assert top[0]["impact"] >= top[-1]["impact"]      # sorted, best first
    assert tbl["Gaikwad"]["bat"] > 0                  # the opener who hit the 6 + 4
    assert MatchService._mom_impact(dto) is not None
    client.delete(f"/api/v1/matches/{mid}")
