"""MatchService — the one place that turns API requests into engine calls and
engine projections into DTOs. Both the JSON API and the HTML demo use it, so the
two never drift."""

from __future__ import annotations

import math
import time

from app.core.streaming import stream_info
from app.domain import presets, zones
from app.domain.engine import InningsEngine, MatchEngine, ScoringError
from app.domain.enums import DismissalType
from app.domain.events import BallEvent
from app.domain.rules import MatchRules
from typing import Optional

from app.repositories.match_player_repository import MatchPlayerLink, MatchPlayerRepository
from app.repositories.match_repository import MatchRepository
from app.schemas.match import (
    BatterDTO,
    DlsSuggestion,
    BowlerDTO,
    CreateMatchRequest,
    FallOfWicketDTO,
    PartnershipDTO,
    InningsDTO,
    MatchClipDTO,
    MatchHighlightsDTO,
    MatchMeta,
    MatchStateDTO,
    MatchSummaryDTO,
    PitchMarkDTO,
    WagonShotDTO,
)
from app.schemas.presets import PresetSummary
from app.schemas.scoring import BallAction, BallRequest


class MatchNotFound(Exception):
    """No match exists for the given id."""


class InvalidMatchSetup(Exception):
    """The create-match request is not coherent."""


class MatchService:
    def __init__(
        self, repo: MatchRepository, match_player_repo: Optional[MatchPlayerRepository] = None
    ) -> None:
        self.repo = repo
        self.match_players = match_player_repo

    # ----- presets -----
    def list_presets(self) -> list[PresetSummary]:
        out: list[PresetSummary] = []
        for pid, factory in presets.PRESETS.items():
            r = factory()
            out.append(
                PresetSummary(
                    id=pid,
                    name=r.name,
                    description=r.description,
                    players_per_side=r.players_per_side,
                    overs_per_innings=r.overs_per_innings,
                    balls_per_over=r.balls_per_over,
                    ball_type=r.ball_type.value,
                    last_man_stands=r.last_man_stands,
                )
            )
        return out

    def get_preset_rules(self, format_id: str) -> MatchRules:
        return presets.get_preset(format_id)  # raises KeyError if unknown

    # ----- matches -----
    def create_match(self, req: CreateMatchRequest) -> MatchStateDTO:
        if req.rules is not None:
            rules = req.rules
        else:
            try:
                rules = presets.get_preset(req.format_id)
            except KeyError as e:
                raise InvalidMatchSetup(f"unknown format '{req.format_id}'") from e

        n = rules.players_per_side
        sa = req.squad_a or [f"{req.team_a} {i + 1}" for i in range(n)]
        sb = req.squad_b or [f"{req.team_b} {i + 1}" for i in range(n)]
        if len(sa) < 2 or len(sb) < 2:
            raise InvalidMatchSetup("each squad needs at least 2 players")

        # When an explicit XI is provided (e.g. picked from a team roster), the
        # match's rules snapshot should reflect the actual squad size.
        if req.squad_a is not None or req.squad_b is not None:
            if len(sa) != len(sb):
                raise InvalidMatchSetup("both squads must have the same number of players")
            rules = rules.model_copy(update={"players_per_side": len(sa)})

        bat_first = req.team_a if req.bat_first == "a" else req.team_b
        match = MatchEngine(rules, req.team_a, req.team_b, sa, sb, bat_first=bat_first)
        match_id = self.repo.add(match)
        self._link_players(match_id, req, sa, sb)
        meta = self._build_meta(req)
        if meta:
            self.repo.set_meta(match_id, meta)
        return self._state(match_id, match)

    @staticmethod
    def _build_meta(req: CreateMatchRequest) -> dict:
        """Collect the display-only setup fields (venue, toss, tournament) captured
        at creation — the toss winner is resolved from a/b to the team name."""
        meta: dict = {}
        if req.venue and req.venue.strip():
            meta["venue"] = req.venue.strip()[:120]
        if req.tournament and req.tournament.strip():
            meta["tournament"] = req.tournament.strip()[:120]
        if req.match_no and req.match_no.strip():
            meta["match_no"] = req.match_no.strip()[:40]
        if req.toss_winner in ("a", "b"):
            meta["toss_winner"] = req.team_a if req.toss_winner == "a" else req.team_b
            if req.toss_decision in ("bat", "bowl"):
                meta["toss_decision"] = req.toss_decision
        return meta

    @staticmethod
    def _meta_dto(m: dict) -> MatchMeta:
        if not m:
            return MatchMeta()
        toss_text = None
        if m.get("toss_winner"):
            verb = {"bat": "chose to bat", "bowl": "chose to bowl"}.get(m.get("toss_decision"))
            toss_text = f"{m['toss_winner']} won the toss" + (f" and {verb}" if verb else "")
        return MatchMeta(
            venue=m.get("venue"), tournament=m.get("tournament"), match_no=m.get("match_no"),
            toss_winner=m.get("toss_winner"), toss_decision=m.get("toss_decision"), toss_text=toss_text,
        )

    def _link_players(self, match_id: str, req: CreateMatchRequest, sa: list[str], sb: list[str]) -> None:
        """Record which real player batted/bowled under which name (for stats)."""
        if self.match_players is None:
            return
        links: list[MatchPlayerLink] = []
        for side, names, ids, team_id in (
            ("a", sa, req.squad_a_ids, req.team_a_id),
            ("b", sb, req.squad_b_ids, req.team_b_id),
        ):
            if not ids:
                continue
            for name, player_id in zip(names, ids):
                links.append(MatchPlayerLink(match_id, str(player_id), name, side, team_id))
        if links:
            self.match_players.link(links)

    def get_engine(self, match_id: str) -> MatchEngine:
        match = self.repo.get(match_id)
        if match is None:
            raise MatchNotFound(match_id)
        return match

    def get_state(self, match_id: str) -> MatchStateDTO:
        return self._state(match_id, self.get_engine(match_id))

    def commentary_feed(self, match_id: str) -> list[dict]:
        """Auto-generated ball-by-ball commentary across all innings."""
        return self.get_engine(match_id).commentary_feed()

    def highlights(self, match_id: str) -> list[dict]:
        """Auto key-moments reel (wickets, boundaries, milestones, result)."""
        return self.get_engine(match_id).highlights()

    def list_summaries(self) -> list[MatchSummaryDTO]:
        return [
            MatchSummaryDTO(
                id=row.id,
                team_a=row.team_a,
                team_b=row.team_b,
                status=row.status,
                result=row.result,
            )
            for row in self.repo.summaries()
        ]

    def record_ball(self, match_id: str, req: BallRequest) -> MatchStateDTO:
        m = self.get_engine(match_id)
        event = self._to_event(req)
        event.ts = time.time()  # wall-clock, for syncing auto highlight clips to a video
        m.current.record(event)  # raises ScoringError (no save on failure)
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def set_bowler(self, match_id: str, bowler: str) -> MatchStateDTO:
        m = self.get_engine(match_id)
        m.current.ensure_bowler_eligible(bowler)  # reject an ineligible pick before staging
        m.current.set_bowler(bowler)
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def undo(self, match_id: str) -> MatchStateDTO:
        m = self.get_engine(match_id)
        m.current.undo()
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def edit_ball(self, match_id: str, index: int, req: BallRequest) -> MatchStateDTO:
        """Correct an earlier delivery in the live innings (re-derives everything)."""
        m = self.get_engine(match_id)
        event = self._to_event(req)
        event.ts = time.time()
        m.current.edit_event(index, event)  # IndexError / ScoringError
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def delete_ball(self, match_id: str, index: int) -> MatchStateDTO:
        m = self.get_engine(match_id)
        m.current.delete_event(index)  # IndexError / ScoringError
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def start_second_innings(self, match_id: str) -> MatchStateDTO:
        m = self.get_engine(match_id)
        m.start_second_innings()  # raises ScoringError if 1st not complete
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def set_revised_target(self, match_id: str, target: int, overs: Optional[int] = None) -> MatchStateDTO:
        """Apply a DLS-style revised target/overs to the chase (rain rules)."""
        m = self.get_engine(match_id)
        m.set_revised_target(target, overs)  # raises ScoringError if DLS off / invalid
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def dls_suggest(self, match_id: str, team2_overs: int, g50: Optional[int] = None) -> DlsSuggestion:
        """Compute a DLS revised target + live par from the match's real innings-1
        total. Team 1's overs = its allotted innings length; team 2's live position
        (overs faced, wickets) feeds the par score."""
        from app.domain import dls

        m = self.get_engine(match_id)
        st = self._state(match_id, m)
        if not st.innings:
            raise InvalidMatchSetup("No innings scored yet.")
        inn1 = st.innings[0]
        s1 = inn1.runs
        team1_overs = inn1.max_overs
        bpo = st.rules.balls_per_over or 6
        faced_overs, wickets = 0.0, 0
        if st.current_innings >= 2 and len(st.innings) >= 2:
            inn2 = st.innings[1]
            faced_overs = dls.overs_from_balls(inn2.legal_balls, bpo)
            wickets = inn2.wickets
        res = dls.chase(
            s1=s1, team1_overs=float(team1_overs), team2_overs=float(team2_overs),
            faced_overs=faced_overs, wickets=wickets,
            g50=(g50 or dls.G50_DEFAULT),
        )
        note = (
            f"Team 1 made {s1} using {res['r1']}% resources; a {team2_overs}-over chase = "
            f"{res['r2']}% → target {res['target']}."
        )
        return DlsSuggestion(note=note, **res)

    # ----- DLS rain interruptions (the scorer only confirms overs) -----
    def interrupt(self, match_id: str, reason: str = "rain", at: Optional[str] = None) -> MatchStateDTO:
        """Flag that play has stopped (rain / bad light / …)."""
        m = self.get_engine(match_id)
        m.interrupt(reason, at)  # raises ScoringError if DLS off / already interrupted
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def resume_interruption(self, match_id: str, overs: int, at: Optional[str] = None) -> MatchStateDTO:
        """Resume with the interrupted innings cut to ``overs`` — the target self-computes."""
        m = self.get_engine(match_id)
        m.resume(overs, at)  # raises ScoringError if invalid
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def cancel_interruption(self, match_id: str) -> MatchStateDTO:
        """Drop a pending interruption (false alarm — play never actually stopped)."""
        m = self.get_engine(match_id)
        m.cancel_interruption()
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def abandon_match(self, match_id: str, reason: str = "rain") -> MatchStateDTO:
        """Call the match off — decided on DLS par if the chase passed the minimum overs."""
        m = self.get_engine(match_id)
        m.abandon(reason)  # raises ScoringError if DLS off
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def declare(self, match_id: str) -> MatchStateDTO:
        """Declare the current innings closed (captain's declaration)."""
        m = self.get_engine(match_id)
        m.declare()  # raises ScoringError if not enabled / already complete / super over
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def super_over(self, match_id: str, bat_first: Optional[str] = None) -> MatchStateDTO:
        """Start a super over on a tie, or begin the reply within the round."""
        m = self.get_engine(match_id)
        m.super_over(bat_first)  # raises ScoringError if not enabled / not required
        self.repo.save(match_id, m)
        return self._state(match_id, m)

    def set_stream(self, match_id: str, url: Optional[str]) -> MatchStateDTO:
        """Attach (or clear, with a blank url) a bring-your-own live-stream link."""
        m = self.get_engine(match_id)  # raises MatchNotFound if missing
        raw = (url or "").strip()
        if not raw:
            self.repo.set_stream_url(match_id, None)
            return self._state(match_id, m)
        info = stream_info(raw)
        if info is None:
            raise InvalidMatchSetup("Enter a valid YouTube, Facebook, or http(s) stream link.")
        self.repo.set_stream_url(match_id, info.url)
        return self._state(match_id, m)

    # ----- highlight clips (bring-your-own links) -----
    @staticmethod
    def _clip_dto(c: dict) -> MatchClipDTO:
        if c.get("source") == "auto":  # a server-cut mp4 played inline (not an embed)
            return MatchClipDTO(id=str(c.get("id")), url=c.get("url"), label=c.get("label"),
                                kind="video", embed_url=None, source="auto")
        info = stream_info(c.get("url"))
        return MatchClipDTO(
            id=str(c.get("id")), url=c.get("url"), label=c.get("label"),
            kind=(info.kind if info else "external"),
            embed_url=(info.embed_url if info else None), source="link",
        )

    def list_clips(self, match_id: str) -> list[MatchClipDTO]:
        self.get_engine(match_id)  # 404 if missing
        return [self._clip_dto(c) for c in self.repo.get_clips(match_id)]

    def scorecard_report(self, match_id: str) -> dict:
        """All data for the premium PDF scorecard: the state + awards + a match-stats
        dashboard, superlatives (most 4s/6s, best stand), and significant ball events.
        (The app doesn't store tournament/venue/date/toss — only who batted first — so
        the report shows what's captured and the template omits the rest.)"""
        m = self.get_engine(match_id)
        state = self._state(match_id, m)
        # engine innings in the SAME order _state builds the DTO list (for dot counts)
        seq = [m.innings1] + ([m.innings2] if m.innings2 is not None else [])
        for so in m.super_overs:
            seq.append(so.first)
            if so.second is not None:
                seq.append(so.second)

        inn_extra: list[dict] = []
        tot = {"runs": 0, "wickets": 0, "fours": 0, "sixes": 0, "dots": 0, "extras": 0, "balls": 0}
        six_leader = {"name": None, "count": 0}
        four_leader = {"name": None, "count": 0}
        best_pnr = None
        for i, dto in enumerate(state.innings):
            eng = seq[i] if i < len(seq) else None
            dots = sum(1 for c in (eng.commentary if eng else []) if c.kind == "dot")
            fours = sum(b.fours for b in dto.batters)
            sixes = sum(b.sixes for b in dto.batters)
            inn_extra.append({"dots": dots, "fours": fours, "sixes": sixes, "boundaries": fours + sixes})
            tot["runs"] += dto.runs; tot["wickets"] += dto.wickets
            tot["fours"] += fours; tot["sixes"] += sixes; tot["dots"] += dots
            tot["extras"] += (dto.extras or {}).get("total", 0); tot["balls"] += dto.legal_balls
            for b in dto.batters:
                if b.sixes > six_leader["count"]:
                    six_leader = {"name": b.name, "count": b.sixes, "team": dto.batting_team}
                if b.fours > four_leader["count"]:
                    four_leader = {"name": b.name, "count": b.fours, "team": dto.batting_team}
            for p in dto.partnerships:
                if best_pnr is None or p.runs > best_pnr["runs"]:
                    best_pnr = {"runs": p.runs, "balls": p.balls, "a": p.batter_a, "b": p.batter_b,
                                "wicket": p.wicket, "team": dto.batting_team}

        stats = {
            "runs": tot["runs"], "wickets": tot["wickets"], "boundaries": tot["fours"] + tot["sixes"],
            "sixes": tot["sixes"], "fours": tot["fours"], "dots": tot["dots"], "extras": tot["extras"],
            "run_rate": round(6.0 * tot["runs"] / tot["balls"], 2) if tot["balls"] else 0.0,
            "best_partnership": best_pnr,
        }
        keep = {"four", "six", "wicket", "fifty", "hundred", "result"}
        highlights = [h for h in m.highlights() if h["kind"] in keep]
        superlatives = {
            "most_sixes": six_leader if six_leader["count"] > 0 else None,
            "most_fours": four_leader if four_leader["count"] > 0 else None,
        }
        impact_tbl = self._impact_table(state)
        top_impact = sorted(impact_tbl.values(), key=lambda s: -s["impact"])[:3]
        side_ids = self._side_team_ids(match_id)
        logo = lambda side: f"/api/v1/teams/{side_ids[side]}/photo" if side_ids.get(side) else None
        return {
            "m": state, "awards": state.awards, "stats": stats, "inn_extra": inn_extra,
            "superlatives": superlatives, "highlights": highlights,
            "bat_first_team": state.team_a if state.bat_first == "a" else state.team_b,
            "mom_impact": self._mom_impact(state), "top_impact": top_impact, "meta": state.meta,
            "logo_a": logo("a"), "logo_b": logo("b"),
        }

    def _side_team_ids(self, match_id: str) -> dict:
        """{'a': team_a_id, 'b': team_b_id} from the match's real-player links, for logos."""
        out: dict[str, str] = {}
        links = self.match_players.for_match(match_id) if self.match_players else []
        for lk in links:
            if lk.team_id and lk.side in ("a", "b"):
                out.setdefault(lk.side, lk.team_id)
        return out

    # ---- broadcast overlay (OBS / vMix) ------------------------------------

    @staticmethod
    def _ball_badge(kind: str, runs: int) -> dict:
        """Map a delivery to a coloured recent-balls badge {token, class}."""
        table = {
            "wicket": ("W", "wkt"),
            "six": ("6", "six"),
            "four": ("4", "four"),
            "dot": ("0", "dot"),
            "wide": ("wd", "extra"),
            "noball": ("nb", "extra"),
        }
        if kind in table:
            t, cls = table[kind]
            return {"t": t, "cls": cls}
        if kind == "bye":
            return {"t": f"{runs}b", "cls": "extra"}
        if kind == "legbye":
            return {"t": f"{runs}lb", "cls": "extra"}
        return {"t": str(runs), "cls": "run"}  # 1/2/3/5 off the bat

    @staticmethod
    def _phase(inn: InningsDTO) -> dict:
        """Which innings phase is live: powerplay / middle / death (for the pills)."""
        if inn.in_powerplay:
            return {"key": "pp", "label": inn.powerplay_label or "Powerplay"}
        mx = inn.max_overs or 0
        death_from = (mx - 5) if mx >= 10 else max(1, int(mx * 0.8))
        if mx and inn.current_over > death_from:
            return {"key": "death", "label": "Death Overs"}
        return {"key": "middle", "label": "Middle Overs"}

    @staticmethod
    def _win_probability(inn: InningsDTO):
        """A lightweight chase-difficulty ESTIMATE (not a trained model) for the 2nd
        innings, 0–100 from the batting side's view. None outside a live chase."""
        if inn.target is None or inn.is_complete:
            return None
        need = inn.required_runs or 0
        balls = inn.balls_remaining or 0
        if need <= 0:
            return 100
        if balls <= 0:
            return 0
        wkts_left = inn.max_wickets - inn.wickets
        if wkts_left <= 0:
            return 0
        req_rate = need / balls * 6.0
        # a side with all wickets can sustain ~high rpo in a limited-overs chase;
        # each wicket lost trims what's sustainable. Logistic around that rate.
        sustainable = 6.0 + 0.55 * wkts_left
        p = 1.0 / (1.0 + math.exp(0.55 * (req_rate - sustainable)))
        return int(round(max(1.0, min(99.0, p * 100.0))))

    def overlay(self, match_id: str) -> dict:
        """Compact, broadcast-overlay payload for /overlay/{id} (OBS/vMix): the live
        scoreboard essentials + current batters, bowler, last-6 balls, partnership,
        phase, ticker and — on the newest ball — what to animate. One fetch drives
        every widget; the page auto-hides whatever is absent. Public."""
        m = self.get_engine(match_id)
        st = self._state(match_id, m)
        inn = st.innings[st.current_innings - 1]

        # Resolve real-player / team links so the overlay can show logos + photos.
        # URLs are emitted unconditionally; the page falls back to a monogram if the
        # image 404s (no photo uploaded) — keeps this decoupled from PhotoService.
        links = self.match_players.for_match(match_id) if self.match_players else []
        name_pid = {lk.name: lk.player_id for lk in links}
        side_team: dict[str, str] = {}
        for lk in links:
            if lk.team_id and lk.side in ("a", "b"):
                side_team.setdefault(lk.side, lk.team_id)

        def team_logo(team_name):
            side = "a" if team_name == st.team_a else "b" if team_name == st.team_b else None
            tid = side_team.get(side)
            return f"/api/v1/teams/{tid}/photo" if tid else None

        def player_photo(name):
            pid = name_pid.get(name)
            return f"/api/v1/players/{pid}/photo" if pid else None

        def bat(name):
            if not name:
                return None
            b = next((x for x in inn.batters if x.name == name), None)
            if b is None:
                return None
            return {"name": b.name, "runs": b.runs, "balls": b.balls, "fours": b.fours,
                    "sixes": b.sixes, "sr": b.strike_rate, "on_strike": b.on_strike,
                    "photo": player_photo(b.name)}

        bowler = None
        if inn.bowler:
            w = next((x for x in inn.bowlers if x.name == inn.bowler), None)
            if w is not None:
                bowler = {"name": w.name, "overs": w.overs, "maidens": w.maidens,
                          "runs": w.runs, "wickets": w.wickets, "econ": w.economy,
                          "photo": player_photo(w.name)}

        recent = [self._ball_badge(c.kind, c.runs) for c in m.current.commentary[-6:]]

        last = m.current.commentary[-1] if m.current.commentary else None
        last_ball = None
        if last is not None:
            last_ball = {"kind": last.kind, "runs": last.runs, "text": last.text,
                         "over": last.over_ball, "batter": last.striker, "bowler": last.bowler}
            if last.kind == "wicket" and inn.fall_of_wickets:
                fw = inn.fall_of_wickets[-1]
                last_ball["out_batter"] = fw.batter_out
                last_ball["out_score"] = fw.score

        pnr = None
        unbroken = [p for p in inn.partnerships if p.unbroken]
        src = unbroken[-1] if unbroken else (inn.partnerships[-1] if inn.partnerships else None)
        if src is not None:
            pnr = {"runs": src.runs, "balls": src.balls, "a": src.batter_a, "b": src.batter_b}

        analytics = self._innings_analytics(m.current, inn, m.rules)
        pp = analytics.get("powerplay")

        return {
            "id": st.id,
            "complete": st.result is not None,
            "result": st.result,
            "status": "result" if st.result else ("break" if st.can_start_second_innings else "live"),
            "format": st.rules_name or st.format_id,
            "innings_no": st.current_innings,
            "teams": {"a": st.team_a, "b": st.team_b},
            "batting": inn.batting_team,
            "bowling": inn.bowling_team,
            "batting_logo": team_logo(inn.batting_team),
            "bowling_logo": team_logo(inn.bowling_team),
            "meta": st.meta.model_dump(),
            "runs": inn.runs, "wickets": inn.wickets, "overs": inn.overs_str,
            "max_overs": inn.max_overs, "max_wickets": inn.max_wickets,
            "crr": inn.run_rate,
            "target": inn.target, "need": inn.required_runs,
            "balls_left": inn.balls_remaining, "rrr": inn.required_run_rate,
            "win_prob": self._win_probability(inn),
            "free_hit": inn.free_hit,
            "striker": bat(inn.striker), "non_striker": bat(inn.non_striker),
            "bowler": bowler,
            "recent": recent,
            "last_ball": last_ball,
            "seq": len(m.commentary_feed()),
            "partnership": pnr,
            "phase": self._phase(inn),
            "ticker": [c.text for c in reversed(m.current.commentary[-10:])],
            "pp_summary": pp if (pp and pp.get("complete")) else None,
            "innings_summary": analytics,
            "awards": self._awards_with_photo(st, player_photo),
            "dls": ({
                "revised_target": st.dls.revised_target,
                "revised_overs": st.dls.revised_overs,
                "par": st.dls.par,
                "reason": (st.dls.interruptions[-1].reason if st.dls.interruptions else None),
                "abandoned": st.dls.abandoned,
                "revision_seq": st.dls.revision_seq,  # bumps per revision → overlay fires the banner once
            } if (st.dls and st.dls.applied) else None),
        }

    # ---- match-impact score (a transparent CricNetra metric, not an official one) --

    @staticmethod
    def _overs_to_balls(overs: str, bpo: int = 6) -> int:
        o, _, b = str(overs or "0").partition(".")
        try:
            return int(o) * bpo + (int(b) if b else 0)
        except ValueError:
            return 0

    @classmethod
    def _impact_table(cls, state: MatchStateDTO) -> dict:
        """Per-player impact = batting + bowling contribution, aggregated across the
        match. Batting: runs + 4s + 2·6s + aggression/milestone bonuses. Bowling:
        22·wkts + 8·maidens + an economy adjustment vs an 8-rpo par. Fielding isn't
        included (it isn't in the innings card). Used for the MoM headline + top list."""
        tbl: dict[str, dict] = {}

        def slot(name: str) -> dict:
            return tbl.setdefault(name, {"name": name, "bat": 0.0, "bowl": 0.0, "impact": 0})

        for inn in state.innings:
            for b in inn.batters:
                if not b.has_batted:
                    continue
                bi = b.runs + b.fours + 2 * b.sixes
                if b.balls >= 10 and b.strike_rate >= 160:
                    bi += 12
                elif b.balls >= 10 and b.strike_rate >= 130:
                    bi += 8
                if b.runs >= 100:
                    bi += 16
                elif b.runs >= 50:
                    bi += 8
                slot(b.name)["bat"] += bi
            for w in inn.bowlers:
                balls = cls._overs_to_balls(w.overs)
                if balls == 0 and w.wickets == 0:
                    continue
                wi = 22 * w.wickets + 8 * w.maidens + (8.0 - w.economy) * (balls / 6.0) * 0.6
                slot(w.name)["bowl"] += wi
        for s in tbl.values():
            s["impact"] = round(s["bat"] + s["bowl"])
            s["bat"], s["bowl"] = round(s["bat"]), round(s["bowl"])
        return tbl

    @classmethod
    def _mom_impact(cls, state: MatchStateDTO):
        """The Player-of-the-Match's impact number, or None if no MoM yet."""
        if not state.awards or not state.awards.man_of_the_match:
            return None
        return cls._impact_table(state).get(state.awards.man_of_the_match.name, {}).get("impact")

    @classmethod
    def _awards_with_impact(cls, state: MatchStateDTO):
        """awards.model_dump() with the MoM's impact number folded in (for the overlay)."""
        if not state.awards:
            return None
        awards = state.awards.model_dump()
        mi = cls._mom_impact(state)
        if awards.get("man_of_the_match") and mi is not None:
            awards["man_of_the_match"]["impact"] = mi
        return awards

    @classmethod
    def _awards_with_photo(cls, state: MatchStateDTO, player_photo):
        """As _awards_with_impact, plus the MoM's player-photo URL (overlay MoM card)."""
        awards = cls._awards_with_impact(state)
        if awards and awards.get("man_of_the_match"):
            awards["man_of_the_match"]["photo"] = player_photo(awards["man_of_the_match"]["name"])
        return awards

    # ---- broadcast analytics (powerplay / innings summary / analysis overlay) -----

    @staticmethod
    def _phase_over_range(dto: InningsDTO, rules, which: str) -> tuple:
        """0-indexed (lo, hi) over span for the first 'pp' or the 'death' overs."""
        mx = dto.max_overs or 0
        if which == "pp":
            pp_end = rules.powerplays[0].end_over if getattr(rules, "powerplays", None) else min(6, mx or 6)
            return 0, min(pp_end, mx or pp_end)
        death_from = (mx - 5) if mx >= 10 else max(0, int(mx * 0.8))
        return death_from, mx

    def _phase_stats(self, inn_engine, dto: InningsDTO, rules, which: str):
        """Score / RR / boundaries / sixes for the powerplay or death overs, or None."""
        lo, hi = self._phase_over_range(dto, rules, which)
        if hi <= lo:
            return None
        worm = dto.worm or []

        def cum(overs: int) -> int:  # cumulative runs after `overs` completed overs
            if overs <= 0:
                return 0
            return worm[overs - 1] if len(worm) >= overs else (dto.runs if worm else 0)

        runs = cum(hi) - cum(lo)
        wkts = sum(1 for fw in dto.fall_of_wickets if lo <= int(str(fw.over).split(".")[0]) < hi)
        fours = sixes = 0
        for c in inn_engine.commentary:
            try:
                ov = int(str(c.over_ball).split(".")[0])
            except (ValueError, AttributeError):
                continue
            if lo <= ov < hi:
                if c.kind == "six":
                    sixes += 1
                elif c.kind == "four":
                    fours += 1
        span = hi - lo
        bpo = getattr(rules, "balls_per_over", 6) or 6
        return {
            "from": lo, "to": hi, "overs": span, "runs": runs, "wickets": wkts,
            "run_rate": round(runs / span, 2) if span else 0.0,
            "fours": fours, "sixes": sixes, "boundaries": fours + sixes,
            "complete": dto.legal_balls >= hi * bpo,   # phase overs fully bowled
        }

    def _innings_analytics(self, inn_engine, dto: InningsDTO, rules) -> dict:
        """Extended per-innings stats shared by the powerplay banner, the innings-break
        card and the analysis overlay — all pure projections of the existing state."""
        fours = sum(b.fours for b in dto.batters)
        sixes = sum(b.sixes for b in dto.batters)
        dots = sum(1 for c in inn_engine.commentary if c.kind == "dot")
        extras = (dto.extras or {}).get("total", 0)
        batted = [b for b in dto.batters if b.has_batted]
        top_bat = max(batted, key=lambda b: b.runs, default=None)
        bowled = [w for w in dto.bowlers if self._overs_to_balls(w.overs) > 0]
        top_bowl = max(bowled, key=lambda w: (w.wickets, -w.runs), default=None)
        hp = max(dto.partnerships, key=lambda p: p.runs, default=None)
        return {
            "team": dto.batting_team, "total": dto.runs, "wickets": dto.wickets,
            "overs": dto.overs_str, "run_rate": dto.run_rate,
            "fours": fours, "sixes": sixes, "boundaries": fours + sixes,
            "dots": dots, "extras": extras,
            "highest_pnr": ({"runs": hp.runs, "balls": hp.balls, "a": hp.batter_a, "b": hp.batter_b} if hp else None),
            "top_bat": ({"name": top_bat.name, "runs": top_bat.runs, "balls": top_bat.balls} if top_bat else None),
            "top_bowl": ({"name": top_bowl.name, "wickets": top_bowl.wickets, "runs": top_bowl.runs,
                          "overs": top_bowl.overs} if top_bowl else None),
            "powerplay": self._phase_stats(inn_engine, dto, rules, "pp"),
            "death": self._phase_stats(inn_engine, dto, rules, "death"),
        }

    def analysis(self, match_id: str) -> dict:
        """Data for the analysis OBS scene (/overlay/{id}/analysis): per-innings worm +
        extended stats, projected score, current/required RR, current partnership. A
        separate low-frequency scene — reuses the same engine projection, no new writes."""
        m = self.get_engine(match_id)
        st = self._state(match_id, m)
        eng_inns = [m.innings1] + ([m.innings2] if m.innings2 is not None else [])
        innings = []
        for i, dto in enumerate(st.innings[:len(eng_inns)]):
            a = self._innings_analytics(eng_inns[i], dto, m.rules)
            a["worm"] = list(dto.worm or [])
            a["max_overs"] = dto.max_overs
            innings.append(a)

        cur = st.innings[st.current_innings - 1]
        projected = round(cur.run_rate * cur.max_overs) if cur.legal_balls else None
        pnr = None
        unbroken = [p for p in cur.partnerships if p.unbroken]
        src = unbroken[-1] if unbroken else (cur.partnerships[-1] if cur.partnerships else None)
        if src is not None:
            pnr = {"runs": src.runs, "balls": src.balls, "a": src.batter_a, "b": src.batter_b}

        return {
            "id": st.id,
            "complete": st.result is not None,
            "result": st.result,
            "status": "result" if st.result else ("break" if st.can_start_second_innings else "live"),
            "format": st.rules_name or st.format_id,
            "innings_no": st.current_innings,
            "teams": {"a": st.team_a, "b": st.team_b},
            "batting": cur.batting_team, "bowling": cur.bowling_team,
            "runs": cur.runs, "wickets": cur.wickets, "overs": cur.overs_str,
            "max_overs": cur.max_overs, "legal_balls": cur.legal_balls,
            "crr": cur.run_rate, "rrr": cur.required_run_rate,
            "target": cur.target, "need": cur.required_runs, "balls_left": cur.balls_remaining,
            "projected": projected,
            "partnership": pnr,
            "wagon": [w.model_dump() for w in cur.wagon],
            "pitch": [p.model_dump() for p in cur.pitch],
            "pp_overs": (m.rules.powerplays[0].end_over if m.rules.powerplays else 0),
            "innings": innings,
            "meta": st.meta.model_dump(),
        }

    def highlight_groups(self) -> list[MatchHighlightsDTO]:
        """Every match that has highlight clips, grouped — live first, most clips first.
        Powers the cross-match highlights gallery (in-app hub + public /highlights)."""
        groups: list[MatchHighlightsDTO] = []
        for s in self.list_summaries():
            try:
                st = self.get_state(s.id)
            except MatchNotFound:
                continue
            if not st.clips:
                continue
            live = st.result is None
            groups.append(
                MatchHighlightsDTO(
                    match_id=st.id, team_a=st.team_a, team_b=st.team_b, live=live,
                    status_label=("Live" if live else "Result"),
                    fmt=(st.rules_name or st.format_id), clips=st.clips,
                )
            )
        groups.sort(key=lambda g: (0 if g.live else 1, -len(g.clips)))
        return groups

    def add_clip(self, match_id: str, url: str, label: Optional[str]) -> list[MatchClipDTO]:
        self.get_engine(match_id)  # 404 if missing
        info = stream_info(url)
        if info is None:
            raise InvalidMatchSetup("Enter a valid YouTube, Facebook, or http(s) clip link.")
        clips = self.repo.get_clips(match_id)
        if len(clips) >= 30:
            raise InvalidMatchSetup("You've reached the maximum of 30 clips for a match.")
        next_id = str(max((int(c["id"]) for c in clips if str(c.get("id", "")).isdigit()), default=0) + 1)
        clips.append({"id": next_id, "url": info.url, "label": ((label or "").strip()[:80] or None), "source": "link"})
        self.repo.set_clips(match_id, clips)
        return [self._clip_dto(c) for c in clips]

    def remove_clip(self, match_id: str, clip_id: str) -> list[MatchClipDTO]:
        self.get_engine(match_id)  # 404 if missing
        clips = [c for c in self.repo.get_clips(match_id) if str(c.get("id")) != str(clip_id)]
        self.repo.set_clips(match_id, clips)
        return [self._clip_dto(c) for c in clips]

    def delete(self, match_id: str) -> None:
        self.get_engine(match_id)  # raises if missing
        self.repo.delete(match_id)
        if self.match_players is not None:
            self.match_players.delete_for_match(match_id)

    # ----- mapping -----
    @staticmethod
    def _to_event(req: BallRequest) -> BallEvent:
        a = req.action
        # optional wagon (batting) + pitch (bowling) markers ride on ANY delivery
        shot: dict = {}
        if req.wagon_x is not None:
            shot["wagon_x"] = req.wagon_x
        if req.wagon_y is not None:
            shot["wagon_y"] = req.wagon_y
        if req.pitch_x is not None:
            shot["pitch_x"] = req.pitch_x
        if req.pitch_y is not None:
            shot["pitch_y"] = req.pitch_y
        if req.speed is not None:
            shot["speed"] = req.speed
        if a is BallAction.runs:
            return BallEvent.runs(req.value, **shot)
        if a is BallAction.wide:
            return BallEvent.wide(ran=req.value, **shot)
        if a is BallAction.no_ball:
            return BallEvent.no_ball(off_bat=req.value, **shot)
        if a is BallAction.bye:
            return BallEvent.bye(req.value or 1, **shot)
        if a is BallAction.leg_bye:
            return BallEvent.leg_bye(req.value or 1, **shot)
        if a is BallAction.wicket:
            if not req.dismissal:
                raise ScoringError("dismissal type is required for a wicket")
            try:
                dt = DismissalType(req.dismissal)
            except ValueError as e:
                raise ScoringError(f"unknown dismissal '{req.dismissal}'") from e
            return BallEvent.out(
                dt, runs_off_bat=req.value, batter_out=req.batter_out,
                fielder=req.fielder or None, **shot,
            )
        raise ScoringError(f"unknown action '{a}'")

    def _state(self, match_id: str, m: MatchEngine) -> MatchStateDTO:
        seq = [m.innings1]
        if m.innings2 is not None:
            seq.append(m.innings2)
        for so in m.super_overs:
            seq.append(so.first)
            if so.second is not None:
                seq.append(so.second)
        links = self.match_players.for_match(match_id) if self.match_players else []
        name_id = {lk.name: lk.player_id for lk in links}
        innings = [self._innings_dto(inn, super_over=(i >= 2), name_id=name_id) for i, inn in enumerate(seq)]
        current_innings = next((i + 1 for i, inn in enumerate(seq) if inn is m.current), len(seq))
        return MatchStateDTO(
            id=match_id,
            team_a=m.team_a,
            team_b=m.team_b,
            bat_first=m.bat_first,
            format_id=m.rules.format_id,
            rules_name=m.rules.name,
            rules=m.rules,
            current_innings=current_innings,
            awaiting_bowler=m.current.awaiting_new_over,
            over_pending=m.current.over_pending,
            staged_bowler=m.current.staged_bowler,
            available_bowlers=m.current.eligible_bowlers(),
            can_start_second_innings=(m.innings1.is_complete and m.innings2 is None),
            needs_super_over=m.needs_super_over,
            awaiting_super_second=m.awaiting_super_second,
            result=m.result,
            innings=innings,
            awards=m.awards(),
            stream=stream_info(self.repo.get_stream_url(match_id)),
            clips=[self._clip_dto(c) for c in self.repo.get_clips(match_id)],
            meta=self._meta_dto(self.repo.get_meta(match_id)),
            dls=m.dls_summary(),
        )

    @staticmethod
    def _innings_dto(inn: InningsEngine, super_over: bool = False, name_id: Optional[dict] = None) -> InningsDTO:
        sc = inn.scorecard()
        nid = name_id or {}
        return InningsDTO(
            batting_team=sc.batting_team,
            bowling_team=sc.bowling_team,
            runs=sc.runs,
            wickets=sc.wickets,
            legal_balls=sc.legal_balls,
            overs_str=sc.overs_str,
            max_overs=sc.max_overs,
            max_wickets=sc.max_wickets,
            extras=sc.extras,
            run_rate=sc.run_rate,
            batters=[
                BatterDTO(
                    name=b.name,
                    order=b.order,
                    runs=b.runs,
                    balls=b.balls,
                    fours=b.fours,
                    sixes=b.sixes,
                    out=b.out,
                    how_out=(b.how_out.value if b.how_out else None),
                    dismissal_text=b.dismissal_text,
                    on_strike=b.on_strike,
                    has_batted=b.has_batted,
                    strike_rate=b.strike_rate,
                    player_id=nid.get(b.name),
                )
                for b in sc.batters
            ],
            bowlers=[
                BowlerDTO(
                    name=w.name,
                    order=w.order,
                    overs=w.overs_str,
                    maidens=w.maidens,
                    runs=w.runs,
                    wickets=w.wickets,
                    economy=w.economy,
                    wides=w.wides,
                    no_balls=w.no_balls,
                    player_id=nid.get(w.name),
                )
                for w in sc.bowlers
            ],
            fall_of_wickets=[
                FallOfWicketDTO(wicket=f.wicket, score=f.score, batter_out=f.batter_out, over=f.over)
                for f in sc.fall_of_wickets
            ],
            partnerships=[
                PartnershipDTO(wicket=p.wicket, runs=p.runs, balls=p.balls, batter_a=p.batter_a,
                               batter_b=p.batter_b, unbroken=p.unbroken, run_rate=p.run_rate)
                for p in sc.partnerships
            ],
            this_over=sc.this_over,
            manhattan=sc.manhattan,
            worm=sc.worm,
            wagon=[
                WagonShotDTO(x=w.x, y=w.y, runs=w.runs, batter=w.batter, over=w.over,
                             ball=w.ball, bowler=w.bowler, wicket=w.wicket,
                             zone=zones.wagon_zone(w.x, w.y))
                for w in sc.wagon
            ],
            pitch=[
                PitchMarkDTO(x=p.x, y=p.y, runs=p.runs, wicket=p.wicket, bowler=p.bowler,
                             batter=p.batter, over=p.over, speed=p.speed,
                             length=zones.pitch_length(p.y), line=zones.pitch_line(p.x),
                             outcome=zones.ball_outcome(p.runs, p.wicket))
                for p in sc.pitch
            ],
            striker=sc.striker,
            non_striker=sc.non_striker,
            bowler=sc.bowler,
            free_hit=sc.free_hit,
            is_complete=sc.is_complete,
            target=sc.target,
            required_runs=sc.required_runs,
            balls_remaining=sc.balls_remaining,
            required_run_rate=sc.required_run_rate,
            result_note=sc.result_note,
            current_over=sc.current_over,
            in_powerplay=sc.in_powerplay,
            powerplay_label=sc.powerplay_label,
            fielders_outside_limit=sc.fielders_outside_limit,
            is_super_over=super_over,
        )
