"""Player-profile shot analytics: batter wagon rollups (off/leg %, six %, top zone,
runs-by-zone) and bowler pitch rollups (length distribution, economy by length),
aggregated from tracked shots across a player's matches."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

RULES = {"name": "T20", "format_id": "t20", "players_per_side": 3, "overs_per_innings": 2, "balls_per_over": 6}


def test_batter_and_bowler_shot_insights():
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
    # Gaikwad hits a 4 to the off side (yorker) then a 6 to the leg side (good length)
    client.post(f"/api/v1/matches/{mid}/balls", json={
        "action": "runs", "value": 4, "wagon_x": 0.6, "wagon_y": 0.4, "pitch_x": 0.2, "pitch_y": 0.08})
    client.post(f"/api/v1/matches/{mid}/balls", json={
        "action": "runs", "value": 6, "wagon_x": -0.4, "wagon_y": 0.3, "pitch_x": 0.0, "pitch_y": 0.40})

    bat = client.get(f"/api/v1/players/{pa[0]}/insights").json()["batting"]
    assert bat["shots_tracked"] == 2
    assert bat["off_side_pct"] == 40.0 and bat["leg_side_pct"] == 60.0   # 4 off, 6 leg
    assert bat["six_pct"] == 50.0                                        # 1 six off 2 balls
    assert bat["top_zone"]                                               # most-productive zone (the six)
    assert sum(bat["runs_by_zone"].values()) == 10

    bowl = client.get(f"/api/v1/players/{pb[2]}/insights").json()["bowling"]
    assert bowl["pitches_tracked"] == 2
    assert bowl["length_dist"].get("Yorker") == 1 and bowl["length_dist"].get("Good Length") == 1
    assert "Yorker" in bowl["econ_by_length"] and "Good Length" in bowl["econ_by_length"]

    client.delete(f"/api/v1/matches/{mid}")
    for p in pa + pb:
        client.delete(f"/api/v1/players/{p}")
    client.delete(f"/api/v1/teams/{ta['id']}")
    client.delete(f"/api/v1/teams/{tb['id']}")


def test_insights_shot_fields_empty_without_tracking():
    ta = client.post("/api/v1/teams", json={"name": "AA"}).json()
    pa = [client.post("/api/v1/players", json={"name": n}).json()["id"] for n in ("X1", "X2", "X3")]
    ins = client.get(f"/api/v1/players/{pa[0]}/insights").json()
    assert ins["batting"]["shots_tracked"] == 0 and ins["batting"]["runs_by_zone"] == {}
    assert ins["bowling"]["length_dist"] == {}
    for p in pa:
        client.delete(f"/api/v1/players/{p}")
    client.delete(f"/api/v1/teams/{ta['id']}")
