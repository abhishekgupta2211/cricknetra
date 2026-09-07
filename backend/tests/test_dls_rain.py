"""DLS rain interruptions end-to-end (the automatic workflow).

The scorer only ever: (1) clicks Interrupt, (2) confirms the new overs on Resume.
Everything — overs lost, resources, the revised target, par, the result — is computed
by the engine. Covers rain in each innings, after the powerplay, multiple stoppages,
abandonment, and validation.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# 4 overs a side, 2 players, DLS on, with a 2-over opening powerplay.
RULES = {
    "name": "DLS rain", "format_id": "custom",
    "players_per_side": 2, "overs_per_innings": 4, "balls_per_over": 6,
    "dls_enabled": True,
    "powerplays": [{"start_over": 1, "end_over": 2, "max_fielders_outside": 2}],
}


def _new(rules=RULES) -> str:
    return client.post("/api/v1/matches",
                       json={"team_a": "A", "team_b": "B", "bat_first": "a", "rules": rules}).json()["id"]


def _over(mid, bowler, runs=1, balls=6):
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler})
    for _ in range(balls):
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": runs})


def _state(mid):
    return client.get(f"/api/v1/matches/{mid}").json()


# --------------------------------------------------------------------------- #
# rain during the SECOND innings → auto revised target
# --------------------------------------------------------------------------- #
def test_rain_in_second_innings_revises_the_target_automatically():
    mid = _new()
    for b in ("B1", "B2", "B3", "B4"):
        _over(mid, b, runs=2)                     # A: 48 off 4 overs
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _over(mid, "A1", runs=1)                       # B faces 1 over (6/1)

    # rain — scorer clicks interrupt, then confirms the chase is cut 4 → 3 overs
    st = client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "rain"}).json()
    assert st["dls"]["pending"] is True
    st = client.post(f"/api/v1/matches/{mid}/resume", json={"overs": 3}).json()

    dls = st["dls"]
    assert dls["pending"] is False and dls["applied"] is True
    assert dls["original_overs"] == 4 and dls["revised_overs"] == 3
    assert dls["overs_lost"] == 1.0
    assert 1 <= dls["revised_target"] <= 49        # a 3-over chase of 48 needs fewer than 49
    assert st["innings"][1]["target"] == dls["revised_target"]
    assert st["innings"][1]["max_overs"] == 3      # the chase is now 3 overs
    assert dls["r2"] < dls["r1"]                    # team 2 has fewer resources
    client.delete(f"/api/v1/matches/{mid}")


# --------------------------------------------------------------------------- #
# rain during the FIRST innings → innings 1 curtailed, target set at the break
# --------------------------------------------------------------------------- #
def test_rain_in_first_innings_curtails_it_and_still_produces_a_target():
    mid = _new()
    _over(mid, "B1", runs=3)
    _over(mid, "B2", runs=3)                        # A: 36 off 2 overs

    st = client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "bad_light"}).json()
    assert st["dls"]["interruptions"][0]["innings"] == 1
    st = client.post(f"/api/v1/matches/{mid}/resume", json={"overs": 3}).json()   # A's innings cut 4 → 3
    assert st["innings"][0]["max_overs"] == 3

    _over(mid, "B3", runs=3)                        # A finishes its (now 3) overs: 54
    st = _state(mid)
    assert st["innings"][0]["is_complete"] is True
    st = client.post(f"/api/v1/matches/{mid}/second-innings").json()
    # innings 2 inherits the 3-over match; a DLS target is in place (not just runs+1)
    assert st["innings"][1]["max_overs"] == 3
    assert st["dls"]["revised_target"] == st["innings"][1]["target"]
    assert st["dls"]["r1"] < 100.0                  # team 1 lost resources to the stoppage
    client.delete(f"/api/v1/matches/{mid}")


# --------------------------------------------------------------------------- #
# rain right after the powerplay (wickets/overs captured at the stoppage)
# --------------------------------------------------------------------------- #
def test_interruption_after_powerplay_captures_position():
    mid = _new()
    for b in ("B1", "B2", "B3", "B4"):
        _over(mid, b, runs=2)
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _over(mid, "A1", runs=1)
    _over(mid, "A2", runs=1)                        # 2 overs bowled = powerplay done (6 legal/over)

    st = client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "wet_outfield"}).json()
    it = st["dls"]["interruptions"][0]
    assert it["innings"] == 2 and it["reason"] == "wet_outfield" and it["pending"] is True
    # can't cut below overs already bowled
    bad = client.post(f"/api/v1/matches/{mid}/resume", json={"overs": 1})
    assert bad.status_code == 409
    st = client.post(f"/api/v1/matches/{mid}/resume", json={"overs": 3}).json()
    assert st["innings"][1]["max_overs"] == 3 and st["dls"]["overs_lost"] == 1.0
    client.delete(f"/api/v1/matches/{mid}")


# --------------------------------------------------------------------------- #
# multiple interruptions stack
# --------------------------------------------------------------------------- #
def test_multiple_interruptions_stack_their_overs_lost():
    mid = _new()
    for b in ("B1", "B2", "B3", "B4"):
        _over(mid, b, runs=3)                       # A: 72
    client.post(f"/api/v1/matches/{mid}/second-innings")
    client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "rain"})
    client.post(f"/api/v1/matches/{mid}/resume", json={"overs": 3})     # 4 → 3
    _over(mid, "A1", runs=1)
    st = client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "rain"}).json()
    st = client.post(f"/api/v1/matches/{mid}/resume", json={"overs": 2}).json()   # 3 → 2

    dls = st["dls"]
    assert dls["overs_lost"] == 2.0 and dls["revised_overs"] == 2
    assert len([i for i in dls["interruptions"] if not i["pending"]]) == 2
    assert dls["revision_seq"] == 2
    assert st["innings"][1]["max_overs"] == 2
    client.delete(f"/api/v1/matches/{mid}")


# --------------------------------------------------------------------------- #
# abandonment → DLS verdict (or no result)
# --------------------------------------------------------------------------- #
def test_abandon_after_min_overs_decides_on_par():
    mid = _new()
    for b in ("B1", "B2", "B3", "B4"):
        _over(mid, b, runs=1)                       # A: 24 off 4 (target 25)
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _over(mid, "A1", runs=2)                        # B: 12
    _over(mid, "A2", runs=1)                        # B: 18 after 2 overs — above par (~11), below 25

    st = client.post(f"/api/v1/matches/{mid}/abandon", json={"reason": "rain"}).json()
    assert st["dls"]["abandoned"] is True
    assert st["result"] and "DLS" in st["result"] and "B won" in st["result"]
    client.delete(f"/api/v1/matches/{mid}")


def test_abandon_before_min_overs_is_no_result():
    mid = _new()
    for b in ("B1", "B2", "B3", "B4"):
        _over(mid, b, runs=1)
    client.post(f"/api/v1/matches/{mid}/second-innings")
    # min overs for a 4-over game is 2; abandon after 1 → no result
    _over(mid, "A1", runs=1)
    st = client.post(f"/api/v1/matches/{mid}/abandon", json={"reason": "rain"}).json()
    assert "No result" in st["result"]
    client.delete(f"/api/v1/matches/{mid}")


# --------------------------------------------------------------------------- #
# validation + gating
# --------------------------------------------------------------------------- #
def test_interrupt_rejected_when_dls_disabled():
    mid = _new(dict(RULES, dls_enabled=False))
    r = client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "rain"})
    assert r.status_code == 409
    client.delete(f"/api/v1/matches/{mid}")


def test_resume_without_interruption_is_rejected():
    mid = _new()
    r = client.post(f"/api/v1/matches/{mid}/resume", json={"overs": 3})
    assert r.status_code == 409
    client.delete(f"/api/v1/matches/{mid}")


def test_cannot_interrupt_twice_without_resuming():
    mid = _new()
    client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "rain"})
    r = client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "rain"})
    assert r.status_code == 409
    client.delete(f"/api/v1/matches/{mid}")


def test_revised_overs_cannot_exceed_the_innings_length():
    mid = _new()
    client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "rain"})
    r = client.post(f"/api/v1/matches/{mid}/resume", json={"overs": 6})   # > 4
    assert r.status_code == 409
    client.delete(f"/api/v1/matches/{mid}")


def test_cancel_interruption_clears_pending():
    mid = _new()
    client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "rain"})
    st = client.post(f"/api/v1/matches/{mid}/interrupt/cancel").json()
    assert st["dls"]["pending"] is False and st["dls"]["interruptions"] == []
    client.delete(f"/api/v1/matches/{mid}")


def test_dls_state_absent_when_disabled():
    mid = _new(dict(RULES, dls_enabled=False))
    assert _state(mid)["dls"] is None
    client.delete(f"/api/v1/matches/{mid}")


def test_tournament_dls_toggle():
    tids = [client.post("/api/v1/teams", json={"name": n}).json()["id"] for n in ["RainA", "RainB"]]
    t = client.post("/api/v1/tournaments", json={
        "name": "Rain Cup", "format": "round_robin", "team_ids": tids, "dls_enabled": True}).json()
    assert t["config"]["dls_enabled"] is True
    tid = t["id"]
    off = client.patch(f"/api/v1/tournaments/{tid}/settings", json={"dls_enabled": False})
    assert off.status_code == 200 and off.json()["config"]["dls_enabled"] is False
    on = client.patch(f"/api/v1/tournaments/{tid}/settings", json={"dls_enabled": True})
    assert on.json()["config"]["dls_enabled"] is True
    assert client.patch("/api/v1/tournaments/999999/settings", json={"dls_enabled": True}).status_code == 404


def test_overlay_public_and_timeline_expose_the_revision():
    mid = _new()
    for b in ("B1", "B2", "B3", "B4"):
        _over(mid, b, runs=2)
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _over(mid, "A1", runs=1)
    client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "rain"})
    tgt = client.post(f"/api/v1/matches/{mid}/resume", json={"overs": 3}).json()["dls"]["revised_target"]

    # overlay payload carries the banner data (revision_seq lets the overlay fire it once)
    ov = client.get(f"/api/v1/matches/{mid}/overlay").json()
    assert ov["dls"] and ov["dls"]["revised_target"] == tgt and ov["dls"]["revision_seq"] == 1

    # timeline (highlights) has the rain delay + DLS-applied entries
    hls = client.get(f"/api/v1/matches/{mid}/highlights").json()
    assert any(h["kind"] == "dls" and "DELAY" in h["title"] for h in hls)
    assert any(h["kind"] == "dls" and "DLS APPLIED" in h["title"] for h in hls)

    # the public scorecard renders the revised target + the Rain/DLS box
    pub = client.get(f"/m/{mid}").text
    assert str(tgt) in pub and "Rain / DLS" in pub
    client.delete(f"/api/v1/matches/{mid}")


def test_resume_posts_auto_commentary():
    mid = _new()
    for b in ("B1", "B2", "B3", "B4"):
        _over(mid, b, runs=2)
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _over(mid, "A1", runs=1)
    client.post(f"/api/v1/matches/{mid}/interrupt", json={"reason": "rain"})
    client.post(f"/api/v1/matches/{mid}/resume", json={"overs": 3})
    lines = [c["text"] for c in client.get(f"/api/v1/matches/{mid}/commentary").json()]
    assert any("Rain has stopped play" in t for t in lines)
    assert any("DLS revised target" in t for t in lines)
    client.delete(f"/api/v1/matches/{mid}")
