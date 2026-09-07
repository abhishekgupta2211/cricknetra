"""Per-match broadcast presentation mode — which analysis screen the single OBS
browser source is currently showing.

Process-local + in-memory on purpose: it's transient control state, not match data.
On restart it resets to LIVE (the failsafe). Public, same trust model as the overlay
page itself. The operator's control tab POSTs a mode; every open overlay instance
(including the one inside OBS) polls and cross-fades to it — no OBS scene switching.
"""

from __future__ import annotations

MODES = {"LIVE", "WORM", "WAGON", "PITCH", "PARTNERSHIP", "SUMMARY"}

# match_id -> {"mode": str, "auto": bool, "seq": int}
_state: dict[str, dict] = {}


def get_broadcast(match_id: str) -> dict:
    return dict(_state.get(match_id) or {"mode": "LIVE", "auto": False, "seq": 0})


def set_broadcast(match_id: str, mode=None, auto=None) -> dict:
    cur = get_broadcast(match_id)
    changed = False
    if mode is not None:
        m = str(mode).upper()
        if m not in MODES:
            raise ValueError(f"unknown broadcast mode '{mode}'")
        if m != cur["mode"]:
            cur["mode"] = m
            changed = True
    if auto is not None:
        a = bool(auto)
        if a != cur["auto"]:
            cur["auto"] = a
            changed = True
    if changed:
        cur["seq"] = int(cur.get("seq", 0)) + 1
        _state[match_id] = cur
    return cur


def clear(match_id: str) -> None:
    _state.pop(match_id, None)
