"""Domain events → follower notifications (the notification producers).

A single ``NotificationDispatcher`` bundles the repos each producer needs and keeps
per-instance idempotency, so wiring a producer into a hot path (record_ball) is cheap
and never double-fires. A producer must NEVER break scoring — every fan-out is wrapped
so an error is swallowed (and, for the once-only ones, the id is un-marked to retry).

Catalog (P4):
  • in-play player milestones — a batter reaching 50/100/150/200, a bowler taking a 5-for
  • on finish — the match's followers, the tournament's followers (if it's a fixture),
    and the match awards (MoM / best batter / best bowler): persisted + each winner notified
"""

from __future__ import annotations

import html

BAT_MILESTONES = (200, 150, 100, 50)     # checked high→low; the highest newly-crossed fires
BAT_LABELS = {50: "Fifty!", 100: "Century!", 150: "150 up!", 200: "Double century!"}
AWARD_LABELS = {"mom": "Man of the Match", "best_bat": "Best batter", "best_bowl": "Best bowler"}


class NotificationDispatcher:
    def __init__(self, social, *, awards=None, roster=None, match_players=None, tournaments=None) -> None:
        self.social = social
        self.awards = awards                 # AwardRepository (persist match awards)
        self.roster = roster                 # RosterRepository (player_id → user_id)
        self.match_players = match_players    # MatchPlayerRepository (award name → player_id)
        self.tournaments = tournaments        # TournamentRepository (match → fixture → tournament)
        self._finished: set[str] = set()      # match ids whose 'finished' fan-out already ran
        self._milestones: set[str] = set()    # "{match}:{bat|bowl}:{player}:{n}" already fired

    # ------------------------------------------------------------------ #
    def on_match_state(self, state) -> None:
        """Call after each ball. Checks in-play milestones every ball, and fans out the
        finish/awards exactly once when the match is decided."""
        try:
            self._check_milestones(state)
        except Exception:  # a milestone must never break scoring
            pass
        if getattr(state, "result", None) and state.id not in self._finished:
            self._finished.add(state.id)
            try:
                self._on_finish(state)
            except Exception:
                self._finished.discard(state.id)  # let a later ball retry

    # ----- helpers -----
    def _user_for(self, player_id: "str | None") -> "str | None":
        if not player_id or self.roster is None:
            return None
        p = self.roster.get_player(str(player_id))
        return getattr(p, "user_id", None) if p else None

    def _tournament_for(self, match_id: str) -> "str | None":
        if self.tournaments is None:
            return None
        fx = self.tournaments.fixture_for_match(str(match_id))
        return fx.tournament_id if fx else None

    def _name_id_map(self, match_id: str) -> dict:
        if self.match_players is None:
            return {}
        return {lk.name: lk.player_id for lk in self.match_players.for_match(str(match_id))}

    # ----- in-play milestones -----
    def _check_milestones(self, state) -> None:
        mid = state.id
        for inn in getattr(state, "innings", None) or []:
            for b in getattr(inn, "batters", None) or []:
                pid = getattr(b, "player_id", None)
                if not pid:
                    continue                     # casual player — nothing to follow / notify
                for thresh in BAT_MILESTONES:
                    if b.runs >= thresh:
                        if self._mark(f"{mid}:bat:{pid}:{thresh}"):
                            self._fire_milestone(mid, pid, b.name, "bat", thresh,
                                                 f"{b.runs} ({b.balls})")
                        break                    # highest crossed handled this ball
            for w in getattr(inn, "bowlers", None) or []:
                pid = getattr(w, "player_id", None)
                if pid and w.wickets >= 5 and self._mark(f"{mid}:bowl:{pid}:5"):
                    self._fire_milestone(mid, pid, w.name, "bowl", 5, f"{w.wickets}/{w.runs}")

    def _mark(self, key: str) -> bool:
        """Record a fired milestone; return True only the first time (idempotent)."""
        if key in self._milestones:
            return False
        self._milestones.add(key)
        return True

    def _fire_milestone(self, mid, pid, name, kind, thresh, detail) -> None:
        link = f"#/match/{mid}"
        uid = self._user_for(pid)
        if kind == "bat":
            title = BAT_LABELS.get(thresh, f"{thresh}!")
            followers_text = f"{name} reached {thresh} — {detail}"
            you_text = f"You reached {thresh} — {detail}"
            group = f"milestone:bat:{pid}"       # a batter's 50→100→150 coalesce for a follower
        else:
            title = "Five-wicket haul!"
            followers_text = f"{name} took a 5-for — {detail}"
            you_text = f"You took a 5-for — {detail}"
            group = f"milestone:bowl:{pid}"
        # followers of this player (their "player" feed); don't double-notify the player
        self.social.notify_followers("player", pid, category="player", kind="player",
                                     title=title, text=followers_text, link=link,
                                     exclude=uid, group=group)
        if uid:  # the player themselves, as an achievement
            self.social.notify_user(uid, category="achievement", kind="achievement",
                                    title=title, text=you_text, link=link)

    # ----- on finish: match + tournament + awards -----
    def _on_finish(self, state) -> None:
        mid, result = state.id, state.result
        link = f"#/match/{mid}"
        # 1) the match's own followers (the original P1 behaviour)
        self.social.notify_followers("match", mid, category="match", kind="match",
                                     title="Match finished", text=result, link=link,
                                     data={"action": "scorecard", "match_id": mid})
        # 2) the tournament's followers, if this match is a tournament fixture
        tid = self._tournament_for(mid)
        if tid:
            self.social.notify_followers("tournament", tid, category="tournament", kind="tournament",
                                         title="Tournament result", text=result, link=link)
        # 3) awards — persist + notify each winner
        self._process_awards(state)

    def _process_awards(self, state) -> None:
        aw = getattr(state, "awards", None)
        if not aw or self.awards is None:
            return
        name_id = self._name_id_map(state.id)
        for atype, entry in (("mom", aw.man_of_the_match),
                             ("best_bat", aw.best_batter),
                             ("best_bowl", aw.best_bowler)):
            if not entry:
                continue
            label = AWARD_LABELS[atype]
            detail = html.unescape(entry.line or "")
            pid = name_id.get(entry.name)             # may be None (casual / name collision)
            self.awards.add_award(state.id, atype, pid or entry.name, entry.name, detail)
            if not pid:
                continue                              # no player entity to follow / notify
            uid = self._user_for(pid)
            self.social.notify_followers("player", pid, category="achievement", kind="achievement",
                                         title=label, text=f"{entry.name} — {detail}",
                                         link=f"#/match/{state.id}", exclude=uid)
            if uid:
                self.social.notify_user(uid, category="achievement", kind="achievement",
                                        title=label, text=f"You won {label} — {detail}",
                                        link=f"#/match/{state.id}")
