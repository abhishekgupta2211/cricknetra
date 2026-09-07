"""Pure zone geometry — wagon field regions + pitch length/line bands."""

from __future__ import annotations

from app.domain import zones


def test_pitch_length_bands():
    assert zones.pitch_length(0.05) == "Yorker"
    assert zones.pitch_length(0.20) == "Full"
    assert zones.pitch_length(0.40) == "Good Length"
    assert zones.pitch_length(0.60) == "Back of Length"
    assert zones.pitch_length(0.80) == "Short"
    assert zones.pitch_length(0.95) == "Bouncer"
    assert zones.pitch_length(None) == ""


def test_pitch_line_bands():
    assert zones.pitch_line(-0.80) == "Down Leg"
    assert zones.pitch_line(-0.40) == "Leg Stump"
    assert zones.pitch_line(0.00) == "Middle"
    assert zones.pitch_line(0.30) == "Off Stump"
    assert zones.pitch_line(0.65) == "Outside Off"
    assert zones.pitch_line(0.90) == "Wide Outside Off"


def test_ball_outcome():
    assert zones.ball_outcome(0, False) == "dot"
    assert zones.ball_outcome(1, False) == "single"
    assert zones.ball_outcome(2, False) == "two"
    assert zones.ball_outcome(3, False) == "three"
    assert zones.ball_outcome(4, False) == "four"
    assert zones.ball_outcome(6, False) == "six"
    assert zones.ball_outcome(0, True) == "wicket"      # wicket dominates any run count
    assert zones.ball_outcome(4, True) == "wicket"


def test_wagon_zone_directions():
    # straight down the ground → Mid/Long Off (off side) or On (leg side)
    assert zones.wagon_zone(0.0, 0.3) == "Mid Off"
    assert zones.wagon_zone(0.05, 0.9) == "Long Off"     # deep + straight-ish off
    assert zones.wagon_zone(-0.05, 0.9) == "Long On"     # deep + straight-ish leg
    # square of the wicket
    assert zones.wagon_zone(0.9, 0.05) == "Deep Point"       # square off, deep
    assert zones.wagon_zone(-0.9, 0.05) == "Deep Square Leg" # square leg, deep
    assert zones.wagon_zone(0.45, 0.5) in ("Cover", "Deep Cover")
    assert zones.wagon_zone(-0.4, 0.5) == "Mid Wicket"
    # behind the wicket, very fine
    assert zones.wagon_zone(-0.1, -0.9) == "Fine Leg"
    assert zones.wagon_zone(0.1, -0.9) == "Fine Third"
    # missing coords → empty
    assert zones.wagon_zone(None, 0.5) == ""
    assert zones.wagon_zone(0.5, None) == ""


def test_wagon_side():
    assert zones.wagon_side(0.5) == "off"
    assert zones.wagon_side(-0.5) == "leg"
    assert zones.wagon_side(None) == ""
