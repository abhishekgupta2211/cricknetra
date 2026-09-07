"""Grounds + academies directory + search integration (#145)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _venue(**over):
    body = {"name": "Wankhede", "kind": "ground", "city": "Mumbai"}
    body.update(over)
    return client.post("/api/v1/venues", json=body)


def test_create_list_and_filter():
    r = _venue(contact="022-100", note="Marine Drive")
    assert r.status_code == 201
    v = r.json()
    assert v["kind"] == "ground" and v["city"] == "Mumbai" and v["contact"] == "022-100"

    _venue(name="Spin Academy", kind="academy", city="Pune")
    allv = client.get("/api/v1/venues").json()
    assert any(x["name"] == "Wankhede" for x in allv)

    grounds = client.get("/api/v1/venues?kind=ground").json()
    assert grounds and all(x["kind"] == "ground" for x in grounds)

    pune = client.get("/api/v1/venues?location=pune").json()  # case-insensitive
    assert any(x["name"] == "Spin Academy" for x in pune)
    assert all("pune" in (x["city"] or "").lower() for x in pune)


def test_get_and_delete():
    vid = _venue(name="Eden Gardens", city="Kolkata").json()["id"]
    assert client.get(f"/api/v1/venues/{vid}").json()["name"] == "Eden Gardens"
    assert client.delete(f"/api/v1/venues/{vid}").status_code == 204
    assert client.get(f"/api/v1/venues/{vid}").status_code == 404


def test_invalid_kind_rejected():
    assert _venue(kind="stadiumish").status_code == 400


def test_venues_q_searches_by_name():
    """The directory filter sends q=, which must match the venue NAME (not just
    city) so people can look a ground up by name — the core of #145's search."""
    _venue(name="Brabourne Oval", kind="ground", city="Mumbai")
    byname = client.get("/api/v1/venues?q=brabourne").json()
    assert any(v["name"] == "Brabourne Oval" for v in byname)
    # every returned row genuinely matches the term in its name or city
    assert all("brabourne" in (v["name"] + " " + (v["city"] or "")).lower() for v in byname)
    # a term that matches nothing returns an empty list (not everything)
    assert client.get("/api/v1/venues?q=zzq-no-such-venue").json() == []


def test_venues_q_composes_with_kind():
    _venue(name="Cover Drive Academy", kind="academy", city="Nagpur")
    _venue(name="Cover Point Ground", kind="ground", city="Nagpur")
    res = client.get("/api/v1/venues?q=cover&kind=academy").json()
    assert any(v["name"] == "Cover Drive Academy" for v in res)
    assert all(v["kind"] == "academy" for v in res)


def test_venues_in_unified_search():
    _venue(name="Chinnaswamy", kind="ground", city="Bengaluru")
    res = client.get("/api/v1/search?q=chinnas").json()
    assert "venues" in res
    assert any(v["name"] == "Chinnaswamy" for v in res["venues"])


def test_get_unknown_404():
    assert client.get("/api/v1/venues/999999").status_code == 404
