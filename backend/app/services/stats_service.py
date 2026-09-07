"""Stats — career, fielding, form, leaderboards, team record.

All aggregated on demand off the event log by replaying matches. Player stats
replay one player's matches; leaderboards replay every match once and fold each
linked player's cards into per-player accumulators (O(matches), not O(players ×
matches)). Materialised aggregates are a later optimisation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.domain import zones
from app.domain.enums import DismissalType, ExtraType
from app.repositories.match_player_repository import MatchPlayerLink, MatchPlayerRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.roster_repository import RosterRepository
from app.schemas.roster import PlayerDTO
from app.schemas.stats import (
    BattingInsights,
    BattingStats,
    BattingVsType,
    BowlingInsights,
    BowlingStats,
    CareerBucket,
    CareerMatch,
    CompareDTO,
    FieldingStats,
    FormatSplit,
    FormEntry,
    LeaderboardEntry,
    Leaderboards,
    PlayerHistoryDTO,
    PlayerSplitsDTO,
    PlayerStatsDTO,
    TeamStatsDTO,
)

_CATCH_TYPES = {
    DismissalType.CAUGHT,
    DismissalType.CAUGHT_BEHIND,
    DismissalType.CAUGHT_AND_BOWLED,
}


class _Bat:
    def __init__(self) -> None:
        self.matches: set[str] = set()
        self.innings = self.runs = self.balls = self.fours = self.sixes = 0
        self.not_outs = self.highest = self.fifties = self.hundreds = 0

    def add(self, c, match_id: str) -> None:
        self.matches.add(match_id)
        self.innings += 1
        self.runs += c.runs
        self.balls += c.balls
        self.fours += c.fours
        self.sixes += c.sixes
        if not c.out:
            self.not_outs += 1
        self.highest = max(self.highest, c.runs)
        if c.runs >= 100:
            self.hundreds += 1
        elif c.runs >= 50:
            self.fifties += 1

    def dismissals(self) -> int:
        return self.innings - self.not_outs

    def avg(self) -> Optional[float]:
        d = self.dismissals()
        return round(self.runs / d, 2) if d > 0 else None

    def sr(self) -> float:
        return round(100 * self.runs / self.balls, 2) if self.balls else 0.0

    def to_dto(self) -> BattingStats:
        return BattingStats(
            matches=len(self.matches), innings=self.innings, not_outs=self.not_outs,
            runs=self.runs, balls=self.balls, highest=self.highest, average=self.avg(),
            strike_rate=self.sr(), fours=self.fours, sixes=self.sixes,
            fifties=self.fifties, hundreds=self.hundreds,
        )


class _Bowl:
    def __init__(self) -> None:
        self.matches: set[str] = set()
        self.innings = self.balls = self.runs = self.wickets = self.maidens = 0
        self.best_w = -1
        self.best_r = 0

    def add(self, c, match_id: str) -> None:
        self.matches.add(match_id)
        self.innings += 1
        self.balls += c.legal_balls
        self.runs += c.runs
        self.wickets += c.wickets
        self.maidens += c.maidens
        if c.wickets > self.best_w or (c.wickets == self.best_w and c.runs < self.best_r):
            self.best_w, self.best_r = c.wickets, c.runs

    def overs_str(self) -> str:
        return f"{self.balls // 6}.{self.balls % 6}"

    def econ(self) -> float:
        return round(self.runs / (self.balls / 6), 2) if self.balls else 0.0

    def avg(self) -> Optional[float]:
        return round(self.runs / self.wickets, 2) if self.wickets else None

    def to_dto(self) -> BowlingStats:
        return BowlingStats(
            matches=len(self.matches), innings=self.innings, balls=self.balls,
            overs=self.overs_str(), maidens=self.maidens, runs=self.runs, wickets=self.wickets,
            average=self.avg(), economy=self.econ(),
            strike_rate=round(self.balls / self.wickets, 2) if self.wickets else None,
            best=f"{self.best_w}/{self.best_r}" if self.best_w >= 0 else "-",
        )


def _fmt_bat(card) -> Optional[str]:
    if card is None:
        return None
    return f"{card.runs}{'' if card.out else '*'} ({card.balls})"


def _fmt_bowl(card) -> Optional[str]:
    if card is None:
        return None
    return f"{card.wickets}/{card.runs} ({card.overs_str})"


def _mid_int(mid: str) -> int:
    return int(mid) if mid.isdigit() else 0


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalise to tz-aware UTC so naive/aware comparisons never raise."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# Free-text bowling styles ("Right-arm fast", "Left-arm orthodox", …) → pace/spin.
# Spin is checked first so "off-spin"/"leg-spin"/"orthodox" win over any pace word.
_SPIN_HINTS = ("spin", "orthodox", "break", "googly", "chinaman", "tweak", "slow")
_PACE_HINTS = ("fast", "medium", "pace", "seam", "quick", "swing")


def classify_bowling(style: Optional[str]) -> Optional[str]:
    """'pace' | 'spin' | None (unknown / unrecorded) for a bowling-style string."""
    if not style:
        return None
    s = style.lower()
    if any(h in s for h in _SPIN_HINTS):
        return "spin"
    if any(h in s for h in _PACE_HINTS):
        return "pace"
    return None


def _format_bucket(rules) -> tuple[str, str]:
    """A match's format bucket from its overs-per-innings (key, label)."""
    ov = getattr(rules, "overs_per_innings", 20) or 20
    if ov <= 6:
        return "box", "Box/Gully"
    if ov <= 10:
        return "t10", "T10"
    if ov <= 20:
        return "t20", "T20"
    if ov <= 50:
        return "odi", "ODI"
    return "multi", "Multi-day"


def _ball_bucket(rules) -> tuple[str, str]:
    """A match's ball-type bucket (key, label) — leather / tennis / other."""
    bt = getattr(rules, "ball_type", "leather")
    val = getattr(bt, "value", bt)  # BallType enum or plain string
    return str(val), str(val).capitalize()


class _VsBat:
    """A batter's tally against one bowling type (pace or spin)."""

    def __init__(self) -> None:
        self.balls = self.runs = self.dots = self.fours = self.sixes = self.dismissals = 0

    def face(self, runs_off_bat: int) -> None:
        self.balls += 1
        self.runs += runs_off_bat
        if runs_off_bat == 0:
            self.dots += 1
        elif runs_off_bat == 4:
            self.fours += 1
        elif runs_off_bat == 6:
            self.sixes += 1

    def to_dto(self, label: str) -> BattingVsType:
        return BattingVsType(
            label=label, balls=self.balls, runs=self.runs, dot_balls=self.dots,
            dot_pct=round(100 * self.dots / self.balls, 1) if self.balls else 0.0,
            fours=self.fours, sixes=self.sixes,
            strike_rate=round(100 * self.runs / self.balls, 2) if self.balls else 0.0,
            dismissals=self.dismissals,
            average=round(self.runs / self.dismissals, 2) if self.dismissals else None,
        )


class StatsService:
    def __init__(
        self,
        match_repo: MatchRepository,
        match_player_repo: MatchPlayerRepository,
        roster_repo: RosterRepository,
        fielding_repo=None,  # optional: dropped catches / runs saved log
    ) -> None:
        self.match_repo = match_repo
        self.mp = match_player_repo
        self.roster = roster_repo
        self.fielding = fielding_repo
        # memoised aggregates, keyed by a cheap match-data version. Recompute only
        # after a mutation (a new ball / undo / match create/delete/complete) instead
        # of replaying matches on every read.
        self._cache: dict = {}
        self._leaderboard_computes = 0  # instrumentation (tests assert caching works)

    def _data_version(self):
        fn = getattr(self.match_repo, "data_version", None)
        return fn() if callable(fn) else None  # no version → no caching (always fresh)

    def _memo(self, key, compute):
        version = self._data_version()
        if version is None:
            return compute()
        hit = self._cache.get(key)
        if hit is not None and hit[0] == version:
            return hit[1]
        value = compute()
        self._cache[key] = (version, value)
        return value

    @staticmethod
    def _innings(match):
        yield match.innings1
        if match.innings2 is not None:
            yield match.innings2

    def _contrib(self, match, link: MatchPlayerLink):
        """A player's (batting card, bowling card, fielding counts, teams label) in a match."""
        team_name = match.team_a if link.side == "a" else match.team_b
        teams = f"{match.team_a} v {match.team_b}"
        bat_card = bowl_card = None
        catches = run_outs = stumpings = 0
        for inn in self._innings(match):
            sc = inn.scorecard()
            if sc.batting_team == team_name:
                bat_card = next((b for b in sc.batters if b.name == link.name and b.has_batted), None)
            else:
                bowl_card = next((w for w in sc.bowlers if w.name == link.name), None)
                for b in sc.batters:  # opponents this player helped dismiss
                    if b.out and b.fielder == link.name:
                        if b.how_out in _CATCH_TYPES:
                            catches += 1
                        elif b.how_out is DismissalType.RUN_OUT:
                            run_outs += 1
                        elif b.how_out is DismissalType.STUMPED:
                            stumpings += 1
        return bat_card, bowl_card, (catches, run_outs, stumpings), teams

    # ----- per-player -----
    def aggregate(self, player_id: str):
        return self._memo(("agg", str(player_id)), lambda: self._compute_aggregate(player_id))

    def _compute_aggregate(self, player_id: str):
        bat, bowl = _Bat(), _Bowl()
        c = r = st = drops = saved = 0
        per_match = []
        for link in self.mp.for_player(player_id):
            match = self.match_repo.get(link.match_id)
            if match is None:
                continue
            bat_card, bowl_card, (cc, rr, ss), teams = self._contrib(match, link)
            if bat_card is not None:
                bat.add(bat_card, link.match_id)
            if bowl_card is not None:
                bowl.add(bowl_card, link.match_id)
            c += cc
            r += rr
            st += ss
            # drops / runs saved come from the (non-delivery) fielding-event log,
            # credited to the fielder's scoring name in that match
            if self.fielding is not None:
                for e in self.fielding.for_match(link.match_id):
                    if e.fielder != link.name:
                        continue
                    if e.kind == "drop":
                        drops += 1
                    elif e.kind == "save":
                        saved += e.runs
            per_match.append((_mid_int(link.match_id), link.match_id, teams, bat_card, bowl_card))

        per_match.sort(key=lambda t: t[0], reverse=True)
        recent = [
            FormEntry(match_id=mid, teams=teams, bat=_fmt_bat(bc), bowl=_fmt_bowl(wc))
            for _, mid, teams, bc, wc in per_match[:5]
        ]
        fielding = FieldingStats(catches=c, run_outs=r, stumpings=st, drops=drops, runs_saved=saved)
        return bat.to_dto(), bowl.to_dto(), fielding, recent

    # ----- leaderboards (the O(all matches) path — cached per data version) -----
    def leaderboards(
        self,
        min_innings: int = 1,
        limit: int = 10,
        since: Optional[datetime] = None,
        location: Optional[str] = None,
    ) -> Leaderboards:
        key = ("lb", min_innings, limit, since, (location or "").strip().lower())
        return self._memo(key, lambda: self._compute_leaderboards(min_innings, limit, since, location))

    def _compute_leaderboards(
        self,
        min_innings: int = 1,
        limit: int = 10,
        since: Optional[datetime] = None,
        location: Optional[str] = None,
    ) -> Leaderboards:
        self._leaderboard_computes += 1
        names = {p.id: p.name for p in self.roster.list_players()}
        team_loc = {t.id: (t.location or "").strip() for t in self.roster.list_teams()}
        all_locations = sorted({v for v in team_loc.values() if v})
        loc_q = (location or "").strip().lower()
        since = _aware(since)

        accs: dict[str, dict] = {}
        for summary in self.match_repo.summaries():
            if since is not None:  # time window — cheap check before any replay
                ca = _aware(summary.created_at)
                if ca is None or ca < since:
                    continue
            links = self.mp.for_match(summary.id)
            if loc_q:  # geo — keep matches where a participating team is from there
                here = (team_loc.get(lk.team_id, "") for lk in links)
                if not any(loc_q in place.lower() for place in here if place):
                    continue
            match = self.match_repo.get(summary.id)
            if match is None:
                continue
            for link in links:
                a = accs.setdefault(link.player_id, {"bat": _Bat(), "bowl": _Bowl(), "c": 0, "ro": 0, "st": 0})
                bat_card, bowl_card, (cc, rr, ss), _ = self._contrib(match, link)
                if bat_card is not None:
                    a["bat"].add(bat_card, summary.id)
                if bowl_card is not None:
                    a["bowl"].add(bowl_card, summary.id)
                a["c"] += cc
                a["ro"] += rr
                a["st"] += ss

        def mvp(a):  # weighted all-round impact
            return a["bat"].runs + a["bowl"].wickets * 20 + a["c"] * 10 + a["st"] * 10 + a["ro"] * 8

        def board(value_fn, detail_fn, reverse, predicate, sort_key=None):
            rows = [(pid, a) for pid, a in accs.items()
                    if pid in names and predicate(a) and value_fn(a) is not None]
            rows.sort(key=sort_key or (lambda row: value_fn(row[1])), reverse=reverse)
            return [
                LeaderboardEntry(player_id=pid, name=names[pid],
                                 value=round(float(value_fn(a)), 2), detail=detail_fn(a))
                for pid, a in rows[:limit]
            ]

        bat, bowl = (lambda a: a["bat"]), (lambda a: a["bowl"])
        result = Leaderboards(
            min_innings=min_innings,
            most_runs=board(lambda a: bat(a).runs, lambda a: f"{bat(a).innings} inns", True, lambda a: bat(a).runs > 0),
            best_average=board(lambda a: bat(a).avg(), lambda a: f"{bat(a).runs} runs", True, lambda a: bat(a).innings >= min_innings and bat(a).dismissals() > 0),
            best_strike_rate=board(lambda a: bat(a).sr(), lambda a: f"{bat(a).runs} ({bat(a).balls})", True, lambda a: bat(a).innings >= min_innings and bat(a).balls > 0),
            most_sixes=board(lambda a: bat(a).sixes, lambda a: f"{bat(a).innings} inns", True, lambda a: bat(a).sixes > 0),
            most_fours=board(lambda a: bat(a).fours, lambda a: f"{bat(a).innings} inns", True, lambda a: bat(a).fours > 0),
            highest_score=board(lambda a: bat(a).highest, lambda a: f"{len(bat(a).matches)} mat", True, lambda a: bat(a).highest > 0),
            most_wickets=board(lambda a: bowl(a).wickets, lambda a: bowl(a).overs_str() + " ov", True, lambda a: bowl(a).wickets > 0),
            best_economy=board(lambda a: bowl(a).econ(), lambda a: bowl(a).overs_str() + " ov", False, lambda a: bowl(a).innings >= min_innings and bowl(a).balls > 0),
            best_bowling_average=board(lambda a: bowl(a).avg(), lambda a: f"{bowl(a).wickets} wkts", False, lambda a: bowl(a).innings >= min_innings and bowl(a).wickets > 0),
            best_bowling=board(lambda a: bowl(a).best_w, lambda a: f"{bowl(a).best_w}/{bowl(a).best_r}", True, lambda a: bowl(a).best_w > 0, sort_key=lambda row: (row[1]["bowl"].best_w, -row[1]["bowl"].best_r)),
            most_catches=board(lambda a: a["c"], lambda a: "", True, lambda a: a["c"] > 0),
            mvp=board(mvp, lambda a: f"{bat(a).runs} runs · {bowl(a).wickets} wkts", True, lambda a: mvp(a) > 0),
        )
        result.location = location or None
        result.locations = all_locations
        return result

    # ----- player insights (CricInsights-style breakdowns) -----
    def insights(self, player_id: str):
        balls = dots = fours = sixes = running = bb = bdots = 0
        dismissals: dict = {}
        wkts_by_type: dict = {}
        zone_runs: dict = {}
        off_runs = leg_runs = shots_tracked = pitches = 0
        len_balls: dict = {}
        len_runs: dict = {}
        for link in self.mp.for_player(player_id):
            match = self.match_repo.get(link.match_id)
            if match is None:
                continue
            team_name = match.team_a if link.side == "a" else match.team_b
            for inn in self._innings(match):
                sc = inn.scorecard()
                if sc.batting_team == team_name:
                    card = next((b for b in sc.batters if b.name == link.name and b.has_batted), None)
                    if card is not None and card.out and card.how_out is not None:
                        dismissals[card.how_out.value] = dismissals.get(card.how_out.value, 0) + 1
                    for e in inn.events:
                        if e.striker == link.name and e.extra is not ExtraType.WIDE:
                            balls += 1
                            rob = e.runs_off_bat if e.extra in (None, ExtraType.NO_BALL) else 0
                            if rob == 0:
                                dots += 1
                            elif rob == 4:
                                fours += 1
                            elif rob == 6:
                                sixes += 1
                            else:
                                running += rob
                            if e.wagon_x is not None and e.wagon_y is not None:
                                z = zones.wagon_zone(e.wagon_x, e.wagon_y)
                                zone_runs[z] = zone_runs.get(z, 0) + rob
                                if zones.wagon_side(e.wagon_x) == "off":
                                    off_runs += rob
                                else:
                                    leg_runs += rob
                                shots_tracked += 1
                else:
                    for e in inn.events:
                        if e.bowler == link.name and e.extra not in (ExtraType.WIDE, ExtraType.NO_BALL):
                            bb += 1
                            r = e.runs_off_bat + (e.extra_runs if e.extra in (ExtraType.BYE, ExtraType.LEG_BYE) else 0)
                            if r == 0:
                                bdots += 1
                            if e.pitch_y is not None:
                                band = zones.pitch_length(e.pitch_y)
                                len_balls[band] = len_balls.get(band, 0) + 1
                                len_runs[band] = len_runs.get(band, 0) + r
                                pitches += 1
                    for b in sc.batters:
                        if b.out and b.out_bowler == link.name and b.how_out is not None:
                            wkts_by_type[b.how_out.value] = wkts_by_type.get(b.how_out.value, 0) + 1

        boundary_balls = fours + sixes
        boundary_runs = fours * 4 + sixes * 6
        off_bat = boundary_runs + running
        side_total = off_runs + leg_runs
        top_zone = max(zone_runs, key=zone_runs.get) if zone_runs else ""
        econ_by_length = {k: round(6.0 * len_runs[k] / len_balls[k], 2) for k in len_balls}
        batting = BattingInsights(
            balls_faced=balls, dot_balls=dots,
            dot_pct=round(100 * dots / balls, 1) if balls else 0.0,
            fours=fours, sixes=sixes,
            boundary_pct=round(100 * boundary_balls / balls, 1) if balls else 0.0,
            boundary_runs=boundary_runs, running_runs=running,
            boundary_runs_pct=round(100 * boundary_runs / off_bat, 1) if off_bat else 0.0,
            dismissals=dismissals,
            six_pct=round(100 * sixes / balls, 1) if balls else 0.0,
            shots_tracked=shots_tracked,
            off_side_pct=round(100 * off_runs / side_total, 1) if side_total else 0.0,
            leg_side_pct=round(100 * leg_runs / side_total, 1) if side_total else 0.0,
            top_zone=top_zone, runs_by_zone=zone_runs,
        )
        bowling = BowlingInsights(
            balls_bowled=bb, dot_balls=bdots,
            dot_pct=round(100 * bdots / bb, 1) if bb else 0.0,
            wickets_by_type=wkts_by_type,
            pitches_tracked=pitches, length_dist=len_balls, econ_by_length=econ_by_length,
        )
        return batting, bowling

    # ----- per-format / per-ball-type splits + pace/spin matchups -----
    def splits(self, player_id: str) -> Optional[PlayerSplitsDTO]:
        rec = self.roster.get_player(player_id)
        if rec is None:
            return None

        by_format: dict[str, dict] = {}
        by_ball: dict[str, dict] = {}
        pace, spin = _VsBat(), _VsBat()
        # one lookup of every roster player's style, reused across the matches
        style_of = {p.id: p.bowling_style for p in self.roster.list_players()}

        def bucket(store: dict, key: str, label: str) -> dict:
            return store.setdefault(
                key, {"label": label, "bat": _Bat(), "bowl": _Bowl(), "matches": set()}
            )

        for link in self.mp.for_player(player_id):
            match = self.match_repo.get(link.match_id)
            if match is None:
                continue
            rules = match.rules
            bat_card, bowl_card, _fld, _teams = self._contrib(match, link)

            # fold this match's cards into both the format and the ball-type bucket
            for store, (key, label) in (
                (by_format, _format_bucket(rules)),
                (by_ball, _ball_bucket(rules)),
            ):
                acc = bucket(store, key, label)
                if bat_card is not None:
                    acc["bat"].add(bat_card, link.match_id)
                    acc["matches"].add(link.match_id)
                if bowl_card is not None:
                    acc["bowl"].add(bowl_card, link.match_id)
                    acc["matches"].add(link.match_id)

            # vs pace/spin — map each scoring name in this match to a bowling type
            type_of_name = {
                l2.name: classify_bowling(style_of.get(l2.player_id))
                for l2 in self.mp.for_match(link.match_id)
            }
            team_name = match.team_a if link.side == "a" else match.team_b
            for inn in self._innings(match):
                sc = inn.scorecard()
                if sc.batting_team != team_name:
                    continue  # only deliveries our player faced
                for e in inn.events:
                    if e.striker == link.name and e.extra is not ExtraType.WIDE:
                        cat = type_of_name.get(e.bowler)
                        tgt = pace if cat == "pace" else (spin if cat == "spin" else None)
                        if tgt is not None:
                            rob = e.runs_off_bat if e.extra in (None, ExtraType.NO_BALL) else 0
                            tgt.face(rob)
                card = next((b for b in sc.batters if b.name == link.name and b.has_batted), None)
                if card is not None and card.out and card.out_bowler is not None:
                    cat = type_of_name.get(card.out_bowler)
                    if cat == "pace":
                        pace.dismissals += 1
                    elif cat == "spin":
                        spin.dismissals += 1

        def to_splits(store: dict) -> list[FormatSplit]:
            rows = [
                FormatSplit(
                    key=key, label=a["label"], matches=len(a["matches"]),
                    batting=a["bat"].to_dto(), bowling=a["bowl"].to_dto(),
                )
                for key, a in store.items() if a["matches"]
            ]
            rows.sort(key=lambda s: s.matches, reverse=True)
            return rows

        player = PlayerDTO(
            id=rec.id, name=rec.name, phone=rec.phone,
            batting_style=rec.batting_style, bowling_style=rec.bowling_style,
        )
        return PlayerSplitsDTO(
            player=player,
            by_format=to_splits(by_format),
            by_ball=to_splits(by_ball),
            vs_pace=pace.to_dto("vs Pace"),
            vs_spin=spin.to_dto("vs Spin"),
            has_matchup=(pace.balls + spin.balls) > 0,
        )

    def player_stats_dto(self, player_id: str) -> Optional[PlayerStatsDTO]:
        rec = self.roster.get_player(player_id)
        if rec is None:
            return None
        bat, bowl, field, recent = self.aggregate(player_id)
        player = PlayerDTO(
            id=rec.id, name=rec.name, phone=rec.phone,
            batting_style=rec.batting_style, bowling_style=rec.bowling_style,
        )
        return PlayerStatsDTO(player=player, batting=bat, bowling=bowl, fielding=field, recent=recent)

    # ----- full career history (cached per data version) -----
    def history(self, player_id: str) -> Optional[PlayerHistoryDTO]:
        """Every match this player has played, grouped by tournament, year and side."""
        return self._memo(("hist", str(player_id)), lambda: self._compute_history(player_id))

    def _match_dates(self) -> dict:
        """match_id -> creation time, from the one call that knows it."""
        return {row.id: row.created_at for row in self.match_repo.summaries()}

    @staticmethod
    def _outcome(match, team_name: str) -> str:
        """Did this player's side win, read from the engine's result sentence.

        The engine writes the winner's name into the result ("Aces won by 12
        runs"), so the side is read back out of it rather than recomputed —
        there is no second source of truth to drift from.
        """
        result = match.result
        if not result:
            return "in_progress"
        low = result.lower()
        if "no result" in low or "abandoned" in low:
            return "no_result"
        if "tied" in low:
            return "tied"
        if result.startswith(team_name):
            return "won"
        return "lost"

    def _compute_history(self, player_id: str) -> Optional[PlayerHistoryDTO]:
        rec = self.roster.get_player(player_id)
        if rec is None:
            return None

        dates = self._match_dates()
        rows: list[tuple[int, CareerMatch]] = []
        # One accumulator set per grouping; a match is folded into each of them.
        groups: dict[str, dict] = {"tournament": {}, "year": {}, "team": {}}

        def bucket(kind: str, key: str, label: str) -> dict:
            store = groups[kind]
            if key not in store:
                store[key] = {
                    "label": label, "matches": 0, "won": 0, "lost": 0,
                    "bat": _Bat(), "bowl": _Bowl(),
                    "c": 0, "r": 0, "st": 0, "drops": 0, "saved": 0,
                }
            return store[key]

        career_bat, career_bowl = _Bat(), _Bowl()
        cc_tot = rr_tot = ss_tot = drops_tot = saved_tot = 0
        won = lost = tied = no_result = 0

        for link in self.mp.for_player(player_id):
            match = self.match_repo.get(link.match_id)
            if match is None:
                continue

            team = match.team_a if link.side == "a" else match.team_b
            opponent = match.team_b if link.side == "a" else match.team_a
            bat_card, bowl_card, (cc, rr, ss), _teams = self._contrib(match, link)
            meta = self.match_repo.get_meta(link.match_id) or {}
            outcome = self._outcome(match, team)

            drops = saved = 0
            if self.fielding is not None:
                for e in self.fielding.for_match(link.match_id):
                    if e.fielder != link.name:
                        continue
                    if e.kind == "drop":
                        drops += 1
                    elif e.kind == "save":
                        saved += e.runs

            when = dates.get(link.match_id)
            row = CareerMatch(
                match_id=link.match_id,
                played_on=when.isoformat() if when else None,
                format=match.rules.name or "",
                team=team,
                opponent=opponent,
                tournament=meta.get("tournament") or None,
                venue=meta.get("venue") or None,
                match_no=meta.get("match_no") or None,
                result=match.result,
                outcome=outcome,
                catches=cc,
                run_outs=rr,
                stumpings=ss,
            )
            if bat_card is not None:
                row.batted = True
                row.runs = bat_card.runs
                row.balls = bat_card.balls
                row.fours = bat_card.fours
                row.sixes = bat_card.sixes
                row.strike_rate = bat_card.strike_rate
                row.not_out = not bat_card.out
                row.how_out = bat_card.how_out.value if bat_card.how_out else None
                row.dismissal_text = bat_card.dismissal_text
                row.bat_line = _fmt_bat(bat_card)
            if bowl_card is not None:
                row.bowled = True
                row.overs = bowl_card.overs_str
                row.maidens = bowl_card.maidens
                row.runs_conceded = bowl_card.runs
                row.wickets = bowl_card.wickets
                balls = bowl_card.legal_balls
                row.economy = round(6.0 * bowl_card.runs / balls, 2) if balls else 0.0
                row.bowl_line = _fmt_bowl(bowl_card)

            rows.append((_mid_int(link.match_id), row))

            if bat_card is not None:
                career_bat.add(bat_card, link.match_id)
            if bowl_card is not None:
                career_bowl.add(bowl_card, link.match_id)
            cc_tot += cc
            rr_tot += rr
            ss_tot += ss
            drops_tot += drops
            saved_tot += saved
            won += outcome == "won"
            lost += outcome == "lost"
            tied += outcome == "tied"
            no_result += outcome == "no_result"

            targets = [bucket("team", team, team)]
            if row.tournament:
                targets.append(bucket("tournament", row.tournament, row.tournament))
            if when:
                year = str(when.year)
                targets.append(bucket("year", year, year))
            for b in targets:
                b["matches"] += 1
                b["won"] += outcome == "won"
                b["lost"] += outcome == "lost"
                if bat_card is not None:
                    b["bat"].add(bat_card, link.match_id)
                if bowl_card is not None:
                    b["bowl"].add(bowl_card, link.match_id)
                b["c"] += cc
                b["r"] += rr
                b["st"] += ss
                b["drops"] += drops
                b["saved"] += saved

        rows.sort(key=lambda t: t[0], reverse=True)
        matches = [r for _, r in rows]

        def to_buckets(kind: str, newest_first: bool) -> list[CareerBucket]:
            out = [
                CareerBucket(
                    key=key,
                    label=b["label"],
                    matches=b["matches"],
                    won=b["won"],
                    lost=b["lost"],
                    batting=b["bat"].to_dto(),
                    bowling=b["bowl"].to_dto(),
                    fielding=FieldingStats(
                        catches=b["c"], run_outs=b["r"], stumpings=b["st"],
                        drops=b["drops"], runs_saved=b["saved"],
                    ),
                )
                for key, b in groups[kind].items()
            ]
            if newest_first:
                return sorted(out, key=lambda x: x.key, reverse=True)
            # Most-played first reads better than alphabetical on a career page.
            return sorted(out, key=lambda x: (-x.matches, x.label))

        decided = won + lost + tied
        return PlayerHistoryDTO(
            player=PlayerDTO(
                id=rec.id, name=rec.name, phone=rec.phone,
                batting_style=rec.batting_style, bowling_style=rec.bowling_style,
            ),
            debut=matches[-1].played_on if matches else None,
            last_played=matches[0].played_on if matches else None,
            matches_played=len(matches),
            won=won, lost=lost, tied=tied, no_result=no_result,
            win_pct=round(100.0 * won / decided, 1) if decided else 0.0,
            batting=career_bat.to_dto(),
            bowling=career_bowl.to_dto(),
            fielding=FieldingStats(
                catches=cc_tot, run_outs=rr_tot, stumpings=ss_tot,
                drops=drops_tot, runs_saved=saved_tot,
            ),
            matches=matches,
            by_tournament=to_buckets("tournament", newest_first=False),
            by_year=to_buckets("year", newest_first=True),
            by_team=to_buckets("team", newest_first=False),
        )

    def compare(self, a_id: str, b_id: str) -> Optional[CompareDTO]:
        a = self.player_stats_dto(a_id)
        b = self.player_stats_dto(b_id)
        if a is None or b is None:
            return None
        return CompareDTO(player_a=a, player_b=b)

    # ----- team record (cached per data version) -----
    def team_stats(self, team_id: str) -> Optional[TeamStatsDTO]:
        return self._memo(("team", str(team_id)), lambda: self._compute_team_stats(team_id))

    def _compute_team_stats(self, team_id: str) -> Optional[TeamStatsDTO]:
        team = self.roster.get_team(team_id)
        if team is None:
            return None
        side_by_match: dict[str, str] = {}
        for link in self.mp.for_team(team_id):
            side_by_match[link.match_id] = link.side

        played = won = lost = tied = nr = runs_for = runs_against = 0
        for mid, side in side_by_match.items():
            match = self.match_repo.get(mid)
            if match is None:
                continue
            played += 1
            team_name = match.team_a if side == "a" else match.team_b
            for inn in self._innings(match):
                sc = inn.scorecard()
                if sc.batting_team == team_name:
                    runs_for += sc.runs
                else:
                    runs_against += sc.runs
            winner = match.winner_team
            if winner is None:
                nr += 1
            elif winner == "tie":
                tied += 1
            elif winner == team_name:
                won += 1
            else:
                lost += 1

        decided = won + lost + tied
        return TeamStatsDTO(
            team_id=team_id, name=team.name, played=played, won=won, lost=lost,
            tied=tied, no_result=nr,
            win_pct=round(100 * won / decided, 1) if decided else 0.0,
            runs_for=runs_for, runs_against=runs_against,
        )
