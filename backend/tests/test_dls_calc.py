"""DLS calculator (app.domain.dls) — algorithm correctness + Standard-Edition anchors."""

from __future__ import annotations

import pytest

from app.domain import dls


# ---- resource curve: boundaries + monotonicity ----
def test_full_50_over_innings_is_100_percent():
    assert dls.resource_pct(50, 0) == 100.0


def test_zero_overs_left_is_zero_resources():
    for w in range(10):
        assert dls.resource_pct(0, w) == 0.0


def test_resources_decrease_as_overs_are_used():
    prev = 101.0
    for overs_left in (50, 40, 30, 20, 10, 5, 1, 0):
        r = dls.resource_pct(overs_left, 0)
        assert r < prev, (overs_left, r, prev)
        prev = r


def test_resources_decrease_as_wickets_fall():
    prev = 101.0
    for w in range(10):
        r = dls.resource_pct(50, w)
        assert r < prev, (w, r, prev)
        prev = r


@pytest.mark.parametrize("overs_left,expected", [(50, 100.0), (30, 75.1), (20, 56.6), (10, 32.1)])
def test_standard_edition_zero_wicket_anchors(overs_left, expected):
    assert dls.resource_pct(overs_left, 0) == pytest.approx(expected, abs=1.0)


def test_fifty_over_remaining_wicket_column_matches_anchors():
    assert [dls.resource_pct(50, w) for w in range(10)] == dls._A


# ---- target formula ----
def test_uninterrupted_equal_overs_target_is_score_plus_one():
    c = dls.chase(s1=160, team1_overs=20, team2_overs=20)
    assert c["target"] == 161
    assert c["r1"] == c["r2"]


def test_reduced_chase_lowers_the_target():
    c = dls.chase(s1=200, team1_overs=50, team2_overs=25)
    assert 100 < c["target"] < 201, c
    assert c["r2"] < c["r1"]


def test_team2_with_more_resources_raises_target_via_g50():
    t = dls.revised_target(s1=150, r1=dls.resource_pct(25, 0), r2=dls.resource_pct(50, 0))
    assert t > 151, t


# ---- par score ----
def test_par_score_tracks_the_chase():
    c = dls.chase(s1=200, team1_overs=50, team2_overs=50, faced_overs=25, wickets=2)
    assert 0 < c["par"] < 200
    # 25 of 50 overs used with 2 down leaves R(25,2)=60.5% → ~39.5% spent
    assert 35 < c["resources_used"] < 70, c


def test_par_at_start_is_zero_and_at_end_is_the_total():
    start = dls.chase(s1=180, team1_overs=20, team2_overs=20, faced_overs=0, wickets=0)
    assert start["par"] == 0
    end = dls.chase(s1=180, team1_overs=20, team2_overs=20, faced_overs=20, wickets=0)
    assert end["par"] == 180


# ---- accuracy: reproduce the full published Standard Edition resource table ----
# overs remaining → [w0, w1, … w9]  (the published anchors)
_ANCHORS = {
    50: [100, 93.4, 85.1, 74.9, 62.7, 49, 34.9, 22, 11.9, 4.7],
    45: [95, 89.1, 81.8, 72.5, 61.3, 48.4, 34.8, 22, 11.9, 4.7],
    40: [89.3, 84.2, 77.8, 69.6, 59.5, 47.6, 34.6, 22, 11.9, 4.7],
    35: [82.7, 78.5, 73, 66, 57.2, 46.4, 34.2, 21.9, 11.9, 4.7],
    30: [75.1, 71.8, 67.3, 61.6, 54.1, 44.7, 33.6, 21.8, 11.9, 4.7],
    25: [66.5, 63.9, 60.5, 56, 50, 42.2, 32.6, 21.6, 11.9, 4.7],
    20: [56.6, 54.8, 52.4, 49.1, 44.6, 38.6, 30.8, 21.2, 11.9, 4.7],
    15: [45.2, 44.1, 42.6, 40.5, 37.6, 33.5, 27.8, 20.2, 11.8, 4.7],
    10: [32.1, 31.6, 30.8, 29.8, 28.3, 26.1, 22.8, 17.9, 11.4, 4.7],
    5: [17.2, 17, 16.8, 16.5, 16.1, 15.4, 14.3, 12.5, 9.4, 4.6],
}


def test_resource_curve_reproduces_published_table_within_a_fifth_of_a_point():
    worst = 0.0
    for overs, row in _ANCHORS.items():
        for w, want in enumerate(row):
            got = dls.resource_pct(overs, w)
            worst = max(worst, abs(got - want))
    assert worst < 0.25, f"worst deviation from published table = {worst}"


# ---- known DLS worked examples (targets that match ICC / CricHeroes) ----
def test_worked_example_250_off_50_chase_of_40_overs():
    # Team 1: 250/50 (uninterrupted). Team 2 reduced to 40 overs before they start.
    t = dls.revised_target(250, dls.resource_pct(50, 0), dls.resource_pct(40, 0))
    assert t == 224            # par 223 → 224 to win (the classic D/L result)


def test_worked_example_team1_curtailed_uses_g50_bonus():
    # Team 1 bowled only 40 overs for 200 (R1=89.3); Team 2 has a full 50 (R2=100).
    t = dls.revised_target(200, dls.resource_pct(40, 0), dls.resource_pct(50, 0))
    assert t == 227            # 200 + floor(245·0.107) + 1


# ---- interruption resource accounting (the core the old calculator lacked) ----
def test_single_mid_innings_interruption_loses_the_right_resources():
    # 50-over innings, cut at 30 overs remaining / 2 down to 20 remaining.
    cuts = [dls.Cut(overs_before=30, wickets=2, overs_after=20)]
    r = dls.innings_resources(50, cuts)
    # loss = R(30,2) − R(20,2) ≈ 67.3 − 52.4 = 14.9 → ~85.1% left
    assert 84.5 < r < 85.6, r


def test_multiple_interruptions_stack():
    cuts = [dls.Cut(30, 1, 25), dls.Cut(15, 4, 10)]     # two separate stoppages
    r = dls.innings_resources(50, cuts)
    lost = dls.resources_lost(30, 1, 25) + dls.resources_lost(15, 4, 10)
    assert r == round(100.0 - lost, 1)
    assert r < dls.innings_resources(50, [dls.Cut(30, 1, 25)])   # more cuts → fewer resources


def test_uninterrupted_full_innings_is_100_percent():
    assert dls.innings_resources(50, []) == 100.0


def test_resources_lost_never_negative():
    assert dls.resources_lost(20, 3, 30) == 0.0          # "cut" that adds overs costs nothing


# ---- abandonment verdict ----
def test_verdict_signs():
    assert dls.verdict(second_score=120, par=110) == 1   # team 2 ahead of par → win
    assert dls.verdict(second_score=100, par=110) == -1  # behind par → team 1 win
    assert dls.verdict(second_score=110, par=110) == 0   # level → tie
