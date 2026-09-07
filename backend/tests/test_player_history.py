"""A player's whole career: every match they played, grouped every useful way.

`/stats` gives the totals and the last five games. This is the other question a
player asks — "what have I actually done, match by match, and how did I go in
each competition" — which nothing answered before.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _player(name: str) -> str:
    return client.post("/api/v1/players", json={"name": name}).json()["id"]


def _match(*, squad_a, squad_b, ids_a, ids_b, tournament=None, venue=None, no=None):
    body = {
        "team_a": "Aces", "team_b": "Blues", "format_id": "t20", "bat_first": "a",
        "squad_a": squad_a, "squad_b": squad_b,
        "squad_a_ids": ids_a, "squad_b_ids": ids_b,
    }
    if tournament:
        body["tournament"] = tournament
    if venue:
        body["venue"] = venue
    if no:
        body["match_no"] = no
    r = client.post("/api/v1/matches", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _bat_out_an_innings(mid: str, bowler: str, runs: list[int]):
    """Score `runs` off the bat, then close the innings with three wickets."""
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": bowler})
    for v in runs:
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": v})
    for _ in range(3):
        client.post(
            f"/api/v1/matches/{mid}/balls",
            json={"action": "wicket", "dismissal": "bowled"},
        )


def test_history_is_the_whole_career_not_a_recent_sample():
    a, b, c = _player("Hist A"), _player("Hist B"), _player("Hist C")
    d, e, f = _player("Hist D"), _player("Hist E"), _player("Hist F")
    names_a, names_b = ["Hist A", "Hist B", "Hist C"], ["Hist D", "Hist E", "Hist F"]
    ids_a, ids_b = [a, b, c], [d, e, f]

    # Six matches — more than the five `/stats` keeps as recent form.
    mids = [
        _match(squad_a=names_a, squad_b=names_b, ids_a=ids_a, ids_b=ids_b)
        for _ in range(6)
    ]
    for mid in mids:
        client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Hist D"})
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})

    stats = client.get(f"/api/v1/players/{a}/stats").json()
    assert len(stats["recent"]) == 5, "recent form is deliberately a sample"

    history = client.get(f"/api/v1/players/{a}/history").json()
    assert history["matches_played"] == 6
    assert len(history["matches"]) == 6, "history is every match"
    # Newest first, so the top of the list is the most recent game.
    order = [int(m["match_id"]) for m in history["matches"]]
    assert order == sorted(order, reverse=True)


def test_a_match_row_carries_what_the_player_did():
    a, b, c = _player("Row A"), _player("Row B"), _player("Row C")
    d, e, f = _player("Row D"), _player("Row E"), _player("Row F")
    mid = _match(
        squad_a=["Row A", "Row B", "Row C"], squad_b=["Row D", "Row E", "Row F"],
        ids_a=[a, b, c], ids_b=[d, e, f],
        tournament="Winter Cup", venue="Oval Ground", no="7",
    )
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Row D"})
    for v in (4, 6, 2, 4):  # even runs keep the striker on strike
        client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": v})
    client.post(
        f"/api/v1/matches/{mid}/balls",
        json={"action": "wicket", "dismissal": "bowled"},
    )

    row = next(
        m for m in client.get(f"/api/v1/players/{a}/history").json()["matches"]
        if m["match_id"] == mid
    )

    assert row["team"] == "Aces" and row["opponent"] == "Blues"
    assert row["tournament"] == "Winter Cup"
    assert row["venue"] == "Oval Ground"
    assert row["match_no"] == "7"
    assert row["format"] == "T20"
    assert row["played_on"], "a career row needs a date"

    assert row["batted"] is True
    assert row["runs"] == 16 and row["balls"] == 5
    assert row["fours"] == 2 and row["sixes"] == 1
    assert row["not_out"] is False
    assert row["how_out"] == "bowled"
    assert row["bat_line"] == "16 (5)"

    # This player never bowled, so the bowling half stays empty rather than zero.
    assert row["bowled"] is False
    assert row["wickets"] is None


def test_a_bowlers_row_carries_their_spell():
    a, b, c = _player("Spell A"), _player("Spell B"), _player("Spell C")
    d, e, f = _player("Spell D"), _player("Spell E"), _player("Spell F")
    mid = _match(
        squad_a=["Spell A", "Spell B", "Spell C"],
        squad_b=["Spell D", "Spell E", "Spell F"],
        ids_a=[a, b, c], ids_b=[d, e, f],
    )
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Spell D"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 2})
    client.post(
        f"/api/v1/matches/{mid}/balls",
        json={"action": "wicket", "dismissal": "bowled"},
    )

    row = next(
        m for m in client.get(f"/api/v1/players/{d}/history").json()["matches"]
        if m["match_id"] == mid
    )

    assert row["team"] == "Blues" and row["opponent"] == "Aces"
    assert row["bowled"] is True
    assert row["wickets"] == 1
    assert row["runs_conceded"] == 6
    assert row["bowl_line"] == "1/6 (0.3)"
    assert row["economy"] == 12.0
    assert row["batted"] is False, "the Blues did not bat"


def test_record_is_broken_down_by_tournament():
    a, b, c = _player("Cup A"), _player("Cup B"), _player("Cup C")
    d, e, f = _player("Cup D"), _player("Cup E"), _player("Cup F")
    names_a, names_b = ["Cup A", "Cup B", "Cup C"], ["Cup D", "Cup E", "Cup F"]
    ids_a, ids_b = [a, b, c], [d, e, f]

    # Two matches in one cup, one in another, one outside any competition.
    for tournament, tally in (("Summer Cup", 2), ("Winter Cup", 1), (None, 1)):
        for _ in range(tally):
            mid = _match(
                squad_a=names_a, squad_b=names_b, ids_a=ids_a, ids_b=ids_b,
                tournament=tournament,
            )
            client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Cup D"})
            client.post(
                f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4}
            )

    history = client.get(f"/api/v1/players/{a}/history").json()
    by_tournament = {t["label"]: t for t in history["by_tournament"]}

    assert set(by_tournament) == {"Summer Cup", "Winter Cup"}, (
        "a match outside a competition belongs to no cup"
    )
    assert by_tournament["Summer Cup"]["matches"] == 2
    assert by_tournament["Summer Cup"]["batting"]["runs"] == 8
    assert by_tournament["Winter Cup"]["matches"] == 1
    assert by_tournament["Winter Cup"]["batting"]["runs"] == 4
    # Most-played first, so the biggest campaign leads.
    assert history["by_tournament"][0]["label"] == "Summer Cup"

    # The career total still counts every match, cup or not.
    assert history["matches_played"] == 4
    assert history["batting"]["runs"] == 16


def test_wins_and_losses_are_counted_from_the_players_side():
    a, b, c = _player("Win A"), _player("Win B"), _player("Win C")
    d, e, f = _player("Win D"), _player("Win E"), _player("Win F")
    mid = _match(
        squad_a=["Win A", "Win B", "Win C"], squad_b=["Win D", "Win E", "Win F"],
        ids_a=[a, b, c], ids_b=[d, e, f],
    )

    # Aces make a few, Blues are bowled out for less.
    _bat_out_an_innings(mid, "Win D", [4, 4, 4])
    client.post(f"/api/v1/matches/{mid}/second-innings")
    _bat_out_an_innings(mid, "Win A", [1])

    aces = client.get(f"/api/v1/players/{a}/history").json()
    blues = client.get(f"/api/v1/players/{d}/history").json()

    assert aces["won"] == 1 and aces["lost"] == 0
    assert aces["win_pct"] == 100.0
    assert aces["matches"][0]["outcome"] == "won"

    # The same match, read from the other dressing room.
    assert blues["won"] == 0 and blues["lost"] == 1
    assert blues["matches"][0]["outcome"] == "lost"


def test_a_live_match_is_in_progress_not_a_loss():
    a, b, c = _player("Live A"), _player("Live B"), _player("Live C")
    d, e, f = _player("Live D"), _player("Live E"), _player("Live F")
    mid = _match(
        squad_a=["Live A", "Live B", "Live C"], squad_b=["Live D", "Live E", "Live F"],
        ids_a=[a, b, c], ids_b=[d, e, f],
    )
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Live D"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})

    history = client.get(f"/api/v1/players/{a}/history").json()
    row = next(m for m in history["matches"] if m["match_id"] == mid)

    assert row["outcome"] == "in_progress"
    assert row["result"] is None
    # An unfinished game must not drag the win percentage down.
    assert history["lost"] == 0


def test_history_groups_by_year_and_by_side():
    a, b, c = _player("Grp A"), _player("Grp B"), _player("Grp C")
    d, e, f = _player("Grp D"), _player("Grp E"), _player("Grp F")
    mid = _match(
        squad_a=["Grp A", "Grp B", "Grp C"], squad_b=["Grp D", "Grp E", "Grp F"],
        ids_a=[a, b, c], ids_b=[d, e, f],
    )
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Grp D"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})

    history = client.get(f"/api/v1/players/{a}/history").json()

    assert len(history["by_year"]) == 1
    assert history["by_year"][0]["label"].isdigit()
    assert history["by_year"][0]["matches"] == 1

    assert [t["label"] for t in history["by_team"]] == ["Aces"]
    assert history["by_team"][0]["batting"]["runs"] == 4


def test_a_player_who_has_never_played_has_an_empty_career():
    solo = _player("Never Played")
    history = client.get(f"/api/v1/players/{solo}/history").json()

    assert history["matches_played"] == 0
    assert history["matches"] == []
    assert history["by_tournament"] == []
    assert history["debut"] is None
    assert history["win_pct"] == 0.0, "no matches must not divide by zero"
    assert history["batting"]["runs"] == 0


def test_an_unknown_player_is_a_404():
    assert client.get("/api/v1/players/does-not-exist/history").status_code == 404


def test_a_match_started_from_a_fixture_lands_in_the_tournament_record():
    """The normal way a cup match begins is from its fixture, not by typing the
    competition's name into a form. If that path does not stamp the tournament,
    every real cup game is filed as a friendly and the whole per-tournament
    record stays empty."""
    a, b, c = _player("Fx A"), _player("Fx B"), _player("Fx C")
    d, e, f = _player("Fx D"), _player("Fx E"), _player("Fx F")

    team_a = client.post("/api/v1/teams", json={"name": "Fixture Aces"}).json()["id"]
    team_b = client.post("/api/v1/teams", json={"name": "Fixture Blues"}).json()["id"]
    for pid in (a, b, c):
        client.post(f"/api/v1/teams/{team_a}/members", json={"player_id": pid})
    for pid in (d, e, f):
        client.post(f"/api/v1/teams/{team_b}/members", json={"player_id": pid})

    tourn = client.post(
        "/api/v1/tournaments",
        json={
            "name": "Fixture Cup",
            "format": "round_robin",
            "team_ids": [team_a, team_b],
        },
    ).json()
    fixture_id = tourn["fixtures"][0]["id"]

    started = client.post(
        f"/api/v1/tournaments/fixtures/{fixture_id}/start",
        json={
            "bat_first": "a",
            "squad_a_ids": [a, b, c],
            "squad_b_ids": [d, e, f],
        },
    )
    assert started.status_code in (200, 201), started.text
    mid = started.json()["match_id"]

    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Fx D"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})

    history = client.get(f"/api/v1/players/{a}/history").json()
    row = next(m for m in history["matches"] if m["match_id"] == mid)
    assert row["tournament"] == "Fixture Cup"
    assert row["match_no"], "a cup game should say which one it was"

    by_tournament = {t["label"]: t for t in history["by_tournament"]}
    assert "Fixture Cup" in by_tournament
    assert by_tournament["Fixture Cup"]["matches"] == 1
    assert by_tournament["Fixture Cup"]["batting"]["runs"] == 4
