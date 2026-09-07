"""Duckworth–Lewis–Stern (DLS) rain-rule calculator — Standard Edition.

The resource curve is the Duckworth–Lewis **Standard Edition** model: for each
number of wickets down, resources decay exponentially with the overs remaining,

    R(u, w) = A[w] · (1 − e^(−b[w]·u)) / (1 − e^(−b[w]·50))

so R(50, w) = A[w] (the published left-most column) and R(50, 0) = 100 exactly.
The per-wicket decay ``b[w]`` is least-squares fitted to the published Standard
Edition resource table (50…1 overs × 0…9 wickets); it reproduces every published
anchor to within ≈0.05 of a percentage point (see ``tests/test_dls_calc.py``). This
matches the method club / associate cricket and apps like CricHeroes use.

The engine is deliberately separated from its data: to move to the licensed ICC
*Professional* Edition later, swap ``_A`` / ``_B`` (or ``resource_pct`` itself) and
every consumer — target, par, interruptions, verdict — follows unchanged.

    resources are always a % of a FULL 50-over innings (100% = a fresh 50 overs).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Standard-Edition resource % with a full 50 overs remaining and w wickets down —
# the table's left-most column (R(50, w)). R(50, 0) = 100 by definition.
_A = [100.0, 93.4, 85.1, 74.9, 62.7, 49.0, 34.9, 22.0, 11.9, 4.7]

# Per-wicket exponential decay, least-squares fitted to the full published Standard
# Edition table. Higher wickets deplete resources far faster (a tail-ender adds little),
# which the old single-slope approximation got badly wrong (b[5] was ~0.043 vs 0.073).
_B = [0.02740, 0.03105, 0.03610, 0.04350, 0.05485,
      0.07295, 0.10505, 0.16805, 0.31255, 0.60060]

# Average first-innings 50-over score — the reference used only when the chasing
# side has MORE resources than the side that set the total (ICC men's value).
G50_DEFAULT = 245


def _clampw(wickets: int) -> int:
    return max(0, min(9, int(wickets)))


def resource_pct(overs_left: float, wickets: int) -> float:
    """Run-scoring resources still available with ``overs_left`` overs to go and
    ``wickets`` down, as a % of a full 50-over innings (0–100)."""
    w = _clampw(wickets)
    u = max(0.0, float(overs_left))
    b = _B[w]
    shape = (1.0 - math.exp(-b * u)) / (1.0 - math.exp(-b * 50.0))
    return round(_A[w] * shape, 1)


def overs_from_balls(balls: int, bpo: int = 6) -> float:
    """Legal balls → decimal overs (34 balls, 6/over → 5.667)."""
    return balls / bpo if bpo else 0.0


# --------------------------------------------------------------------------- #
# Interruptions — a cut in the overs remaining costs resources
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Cut:
    """One overs-reduction: at ``wickets`` down, the overs still to come were cut
    from ``overs_before`` to ``overs_after`` (both = overs REMAINING at that moment)."""
    overs_before: float
    wickets: int
    overs_after: float


def resources_lost(overs_before: float, wickets: int, overs_after: float) -> float:
    """Resources a team loses when an interruption cuts the remaining overs from
    ``overs_before`` to ``overs_after`` with ``wickets`` down. Never negative."""
    return max(0.0, resource_pct(overs_before, wickets) - resource_pct(overs_after, wickets))


def innings_resources(original_overs: float, cuts: "list[Cut] | None" = None) -> float:
    """Total resource % available to an innings scheduled for ``original_overs`` overs
    (0 wickets down at the start), after a sequence of mid-innings ``cuts``. Handles
    any number of interruptions — each one's loss is computed at the wickets down when
    it happened and summed. Clamped to [0, 100]."""
    r = resource_pct(original_overs, 0)
    for c in (cuts or []):
        r -= resources_lost(c.overs_before, c.wickets, c.overs_after)
    return round(max(0.0, min(100.0, r)), 1)


# --------------------------------------------------------------------------- #
# Target + par
# --------------------------------------------------------------------------- #
def revised_target(s1: int, r1: float, r2: float, g50: int = G50_DEFAULT) -> int:
    """Team 2's target (runs to win) given team 1 made ``s1`` with ``r1``% resources
    and team 2 has ``r2``%.
      • r2 ≤ r1 → scale the total down by the resource ratio.
      • r2 > r1 → team 2 gained resources (team 1 was cut short): add a G50-weighted
        bonus for the extra resources."""
    if r1 <= 0:
        return s1 + 1
    if r2 <= r1:
        return int(math.floor(s1 * r2 / r1)) + 1
    return int(s1 + math.floor(g50 * (r2 - r1) / 100.0)) + 1


def par_score(s1: int, r1: float, resources_used_by_team2: float) -> int:
    """The score team 2 should be LEVEL with, having used ``resources_used``%.
    Team 2 is ahead if its score exceeds this; a match abandoned here is won by
    team 2 iff its score is at least par + 1 (level = tie)."""
    if r1 <= 0:
        return 0
    return int(math.floor(s1 * resources_used_by_team2 / r1))


def verdict(second_score: int, par: int) -> int:
    """Result sign for a DLS-decided (e.g. abandoned) chase: +1 team 2 won,
    0 tie (level with par), −1 team 1 (defending side) won. Margin = |score − par|."""
    if second_score > par:
        return 1
    if second_score < par:
        return -1
    return 0


def chase(s1: int, team1_overs: float, team2_overs: float,
          faced_overs: float = 0.0, wickets: int = 0, g50: int = G50_DEFAULT,
          team1_cuts: "list[Cut] | None" = None,
          team2_cuts: "list[Cut] | None" = None) -> dict:
    """Full chase calculation. Team 1 finished on ``s1``; team 1 and team 2 each had
    their scheduled overs, less any interruption ``cuts``. Returns the revised target
    plus a live par at the current (``faced_overs``, ``wickets``) point of the chase.

    ``team2_overs`` is team 2's TOTAL available overs (after any reduction applied
    before this point). Extra mid-chase cuts still to model go in ``team2_cuts``.
    """
    r1 = innings_resources(team1_overs, team1_cuts)   # team 1's resources (100 if uninterrupted 50)
    r2 = innings_resources(team2_overs, team2_cuts)   # team 2's total available resources
    target = revised_target(s1, r1, r2, g50)
    overs_left = max(0.0, team2_overs - faced_overs)
    used = max(0.0, r2 - resource_pct(overs_left, wickets))  # resources team 2 has spent
    par = par_score(s1, r1, used)
    return {
        "target": target,
        "par": par,
        "r1": round(r1, 1),
        "r2": round(r2, 1),
        "resources_used": round(used, 1),
        "overs_left": round(overs_left, 3),
    }
