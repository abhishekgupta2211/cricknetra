"""Leaderboard scoping by place (team location) and time window (#139)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_seq = [0]


def _uid() -> str:
    _seq[0] += 1
    return f"139_{_seq[0]}"


def _pl(name: str) -> dict:
    return {"id": client.post("/api/v1/players", json={"name": name}).json()["id"], "name": name}


def _team(name: str, loc: str) -> str:
    return client.post("/api/v1/teams", json={"name": name, "location": loc}).json()["id"]


def _scored(team_a: str, loc_a: str, team_b: str, loc_b: str, batter_name: str) -> str:
    """A 1-over match where `batter_name` (team A) hammers 6 fours (24 runs)."""
    u = _uid()
    ta, tb = _team(team_a, loc_a), _team(team_b, loc_b)
    batter, bowler = _pl(batter_name), _pl(f"bowl_{u}")
    fil = [_pl(f"f{i}_{u}") for i in range(4)]
    mid = client.post("/api/v1/matches", json={
        "team_a": team_a, "team_b": team_b, "bat_first": "a",
        "rules": {"name": "Mini", "format_id": "mini", "overs_per_innings": 1, "balls_per_over": 6},
        "squad_a": [batter["name"], fil[0]["name"], fil[1]["name"]],
        "squad_b": [bowler["name"], fil[2]["name"], fil[3]["name"]],
        "squad_a_ids": [batter["id"], fil[0]["id"], fil[1]["id"]],
        "squad_b_ids": [bowler["id"], fil[2]["id"], fil[3]["id"]],
        "team_a_id": ta, "team_b_id": tb,
    }).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler["name"]})
    for _ in range(6):
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})
    return mid


def _runs_names(board) -> list[str]:
    return [e["name"] for e in board["most_runs"]]


def test_location_scope():
    _scored("AcesP139", "Pune139", "BluesP139", "Pune139", "RunnerPune139")
    _scored("RoyalsM139", "Mumbai139", "KingsM139", "Mumbai139", "RunnerMumbai139")

    pune = client.get("/api/v1/leaderboards?location=Pune139").json()
    assert "RunnerPune139" in _runs_names(pune)
    assert "RunnerMumbai139" not in _runs_names(pune)
    assert pune["location"] == "Pune139"
    assert "Pune139" in pune["locations"] and "Mumbai139" in pune["locations"]

    mum = client.get("/api/v1/leaderboards?location=Mumbai139").json()
    assert "RunnerMumbai139" in _runs_names(mum)
    assert "RunnerPune139" not in _runs_names(mum)

    everywhere = client.get("/api/v1/leaderboards").json()
    assert "RunnerPune139" in _runs_names(everywhere)
    assert "RunnerMumbai139" in _runs_names(everywhere)
    assert everywhere["location"] is None


def test_location_scope_is_case_insensitive_substring():
    _scored("Strikers139", "Bangalore139", "Chargers139", "Bangalore139", "RunnerBlr139")
    board = client.get("/api/v1/leaderboards?location=bangalore139").json()  # lower-case
    assert "RunnerBlr139" in _runs_names(board)


def test_time_window_scope():
    _scored("TA139", "TZ139", "TB139", "TZ139", "TimeRunner139")

    yr = client.get("/api/v1/leaderboards?window=year").json()
    assert "TimeRunner139" in _runs_names(yr)
    assert yr["window"] == "year"

    # an explicit future cutoff excludes every match (all created "now")
    fut = client.get("/api/v1/leaderboards?since=2999-01-01T00:00:00Z").json()
    assert fut["most_runs"] == []
    assert fut["window"] == "custom"

    # an explicit past cutoff includes everything
    past = client.get("/api/v1/leaderboards?since=2000-01-01T00:00:00Z").json()
    assert "TimeRunner139" in _runs_names(past)


def test_unknown_window_falls_back_to_all():
    _scored("WA139", "WZ139", "WB139", "WZ139", "WindowRunner139")
    board = client.get("/api/v1/leaderboards?window=decade").json()
    assert board["window"] == "all"
    assert "WindowRunner139" in _runs_names(board)
