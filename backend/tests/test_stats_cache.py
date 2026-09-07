"""Stats caching — memoise expensive aggregates, recompute only after a mutation (#143)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import get_stats_service
from app.main import app

client = TestClient(app)

_RULES = {"name": "Mini", "format_id": "mini", "overs_per_innings": 5, "players_per_side": 4, "balls_per_over": 6}


def _stats():
    return app.dependency_overrides[get_stats_service]()


def _player(n):
    return client.post("/api/v1/players", json={"name": n}).json()["id"]


def _scored_match():
    ids = {n: _player(n) for n in ["A1", "A2", "A3", "B1", "B2", "B3"]}
    mid = client.post("/api/v1/matches", json={
        "team_a": "Aces", "team_b": "Blues", "bat_first": "a", "rules": _RULES,
        "squad_a": ["A1", "A2", "A3"], "squad_b": ["B1", "B2", "B3"],
        "squad_a_ids": [ids["A1"], ids["A2"], ids["A3"]],
        "squad_b_ids": [ids["B1"], ids["B2"], ids["B3"]],
    }).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "B1"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})  # A1: 4
    return mid, ids


def test_data_version_changes_on_each_mutation():
    svc = _stats()
    v0 = svc.match_repo.data_version()
    mid, _ = _scored_match()  # create + bowler + ball
    v1 = svc.match_repo.data_version()
    assert v1 != v0
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})
    assert svc.match_repo.data_version() != v1


def test_leaderboards_cached_until_a_mutation():
    mid, _ = _scored_match()
    svc = _stats()
    base = svc._leaderboard_computes
    svc.leaderboards()
    assert svc._leaderboard_computes == base + 1  # first call computes
    svc.leaderboards()
    svc.leaderboards()
    assert svc._leaderboard_computes == base + 1  # served from cache, no recompute
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})  # mutation
    svc.leaderboards()
    assert svc._leaderboard_computes == base + 2  # version moved → recomputed


def test_leaderboards_never_serve_stale_data():
    mid, ids = _scored_match()  # A1 has 4
    svc = _stats()
    lb = svc.leaderboards()
    assert next((e.value for e in lb.most_runs if e.player_id == ids["A1"]), 0) == 4
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 6})  # A1 → 10
    lb2 = svc.leaderboards()
    assert next((e.value for e in lb2.most_runs if e.player_id == ids["A1"]), 0) == 10


def test_player_stats_cache_is_fresh_after_mutation():
    mid, ids = _scored_match()  # A1: 4
    r1 = client.get(f"/api/v1/players/{ids['A1']}/stats").json()["batting"]["runs"]
    assert r1 == 4
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})  # A1: 8
    r2 = client.get(f"/api/v1/players/{ids['A1']}/stats").json()["batting"]["runs"]
    assert r2 == 8  # cache invalidated, not the stale 4
