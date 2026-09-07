""""Looking For" board — API CRUD + filters (#140). Acts as the conftest admin."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _post(kind, text, **over):
    body = {"kind": kind, "text": text}
    body.update(over)
    return client.post("/api/v1/looking-for", json=body)


def test_create_list_and_filter():
    r = _post("team", "Looking for a team in Pune", location="Pune", role="all-rounder")
    assert r.status_code == 201
    p = r.json()
    assert p["kind"] == "team" and p["mine"] is True and p["status"] == "open"
    assert p["location"] == "Pune" and p["role"] == "all-rounder"
    pid = p["id"]

    _post("player", "Need 2 players for Sunday", location="Mumbai")

    everything = {x["id"]: x for x in client.get("/api/v1/looking-for").json()}
    assert pid in everything and everything[pid]["kind"] == "team"

    teams_only = client.get("/api/v1/looking-for?kind=team").json()
    assert teams_only and all(x["kind"] == "team" for x in teams_only)
    assert any(x["id"] == pid for x in teams_only)

    pune = client.get("/api/v1/looking-for?location=pune").json()  # case-insensitive substring
    assert any(x["id"] == pid for x in pune)
    assert all("pune" in (x["location"] or "").lower() for x in pune)


def test_invalid_kind_rejected():
    assert _post("coach", "Need a coach").status_code == 400


def test_mine_close_and_delete():
    pid = _post("match", "Friendly match this weekend").json()["id"]
    assert any(x["id"] == pid for x in client.get("/api/v1/looking-for/mine").json())

    # close → drops off the open board, stays in mine as 'closed'
    assert client.post(f"/api/v1/looking-for/{pid}/close").status_code == 204
    assert not any(x["id"] == pid for x in client.get("/api/v1/looking-for").json())
    mine = {x["id"]: x["status"] for x in client.get("/api/v1/looking-for/mine").json()}
    assert mine.get(pid) == "closed"

    # delete → gone from mine too
    assert client.delete(f"/api/v1/looking-for/{pid}").status_code == 204
    assert not any(x["id"] == pid for x in client.get("/api/v1/looking-for/mine").json())


def test_close_and_delete_unknown_return_404():
    assert client.post("/api/v1/looking-for/999999/close").status_code == 404
    assert client.delete("/api/v1/looking-for/999999").status_code == 404
