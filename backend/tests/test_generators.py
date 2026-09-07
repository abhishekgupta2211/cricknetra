"""Notification generators (P4) — in-play milestones, on-finish fan-out (match +
tournament), and persisted awards. Drives the dispatcher directly with lightweight
fake state so the producer logic is tested without spinning up the scoring engine."""

from __future__ import annotations

from types import SimpleNamespace as NS

from fastapi.testclient import TestClient

from app.api.deps import get_award_repo
from app.main import app
from app.repositories.award_repository import InMemoryAwardRepository
from app.repositories.match_player_repository import InMemoryMatchPlayerRepository, MatchPlayerLink
from app.repositories.social_repository import InMemorySocialRepository
from app.repositories.tournament_repository import InMemoryTournamentRepository
from app.repositories.user_repository import InMemoryUserRepository
from app.services.notification_generators import NotificationDispatcher
from app.services.social_service import SocialService

client = TestClient(app)


class _Roster:
    """Minimal roster stand-in: player_id → linked user_id (None if unclaimed)."""
    def __init__(self, links=None):
        self.links = links or {}

    def get_player(self, pid):
        return NS(user_id=self.links.get(str(pid)))


def _bat(name, runs, balls=0, player_id=None):
    return NS(name=name, runs=runs, balls=balls, player_id=player_id)


def _bowl(name, wkts, runs=0, player_id=None):
    return NS(name=name, wickets=wkts, runs=runs, player_id=player_id)


def _inn(batters=(), bowlers=()):
    return NS(batters=list(batters), bowlers=list(bowlers))


def _award(name, line):
    return NS(name=name, line=line, team=None)


def _awards(mom=None, best_bat=None, best_bowl=None):
    return NS(man_of_the_match=mom, best_batter=best_bat, best_bowler=best_bowl)


def _state(mid, result=None, innings=(), awards=None):
    return NS(id=mid, result=result, innings=list(innings), awards=awards)


def _make(player_users=None):
    srepo = InMemorySocialRepository()
    social = SocialService(srepo, InMemoryUserRepository())
    awards, mp, tourn = InMemoryAwardRepository(), InMemoryMatchPlayerRepository(), InMemoryTournamentRepository()
    disp = NotificationDispatcher(social, awards=awards, roster=_Roster(player_users),
                                  match_players=mp, tournaments=tourn)
    return disp, srepo, awards, mp, tourn


# --------------------------------------------------------------------------- #
# in-play milestones
# --------------------------------------------------------------------------- #
def test_fifty_notifies_player_followers_once():
    disp, srepo, *_ = _make()
    srepo.follow_entity("fan", "player", "p7")
    st = _state("m1", innings=[_inn(batters=[_bat("Kohli", 50, 34, "p7")])])
    disp.on_match_state(st)
    disp.on_match_state(st)                       # same state next ball → idempotent
    notes = srepo.notifications("fan")
    assert len(notes) == 1 and notes[0].category == "player" and "50" in notes[0].text


def test_batting_milestones_coalesce_for_follower():
    disp, srepo, *_ = _make()
    srepo.follow_entity("fan", "player", "p7")
    disp.on_match_state(_state("m1", innings=[_inn(batters=[_bat("Kohli", 50, 34, "p7")])]))
    disp.on_match_state(_state("m1", innings=[_inn(batters=[_bat("Kohli", 100, 72, "p7")])]))
    notes = srepo.notifications("fan")
    assert len(notes) == 1 and "100" in notes[0].text and notes[0].count == 2   # 50 then 100 fold


def test_five_wicket_haul_notifies():
    disp, srepo, *_ = _make()
    srepo.follow_entity("fan", "player", "b3")
    disp.on_match_state(_state("m1", innings=[_inn(bowlers=[_bowl("Bumrah", 5, 24, "b3")])]))
    notes = srepo.notifications("fan")
    assert len(notes) == 1 and "5-for" in notes[0].text


def test_casual_player_without_id_fires_nothing():
    disp, srepo, *_ = _make()
    srepo.follow_entity("fan", "player", "Kohli")   # can't really follow a nameless casual
    disp.on_match_state(_state("m1", innings=[_inn(batters=[_bat("Kohli", 80, 50, None)])]))
    assert srepo.unread_count("fan") == 0


def test_milestone_notifies_linked_user_as_achievement():
    disp, srepo, *_ = _make(player_users={"p7": "u9"})
    disp.on_match_state(_state("m1", innings=[_inn(batters=[_bat("Kohli", 50, 30, "p7")])]))
    notes = srepo.notifications("u9")
    assert len(notes) == 1 and notes[0].category == "achievement" and "You reached 50" in notes[0].text


def test_player_not_double_notified_when_following_self():
    disp, srepo, *_ = _make(player_users={"p7": "u9"})
    srepo.follow_entity("u9", "player", "p7")        # the player's user follows their own entity
    disp.on_match_state(_state("m1", innings=[_inn(batters=[_bat("Kohli", 50, 30, "p7")])]))
    notes = srepo.notifications("u9")
    assert len(notes) == 1 and notes[0].category == "achievement"   # only the achievement, not a follower copy


# --------------------------------------------------------------------------- #
# on finish: awards + tournament fan-out
# --------------------------------------------------------------------------- #
def test_awards_persisted_and_winners_notified():
    disp, srepo, awards, mp, tourn = _make(player_users={"p7": "u9"})
    mp.link([MatchPlayerLink("m1", "p7", "Kohli", "a"), MatchPlayerLink("m1", "b3", "Bumrah", "b")])
    srepo.follow_entity("fan", "player", "p7")
    st = _state("m1", result="Team A won by 20 runs",
                awards=_awards(mom=_award("Kohli", "82 (45) &amp; 1/12"), best_bowl=_award("Bumrah", "5/24")))
    disp.on_match_state(st)

    a = {x.award_type: x for x in awards.awards_for_match("m1")}
    assert a["mom"].player_key == "p7" and a["mom"].player_name == "Kohli"
    assert a["mom"].detail == "82 (45) & 1/12"          # HTML entities unescaped for the plain-text notif
    assert a["best_bowl"].player_key == "b3"
    assert any(n.title == "Man of the Match" for n in srepo.notifications("fan"))        # follower notified
    assert any("You won Man of the Match" in n.text for n in srepo.notifications("u9"))  # winner notified


def test_award_name_without_link_still_persists():
    disp, srepo, awards, mp, tourn = _make()
    # no match_players link → name can't resolve to a player id; store under the name
    disp.on_match_state(_state("m1", result="tie", awards=_awards(mom=_award("Guest", "40 (20)"))))
    a = awards.awards_for_match("m1")
    assert len(a) == 1 and a[0].player_key == "Guest" and a[0].player_name == "Guest"


def test_finish_fans_out_to_tournament_followers():
    disp, srepo, awards, mp, tourn = _make()
    t = tourn.add("Cup", "league", {}, ["1", "2"])
    fx = tourn.add_fixtures(t.id, [(1, 0, "1", "2")])[0]
    tourn.update_fixture(fx.id, match_id="m1")
    srepo.follow_entity("tfan", "tournament", t.id)
    disp.on_match_state(_state("m1", result="Team A won"))
    notes = srepo.notifications("tfan")
    assert len(notes) == 1 and notes[0].category == "tournament" and "Team A won" in notes[0].text


def test_finish_notifies_match_followers_once():
    disp, srepo, *_ = _make()
    srepo.follow_entity("mfan", "match", "m1")
    st = _state("m1", result="Draw")
    disp.on_match_state(st)
    disp.on_match_state(st)
    assert srepo.unread_count("mfan") == 1        # the match-finished fan-out is idempotent


# --------------------------------------------------------------------------- #
# awards surfaced on a player's profile (public endpoint)
# --------------------------------------------------------------------------- #
def test_player_awards_endpoint_lists_honours():
    repo = app.dependency_overrides[get_award_repo]()   # the per-test in-memory award store
    repo.add_award("m5", "mom", "p7", "Kohli", "82 (45)")
    repo.add_award("m6", "best_bat", "p7", "Kohli", "70 (40)")
    out = client.get("/api/v1/players/p7/awards").json()
    assert {o["award_type"] for o in out} == {"mom", "best_bat"}
    assert all(o["player_name"] == "Kohli" and "player_key" not in o for o in out)   # key stays internal
