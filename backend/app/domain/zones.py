"""Pure geometry → named cricket zones.

Turns normalised wagon-wheel and pitch-map coordinates into the field/length/line
names broadcasts show. No engine or I/O deps, so it's trivially unit-testable and
reused by the scorecard, analytics, overlay and PDF alike.

Conventions
-----------
Wagon shot direction (right-hander): ``x`` = off(+)/leg(-), ``y`` = straight in
front(+)/behind the wicket(-); both normalised to roughly -1..1 from the striker.
Pitch map: ``x`` = line, -1 (down leg) .. +1 (wide outside off); ``y`` = length,
0 (yorker, at the batter) .. 1 (bouncer, bounced short).
"""

from __future__ import annotations

import math
from typing import Optional


def wagon_zone(x: Optional[float], y: Optional[float]) -> str:
    """Fielding region a shot travelled to (right-hander convention). Prefixes
    ``Long``/``Deep`` when the shot carried toward the boundary."""
    if x is None or y is None:
        return ""
    deg = math.degrees(math.atan2(x, y))   # 0 straight, +off, -leg, ±180 behind
    dist = min(1.0, math.hypot(x, y))
    deep = dist >= 0.72
    a = abs(deg)

    # straight down the ground splits by off/leg for the "Long on/off" names
    if a <= 22.5:
        if deg >= 0:   # straight, off side
            return "Long Off" if deep else "Mid Off"
        return "Long On" if deep else "Mid On"   # straight, leg side
    if deg > 0:   # off side
        if deg <= 50:  return "Deep Cover" if deep else "Cover"
        if deg <= 100: return "Deep Point" if deep else "Point"
        if deg <= 135: return "Third Man" if deep else "Gully"
        return "Fine Third"
    else:         # leg side
        if a <= 50:  return "Deep Mid Wicket" if deep else "Mid Wicket"
        if a <= 100: return "Deep Square Leg" if deep else "Square Leg"
        if a <= 135: return "Long Leg" if deep else "Backward Square Leg"
        return "Fine Leg"


def wagon_side(x: Optional[float]) -> str:
    """"off" | "leg" | "" — which side of the wicket a shot went (right-hander)."""
    if x is None:
        return ""
    return "off" if x >= 0 else "leg"


def pitch_length(y: Optional[float]) -> str:
    """Bowling length band from the pitch-map ``y`` (0 = yorker .. 1 = bouncer)."""
    if y is None:
        return ""
    if y < 0.12: return "Yorker"
    if y < 0.28: return "Full"
    if y < 0.52: return "Good Length"
    if y < 0.72: return "Back of Length"
    if y < 0.90: return "Short"
    return "Bouncer"


def pitch_line(x: Optional[float]) -> str:
    """Bowling line band from the pitch-map ``x`` (-1 = down leg .. +1 = wide off)."""
    if x is None:
        return ""
    if x < -0.6: return "Down Leg"
    if x < -0.25: return "Leg Stump"
    if x < 0.15: return "Middle"
    if x < 0.5: return "Off Stump"
    if x < 0.8: return "Outside Off"
    return "Wide Outside Off"


def ball_outcome(runs: int, wicket: bool, four_value: int = 4, six_value: int = 6) -> str:
    """Coarse outcome label used to colour a pitch-map dot / wagon line."""
    if wicket:
        return "wicket"
    if runs >= six_value:
        return "six"
    if runs >= four_value:
        return "four"
    return {0: "dot", 1: "single", 2: "two", 3: "three"}.get(runs, "runs")
