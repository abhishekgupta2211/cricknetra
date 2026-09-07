"""Players, teams, rosters, and creating a match from a picked XI."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_player_crud():
    r = client.post("/api/v1/players", json={"name": "Virat", "batting_style": "RHB"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["name"] == "Virat"
    assert any(p["id"] == pid for p in client.get("/api/v1/players").json())
    assert client.get(f"/api/v1/players/{pid}").json()["batting_style"] == "RHB"
    assert client.delete(f"/api/v1/players/{pid}").status_code == 204
    assert client.get(f"/api/v1/players/{pid}").status_code == 404


def test_update_player_details():
    pid = client.post("/api/v1/players", json={"name": "Jonny"}).json()["id"]
    r = client.patch(
        f"/api/v1/players/{pid}",
        json={"phone": "+44 123", "batting_style": "Left-hand bat", "bowling_style": "Right-arm fast"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["phone"] == "+44 123"
    assert body["batting_style"] == "Left-hand bat"
    assert body["bowling_style"] == "Right-arm fast"

    # partial update leaves other fields intact
    r2 = client.patch(f"/api/v1/players/{pid}", json={"phone": "+44 999"})
    assert r2.json()["phone"] == "+44 999"
    assert r2.json()["batting_style"] == "Left-hand bat"

    assert client.patch("/api/v1/players/999999", json={"phone": "x"}).status_code == 404


def test_team_roster_flow():
    tid = client.post("/api/v1/teams", json={"name": "Mumbai", "location": "MH"}).json()["id"]

    # add an existing player by id, as captain
    rohit = client.post("/api/v1/players", json={"name": "Rohit"}).json()
    t = client.post(f"/api/v1/teams/{tid}/members", json={"player_id": rohit["id"], "is_captain": True}).json()
    assert len(t["members"]) == 1 and t["members"][0]["is_captain"] is True

    # add a brand-new player by name (create + add in one call)
    t = client.post(f"/api/v1/teams/{tid}/members", json={"name": "Surya"}).json()
    assert {m["name"] for m in t["members"]} == {"Rohit", "Surya"}

    # remove a member
    t = client.delete(f"/api/v1/teams/{tid}/members/{rohit['id']}").json()
    assert [m["name"] for m in t["members"]] == ["Surya"]

    assert any(x["id"] == tid for x in client.get("/api/v1/teams").json())
    assert client.delete(f"/api/v1/teams/{tid}").status_code == 204
    assert client.get(f"/api/v1/teams/{tid}").status_code == 404


def test_player_has_code_and_can_join_multiple_teams():
    p = client.post("/api/v1/players", json={"name": "Hardik"}).json()
    assert p["code"].startswith("P") and len(p["code"]) >= 5   # stable roster code

    t1 = client.post("/api/v1/teams", json={"name": "Team One"}).json()["id"]
    t2 = client.post("/api/v1/teams", json={"name": "Team Two"}).json()["id"]

    # the SAME existing player added to BOTH teams — via player_id, no duplicate
    m1 = client.post(f"/api/v1/teams/{t1}/members", json={"player_id": p["id"]}).json()
    m2 = client.post(f"/api/v1/teams/{t2}/members", json={"player_id": p["id"]}).json()
    assert m1["members"][0]["player_id"] == p["id"]
    assert m2["members"][0]["player_id"] == p["id"]
    assert m1["members"][0]["code"] == p["code"]               # member carries the code

    # still exactly one "Hardik" in the pool (no duplicate created)
    assert len([x for x in client.get("/api/v1/players").json() if x["name"] == "Hardik"]) == 1


def test_create_match_from_picked_xi():
    r = client.post(
        "/api/v1/matches",
        json={
            "team_a": "Mumbai", "team_b": "Chennai", "format_id": "t20", "bat_first": "a",
            "squad_a": ["A1", "A2", "A3", "A4"],
            "squad_b": ["B1", "B2", "B3", "B4"],
        },
    )
    assert r.status_code == 201
    state = r.json()
    # rules snapshot reflects the 4-player XI
    assert state["rules"]["players_per_side"] == 4
    assert state["innings"][0]["max_wickets"] == 3  # all out at players-1
    assert state["innings"][0]["batters"][0]["name"] == "A1"


def test_uneven_squads_rejected():
    r = client.post(
        "/api/v1/matches",
        json={"team_a": "X", "team_b": "Y", "format_id": "t20",
              "squad_a": ["a", "b", "c"], "squad_b": ["d", "e"]},
    )
    assert r.status_code == 400
