"""Tournament depth — group stage + seeded playoffs + configurable points (#141)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.tournament_service import TournamentService

client = TestClient(app)

_MINI = {"name": "Mini", "format_id": "mini", "overs_per_innings": 1, "players_per_side": 2, "balls_per_over": 6}


# ----- pure helpers ---------------------------------------------------------
def test_partition_groups_deals_evenly():
    groups = TournamentService._partition_groups(["1", "2", "3", "4", "5"], 2)
    assert groups == {"A": ["1", "3", "5"], "B": ["2", "4"]}


def test_seed_playoff_cross_seeds_winner_vs_other_runner_up():
    finishers = {"A": ["a1", "a2"], "B": ["b1", "b2"]}
    # A1 v B2, B1 v A2  → order [a1, b2, b1, a2]
    assert TournamentService._seed_playoff(finishers, 2) == ["a1", "b2", "b1", "a2"]
    # top-1 from each of three groups → winners only
    assert TournamentService._seed_playoff({"A": ["a1"], "B": ["b1"], "C": ["c1"]}, 1) == ["a1", "b1", "c1"]


# ----- setup helpers --------------------------------------------------------
def _team(n):
    return client.post("/api/v1/teams", json={"name": n}).json()["id"]


def _player(n):
    return client.post("/api/v1/players", json={"name": n}).json()["id"]


_PL = {}


def _ensure_players():
    if not _PL:
        for n in ("Bat1", "Bat2", "Bwl1", "Bwl2"):
            _PL[n] = _player(n)


def _complete(fid, bat_first="a"):
    """Start a fixture and play it so the bat-first side wins by 12."""
    st = client.post(f"/api/v1/tournaments/fixtures/{fid}/start", json={
        "squad_a_ids": [_PL["Bat1"], _PL["Bat2"]],
        "squad_b_ids": [_PL["Bwl1"], _PL["Bwl2"]],
        "bat_first": bat_first,
    }).json()
    mid = st["match_id"]
    bowl1, bowl2 = ("Bwl1", "Bat1") if bat_first == "a" else ("Bat1", "Bwl1")
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowl1})
    for v in (6, 6, 0, 0, 0, 0):
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": v})
    client.post(f"/api/v1/matches/{mid}/second-innings")
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowl2})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "wicket", "dismissal": "bowled"})
    return mid


# ----- create structure -----------------------------------------------------
def test_groups_create_structure():
    _ensure_players()
    ids = [_team(f"G{i}_141a") for i in range(4)]
    t = client.post("/api/v1/tournaments", json={
        "name": "Pool Cup", "format": "groups", "team_ids": ids,
        "num_groups": 2, "advance_per_group": 1, "win_points": 3, "rules": _MINI,
    }).json()
    assert t["format"] == "groups"
    assert t["config"]["num_groups"] == 2 and t["config"]["win_points"] == 3
    assert set(t["config"]["groups"].keys()) == {"A", "B"}
    # two pools of two → one group fixture each, all labelled, no bracket yet
    gfx = [f for f in t["fixtures"] if f["group"]]
    assert len(gfx) == 2 and {f["group"] for f in gfx} == {"A", "B"}
    assert not [f for f in t["fixtures"] if f["group"] is None]
    assert len(t["groups"]) == 2 and all(len(g["standings"]) == 2 for g in t["groups"])
    assert t["champion"] is None


def test_groups_full_pipeline_to_champion():
    _ensure_players()
    ids = [_team(f"P{i}_141b") for i in range(4)]
    t = client.post("/api/v1/tournaments", json={
        "name": "Playoff Cup", "format": "groups", "team_ids": ids,
        "num_groups": 2, "advance_per_group": 1, "win_points": 3, "rules": _MINI,
    }).json()
    tid = t["id"]

    # play both group games
    for f in [f for f in t["fixtures"] if f["group"]]:
        _complete(f["id"])

    # the playoff final is auto-generated from the two group winners
    t = client.get(f"/api/v1/tournaments/{tid}").json()
    bracket = [f for f in t["fixtures"] if f["group"] is None]
    assert len(bracket) == 1  # 2 advancers → a single final
    assert t["champion"] is None  # not played yet
    # a group winner earned 3 points (configurable points applied)
    winners_pts = [s["points"] for g in t["groups"] for s in g["standings"] if s["won"] == 1]
    assert winners_pts and all(p == 3 for p in winners_pts)

    # play the final → champion crowned
    _complete(bracket[0]["id"])
    t = client.get(f"/api/v1/tournaments/{tid}").json()
    assert t["champion"] is not None
    advancers = {g["standings"][0]["team_id"] for g in t["groups"]}
    assert t["champion"]["id"] in advancers


def test_configurable_points_on_round_robin():
    _ensure_players()
    a, b = _team("RR141_A"), _team("RR141_B")
    t = client.post("/api/v1/tournaments", json={
        "name": "League Pts", "format": "round_robin", "team_ids": [a, b],
        "win_points": 4, "rules": _MINI,
    }).json()
    tid = t["id"]
    _complete(t["fixtures"][0]["id"])
    t = client.get(f"/api/v1/tournaments/{tid}").json()
    top = t["standings"][0]
    assert top["won"] == 1 and top["points"] == 4  # 1 win × 4 points


def test_groups_rejects_too_many_groups():
    ids = [_team(f"X{i}_141c") for i in range(3)]
    r = client.post("/api/v1/tournaments", json={
        "name": "Bad", "format": "groups", "team_ids": ids, "num_groups": 2, "rules": _MINI,
    })
    assert r.status_code == 400  # 3 teams can't make 2 pools of ≥2
