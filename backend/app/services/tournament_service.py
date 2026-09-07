"""TournamentService — create competitions, generate fixtures, start fixtures
(which create real matches), and compute the points table with NRR.

Standings are recomputed on read from the linked matches (event-sourced truth),
so they're always consistent. Fixture status is cached back to the repo so the
list view doesn't need to rebuild every match.
"""

from __future__ import annotations

from typing import Optional

from app.domain import presets
from app.domain.rules import MatchRules
from app.repositories.tournament_repository import TournamentRepository
from app.repositories.tournament_squad_repository import TournamentSquadRepository
from app.schemas.match import CreateMatchRequest
from app.schemas.tournament import (
    FixtureDTO,
    GroupStanding,
    PlayerTournamentDTO,
    StandingRow,
    StartFixtureRequest,
    TeamRef,
    TeamSquadDTO,
    TournamentCreate,
    TournamentDetailDTO,
    TournamentDTO,
)
from app.services.match_service import MatchNotFound, MatchService
from app.services.roster_service import RosterNotFound, RosterService

WIN_POINTS, TIE_POINTS, NR_POINTS = 2, 1, 1


def _as_int(value: str) -> int:
    """Sort key for an id that is numeric everywhere it is generated, but must
    not blow up a listing if one ever isn't."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class TournamentNotFound(Exception):
    ...


class InvalidTournament(Exception):
    ...


class FixtureError(Exception):
    ...


class SquadConflict(Exception):
    """A player is already registered to another team in this tournament."""


def _round_robin_schedule(team_ids: list[str]) -> list[list[tuple]]:
    """Circle-method schedule: list of rounds, each a list of (a, b) pairs."""
    teams: list = list(team_ids)
    if len(teams) % 2 == 1:
        teams.append(None)  # bye marker
    n = len(teams)
    rounds = []
    for _ in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = teams[i], teams[n - 1 - i]
            if a is not None and b is not None:
                pairs.append((a, b))
        rounds.append(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]  # rotate, keep first fixed
    return rounds


class TournamentService:
    def __init__(
        self,
        repo: TournamentRepository,
        match_service: MatchService,
        roster_service: RosterService,
        squad_repo: TournamentSquadRepository,
    ) -> None:
        self.repo = repo
        self.matches = match_service
        self.roster = roster_service
        self.squads = squad_repo

    # ----- per-tournament squads -----
    def _player_name(self, player_id: str) -> str:
        rec = self.roster.repo.get_player(player_id)
        return rec.name if rec else f"Player {player_id}"

    def team_squads(self, tournament_id: str) -> list[TeamSquadDTO]:
        rec = self.repo.get(tournament_id)
        if rec is None:
            raise TournamentNotFound(tournament_id)
        out: list[TeamSquadDTO] = []
        for tid in rec.team_ids:
            players = []
            for pid in self.squads.list_team(tournament_id, tid):
                try:
                    players.append(self.roster.get_player(pid))
                except RosterNotFound:
                    pass
            out.append(
                TeamSquadDTO(team_id=str(tid), team_name=self._team_name(tid) or f"Team {tid}", players=players)
            )
        return out

    def register_player(self, tournament_id: str, team_id: str, player_id: str) -> list[TeamSquadDTO]:
        rec = self.repo.get(tournament_id)
        if rec is None:
            raise TournamentNotFound(tournament_id)
        if str(team_id) not in [str(t) for t in rec.team_ids]:
            raise InvalidTournament("that team is not in this tournament")
        if self.roster.repo.get_player(player_id) is None:
            raise RosterNotFound(player_id)
        existing = self.squads.team_of(tournament_id, player_id)
        if existing is not None and str(existing) != str(team_id):
            raise SquadConflict(
                f"{self._player_name(player_id)} is already in "
                f"{self._team_name(existing)}'s squad for this tournament"
            )
        self.squads.add(tournament_id, team_id, player_id)
        return self.team_squads(tournament_id)

    def unregister_player(self, tournament_id: str, team_id: str, player_id: str) -> list[TeamSquadDTO]:
        if self.repo.get(tournament_id) is None:
            raise TournamentNotFound(tournament_id)
        self.squads.remove(tournament_id, team_id, player_id)
        return self.team_squads(tournament_id)

    def registrations_for_player(self, player_id: str) -> list[PlayerTournamentDTO]:
        """Every competition this player is registered in, newest first.

        The registration is the fact, not the appearance: a player picked for a
        squad belongs to that competition from the moment the organizer enters
        them, weeks before the first ball. Career history can only ever show
        the second half of that, because it is rebuilt from matches that have
        been played — so a player waiting for their first game is invisible
        there, and has to ask an organizer which cups they are even in.

        ``has_played`` keeps both facts on the same row rather than making the
        client join two endpoints to tell "entered" from "played".
        """
        played = self._tournament_appearances(player_id)
        out: list[PlayerTournamentDTO] = []
        for tournament_id, team_id in self.squads.list_for_player(str(player_id)):
            rec = self.repo.get(str(tournament_id))
            if rec is None:
                # The competition was deleted out from under the registration.
                # Nothing to show, and nothing to claim about a name we no
                # longer have.
                continue
            out.append(
                PlayerTournamentDTO(
                    tournament_id=str(rec.id),
                    tournament_name=rec.name,
                    format=rec.format,
                    status=rec.status,
                    team_id=str(team_id),
                    team_name=self._team_name(team_id) or f"Team {team_id}",
                    has_played=bool(played.get(str(rec.id))),
                    matches_played=played.get(str(rec.id), 0),
                )
            )
        out.sort(key=lambda d: _as_int(d.tournament_id), reverse=True)
        return out

    def _tournament_appearances(self, player_id: str) -> dict[str, int]:
        """How many matches this player has actually played in each competition.

        Read through the fixture rows rather than the match's display metadata:
        the ``tournament`` name stamped on a match is for the scorecard and two
        competitions may share a name, whereas the fixture link is the same fact
        authorization uses.
        """
        links = getattr(self.matches, "match_players", None)
        if links is None:
            return {}
        counts: dict[str, int] = {}
        for link in links.for_player(str(player_id)):
            tid = self.repo.tournament_id_for_match(link.match_id)
            if tid is not None:
                counts[str(tid)] = counts.get(str(tid), 0) + 1
        return counts

    # ----- helpers -----
    def _team_name(self, team_id: Optional[str]) -> Optional[str]:
        if team_id is None:
            return None
        try:
            return self.roster.get_team(team_id).name
        except RosterNotFound:
            return f"Team {team_id}"

    def _team_ref(self, team_id: Optional[str]) -> Optional[TeamRef]:
        if team_id is None:
            return None
        return TeamRef(id=team_id, name=self._team_name(team_id) or f"Team {team_id}")

    def _match_or_none(self, match_id: Optional[str]):
        if not match_id:
            return None
        try:
            return self.matches.get_engine(match_id)
        except MatchNotFound:
            return None

    # ----- create / list -----
    def create(self, req: TournamentCreate) -> TournamentDetailDTO:
        if req.format not in ("round_robin", "knockout", "groups"):
            raise InvalidTournament("format must be round_robin, knockout or groups")
        if len(req.team_ids) < 2:
            raise InvalidTournament("need at least 2 teams")
        for tid in req.team_ids:
            if self.roster.repo.get_team(tid) is None:
                raise InvalidTournament(f"team {tid} not found")
        rules = req.rules if req.rules is not None else self._preset_rules(req.format_id)
        team_ids = [str(t) for t in req.team_ids]

        config = {"win_points": req.win_points, "tie_points": req.tie_points, "nr_points": req.nr_points,
                  # DLS on if the top-level flag OR the chosen rulebook has it (captures the create-form toggle)
                  "dls_enabled": bool(req.dls_enabled or rules.dls_enabled)}
        groups_map: dict[str, list[str]] = {}
        if req.format == "groups":
            if req.num_groups > len(team_ids) // 2:
                raise InvalidTournament("each group needs at least 2 teams")
            groups_map = self._partition_groups(team_ids, req.num_groups)
            min_group = min(len(g) for g in groups_map.values())
            if req.advance_per_group > min_group:
                raise InvalidTournament("advance_per_group exceeds the smallest group")
            config.update(num_groups=req.num_groups, advance_per_group=req.advance_per_group, groups=groups_map)

        rec = self.repo.add(req.name, req.format, rules.model_dump(mode="json"), team_ids, config=config)
        if req.format == "round_robin":
            self.repo.add_fixtures(rec.id, self._round_robin_fixtures(team_ids))
        elif req.format == "groups":
            fixtures = []
            for label, gteams in groups_map.items():
                for rnd, pos, a, b, _g in self._round_robin_fixtures(gteams):
                    fixtures.append((rnd, pos, a, b, label))
            self.repo.add_fixtures(rec.id, fixtures)
        else:  # knockout — generate round 1 (byes become auto-completed fixtures)
            self._generate_knockout_round(rec.id, team_ids, 1)
        return self.get_detail(rec.id)

    @staticmethod
    def _partition_groups(team_ids: list[str], num_groups: int) -> dict[str, list[str]]:
        """Deal teams round-robin into pools A, B, … (sizes differ by at most one)."""
        labels = [chr(ord("A") + i) for i in range(num_groups)]
        groups: dict[str, list[str]] = {lab: [] for lab in labels}
        for idx, tid in enumerate(team_ids):
            groups[labels[idx % num_groups]].append(str(tid))
        return groups

    @staticmethod
    def _round_robin_fixtures(team_ids: list[str]) -> list[tuple]:
        """(round, position, team_a, team_b, None) tuples for a round-robin."""
        out = []
        for round_no, pairs in enumerate(_round_robin_schedule(team_ids), start=1):
            for pos, (a, b) in enumerate(pairs, start=1):
                out.append((round_no, pos, a, b, None))
        return out

    @staticmethod
    def _preset_rules(format_id: str):
        try:
            return presets.get_preset(format_id)
        except KeyError as e:
            raise InvalidTournament(f"unknown format '{format_id}'") from e

    # ----- knockout bracket (also used for the playoff stage of 'groups') -----
    def _generate_knockout_round(self, tournament_id: str, advancing: list[str], round_no: int, group=None) -> None:
        pairs, pos, i, bye = [], 1, 0, None
        while i + 1 < len(advancing):
            pairs.append((round_no, pos, advancing[i], advancing[i + 1], group))
            i += 2
            pos += 1
        if i < len(advancing):  # odd team out -> bye
            bye = advancing[i]
            pairs.append((round_no, pos, bye, None, group))
        created = self.repo.add_fixtures(tournament_id, pairs)
        if bye is not None:  # auto-complete the bye fixture
            self.repo.update_fixture(created[-1].id, status="completed", winner_team_id=bye)

    def _advance_knockout(self, tournament_id: str) -> None:
        """Advance the bracket (knockout fixtures, i.e. group is None)."""
        while True:
            bracket = [f for f in self.repo.fixtures(tournament_id) if f.group is None]
            if not bracket:
                break
            by_round: dict[int, list] = {}
            for f in bracket:
                by_round.setdefault(f.round, []).append(f)
            max_round = max(by_round)
            cur = by_round[max_round]
            if len(cur) <= 1:  # the final (or fewer) -> nothing to advance
                break
            if not all(f.status == "completed" for f in cur):
                break
            winners = [f.winner_team_id for f in cur if f.winner_team_id]
            if len(winners) != len(cur):  # an unresolved (tied) fixture blocks the bracket
                break
            self._generate_knockout_round(tournament_id, winners, max_round + 1)

    def _champion(self, fixtures) -> Optional[TeamRef]:
        bracket = [f for f in fixtures if f.group is None]
        if not bracket:
            return None
        max_round = max(f.round for f in bracket)
        final = [f for f in bracket if f.round == max_round]
        if len(final) == 1 and final[0].status == "completed" and final[0].winner_team_id:
            return self._team_ref(final[0].winner_team_id)
        return None

    @staticmethod
    def _seed_playoff(finishers: dict[str, list[str]], advance: int) -> list[str]:
        """Cross-seed group finishers into a bracket order: each group winner faces
        the next group's runner-up (A1 v B2, B1 v A2, …). Deeper qualifiers, if any,
        are appended in finishing order."""
        labels = sorted(finishers)
        adv: list[str] = []
        for i, lab in enumerate(labels):
            fs = finishers[lab]
            if not fs:
                continue
            adv.append(fs[0])  # group winner
            if advance >= 2:
                other = finishers[labels[(i + 1) % len(labels)]]
                if len(other) >= 2:
                    adv.append(other[1])  # next group's runner-up
        for pos in range(2, advance):
            for lab in labels:
                if pos < len(finishers[lab]):
                    adv.append(finishers[lab][pos])
        seen, out = set(), []
        for t in adv:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out

    def list(self) -> list[TournamentDTO]:
        return [self._summary(t) for t in self.repo.list()]

    def _summary(self, rec) -> TournamentDTO:
        return TournamentDTO(
            id=rec.id, name=rec.name, format=rec.format, status=rec.status,
            teams=[self._team_ref(tid) for tid in rec.team_ids],  # type: ignore[misc]
        )

    def delete(self, tournament_id: str) -> None:
        if self.repo.get(tournament_id) is None:
            raise TournamentNotFound(tournament_id)
        self.squads.delete_tournament(tournament_id)
        self.repo.delete(tournament_id)

    def set_dls(self, tournament_id: str, enabled: bool) -> TournamentDetailDTO:
        """Enable/disable DLS rain rules for every match in the tournament (admin)."""
        if self.repo.update_config(tournament_id, {"dls_enabled": bool(enabled)}) is None:
            raise TournamentNotFound(tournament_id)
        return self.get_detail(tournament_id)

    # ----- detail (fixtures + standings) -----
    def get_detail(self, tournament_id: str) -> TournamentDetailDTO:
        rec = self.repo.get(tournament_id)
        if rec is None:
            raise TournamentNotFound(tournament_id)

        results = self._resolve_fixtures(tournament_id)  # cache status/winner; collect result texts
        if rec.format == "knockout":
            self._advance_knockout(tournament_id)

        standings: list[StandingRow] = []
        groups: list[GroupStanding] = []
        if rec.format == "round_robin":
            standings = self._standings_for(rec, self.repo.fixtures(tournament_id), rec.team_ids)
        elif rec.format == "groups":
            groups = self._group_standings(rec)
            self._maybe_start_playoffs(rec, groups)  # seed the bracket once pools finish
            self._advance_knockout(tournament_id)  # advance the playoff bracket

        fixtures = self.repo.fixtures(tournament_id)  # re-read (playoffs may have been added)
        fixture_dtos = []
        for f in fixtures:
            result = results.get(f.id)
            if result is None and f.status == "completed" and f.team_b_id is None:
                result = "bye"
            fixture_dtos.append(
                FixtureDTO(
                    id=f.id, round=f.round, position=f.position,
                    team_a=self._team_ref(f.team_a_id), team_b=self._team_ref(f.team_b_id),
                    match_id=f.match_id, status=f.status, result=result, group=f.group,
                )
            )

        champion = self._champion(fixtures) if rec.format in ("knockout", "groups") else None
        summary = self._summary(rec)
        return TournamentDetailDTO(
            **summary.model_dump(), fixtures=fixture_dtos, standings=standings,
            groups=groups, champion=champion, config=rec.config or {},
        )

    def _group_standings(self, rec) -> list[GroupStanding]:
        """Per-pool points tables for a 'groups' tournament."""
        groups_map = (rec.config or {}).get("groups", {})
        all_fixtures = self.repo.fixtures(rec.id)
        out = []
        for label in sorted(groups_map):
            gteams = [str(t) for t in groups_map[label]]
            gfx = [f for f in all_fixtures if f.group == label]
            out.append(GroupStanding(group=label, standings=self._standings_for(rec, gfx, gteams)))
        return out

    def _maybe_start_playoffs(self, rec, groups: list[GroupStanding]) -> None:
        """Once every group game is complete and no bracket exists yet, seed the
        playoff bracket from each pool's top `advance_per_group` finishers."""
        all_fixtures = self.repo.fixtures(rec.id)
        group_fx = [f for f in all_fixtures if f.group is not None]
        if not group_fx or any(f.status != "completed" for f in group_fx):
            return
        if any(f.group is None for f in all_fixtures):  # bracket already generated
            return
        advance = int((rec.config or {}).get("advance_per_group", 2))
        finishers = {g.group: [r.team_id for r in g.standings][:advance] for g in groups}
        seeds = self._seed_playoff(finishers, advance)
        if len(seeds) >= 2:
            self._generate_knockout_round(rec.id, seeds, 1, group=None)

    def _resolve_fixtures(self, tournament_id: str) -> dict:
        """Derive & cache each fixture's status/winner from its linked match."""
        results: dict = {}
        for f in self.repo.fixtures(tournament_id):
            if not f.match_id:
                continue
            match = self._match_or_none(f.match_id)
            if match is None:
                continue
            if match.result is not None:
                winner_id = None
                if match.winner_team not in (None, "tie"):
                    if match.winner_team == self._team_name(f.team_a_id):
                        winner_id = f.team_a_id
                    elif match.winner_team == self._team_name(f.team_b_id):
                        winner_id = f.team_b_id
                self.repo.update_fixture(f.id, status="completed", winner_team_id=winner_id)
                results[f.id] = match.result
            else:
                self.repo.update_fixture(f.id, status="live")
        return results

    def _standings_for(self, rec, fixtures, team_ids) -> list[StandingRow]:
        cfg = rec.config or {}
        win_pts = int(cfg.get("win_points", WIN_POINTS))
        tie_pts = int(cfg.get("tie_points", TIE_POINTS))
        nr_pts = int(cfg.get("nr_points", NR_POINTS))
        acc = {
            str(tid): dict(p=0, w=0, l=0, t=0, nr=0, rf=0.0, of=0.0, ra=0.0, oa=0.0)
            for tid in team_ids
        }
        for f in fixtures:
            match = self._match_or_none(f.match_id)
            if match is None or match.result is None:
                continue
            winner = match.winner_team  # team name, "tie", or None
            for tid in (f.team_a_id, f.team_b_id):
                if tid not in acc:
                    continue
                a = acc[tid]
                name = self._team_name(tid)
                a["p"] += 1
                rf, of, ra, oa = self._nrr_contrib(match, name)
                a["rf"] += rf
                a["of"] += of
                a["ra"] += ra
                a["oa"] += oa
                if winner == "tie":
                    a["t"] += 1
                elif winner == name:
                    a["w"] += 1
                else:
                    a["l"] += 1

        rows = []
        for tid, a in acc.items():
            points = a["w"] * win_pts + a["t"] * tie_pts + a["nr"] * nr_pts
            nrr = (a["rf"] / a["of"] if a["of"] else 0.0) - (a["ra"] / a["oa"] if a["oa"] else 0.0)
            rows.append(
                StandingRow(
                    team_id=tid, name=self._team_name(tid) or f"Team {tid}",
                    played=a["p"], won=a["w"], lost=a["l"], tied=a["t"], no_result=a["nr"],
                    points=points, nrr=round(nrr, 3),
                )
            )
        rows.sort(key=lambda r: (r.points, r.nrr), reverse=True)
        return rows

    @staticmethod
    def _nrr_contrib(match, team_name):
        """(runs_for, overs_for, runs_against, overs_against) — all-out counts the
        full quota of overs (standard NRR)."""
        bpo = match.rules.balls_per_over
        max_overs = match.rules.overs_per_innings
        rf = of = ra = oa = 0.0
        innings = [match.innings1] + ([match.innings2] if match.innings2 is not None else [])
        for inn in innings:
            sc = inn.scorecard()
            all_out = sc.wickets >= sc.max_wickets
            overs = float(max_overs) if all_out else (sc.legal_balls / bpo)
            if sc.batting_team == team_name:
                rf, of = sc.runs, overs
            else:
                ra, oa = sc.runs, overs
        return rf, of, ra, oa

    # ----- start a fixture (creates the match) -----
    def start_fixture(self, fixture_id: str, req: StartFixtureRequest) -> FixtureDTO:
        f = self.repo.get_fixture(fixture_id)
        if f is None:
            raise FixtureError("fixture not found")
        if f.match_id:
            raise FixtureError("fixture already started")
        if f.team_a_id is None or f.team_b_id is None:
            raise FixtureError("fixture teams not set yet")

        team_a, team_b = self.roster.get_team(f.team_a_id), self.roster.get_team(f.team_b_id)
        # When a tournament squad is registered for a team, the XI must come from it.
        for team_id, picked in ((f.team_a_id, req.squad_a_ids), (f.team_b_id, req.squad_b_ids)):
            squad = set(self.squads.list_team(f.tournament_id, team_id))
            if squad and not set(map(str, picked)) <= squad:
                raise FixtureError("the XI must be chosen from the team's tournament squad")
        names_a = self._player_names(req.squad_a_ids)
        names_b = self._player_names(req.squad_b_ids)
        tournament = self.repo.get(f.tournament_id)
        rules = MatchRules.model_validate(tournament.rules)
        cfg = tournament.config or {}
        if "dls_enabled" in cfg:  # the tournament-wide DLS switch is authoritative
            rules = rules.model_copy(update={"dls_enabled": bool(cfg["dls_enabled"])})

        # Stamp the competition onto the match. Without this a fixture-started
        # match is indistinguishable from a friendly, and never appears in
        # anybody's tournament record — which is where a season is read.
        state = self.matches.create_match(
            CreateMatchRequest(
                team_a=team_a.name, team_b=team_b.name, bat_first=req.bat_first, rules=rules,
                squad_a=names_a, squad_b=names_b,
                squad_a_ids=req.squad_a_ids, squad_b_ids=req.squad_b_ids,
                team_a_id=f.team_a_id, team_b_id=f.team_b_id,
                tournament=tournament.name,
                match_no=self._fixture_label(
                    f, tournament.format, self.repo.fixtures(f.tournament_id)
                ),
            )
        )
        self.repo.update_fixture(fixture_id, match_id=state.id, status="live")
        updated = self.repo.get_fixture(fixture_id)
        return FixtureDTO(
            id=updated.id, round=updated.round, position=updated.position,
            team_a=self._team_ref(updated.team_a_id), team_b=self._team_ref(updated.team_b_id),
            match_id=updated.match_id, status="live", result=None,
        )

    @staticmethod
    def _fixture_label(fixture, fmt: str, all_fixtures: list) -> str:
        """How this fixture reads on a scorecard: "Final", "Match 3"."""
        if fixture.group:
            return f"Group {fixture.group} · Match {fixture.position}"
        # A knockout's rounds have names; a league's are just match numbers.
        rounds = [f.round for f in all_fixtures if f.round and not f.group]
        total = max(rounds) if rounds else 1
        if fmt != "round_robin" and total >= 1:
            named = {1: "Final", 2: "Semi-final", 3: "Quarter-final"}
            remaining = total - fixture.round + 1
            if remaining in named:
                return named[remaining]
            return f"Round {fixture.round}"
        return f"Match {fixture.position}"

    def _player_names(self, player_ids: list[str]) -> list[str]:
        names = []
        for pid in player_ids:
            rec = self.roster.repo.get_player(pid)
            names.append(rec.name if rec else f"Player {pid}")
        return names
