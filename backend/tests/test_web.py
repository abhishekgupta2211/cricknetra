"""Frontend + marketing-site serving smoke tests.

Marketing site (/, /contact, /tips, /tools) and public directories
(/live-matches, /tournaments) are server-rendered (Jinja). The scoring SPA is at
/app. Static assets are shared by all.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ----- marketing site -------------------------------------------------------
def test_landing_page_served_at_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "CricNetra" in r.text
    assert "/landing.css" in r.text
    assert "/app" in r.text          # links into the scoring app
    assert "/js/app.js" not in r.text  # not the SPA shell


def test_contact_page_served():
    r = client.get("/contact")
    assert r.status_code == 200
    assert "Get in touch" in r.text


def test_login_and_register_pages_served():
    lo = client.get("/login")
    assert lo.status_code == 200
    assert "Sign in to continue" in lo.text and "/auth.js" in lo.text
    rg = client.get("/register")
    assert rg.status_code == 200
    assert "Create your account" in rg.text


def test_tips_page_served():
    r = client.get("/tips")
    assert r.status_code == 200
    assert "Cricket tips" in r.text
    assert "Fielding" in r.text and "Bowling" in r.text


def test_tools_page_served():
    r = client.get("/tools")
    assert r.status_code == 200
    assert "calculators" in r.text.lower()
    assert "/tools.js" in r.text       # interactive calculators/toss/wheel


# ----- public directories ---------------------------------------------------
def test_live_matches_directory():
    r = client.get("/live-matches")
    assert r.status_code == 200
    assert "Live cricket matches" in r.text


def test_tournaments_directory():
    r = client.get("/tournaments")
    assert r.status_code == 200
    assert "Cricket tournaments" in r.text
    assert "Organising a tournament" in r.text   # the sidebar CTA


# ----- the app + assets -----------------------------------------------------
def test_spa_shell_served_at_app():
    r = client.get("/app")
    assert r.status_code == 200
    assert "CricNetra" in r.text
    assert "/js/app.js" in r.text


def test_static_assets_served():
    assert client.get("/css/styles.css").status_code == 200
    assert client.get("/js/app.js").status_code == 200
    assert client.get("/landing.css").status_code == 200
    assert client.get("/tools.js").status_code == 200
    assert client.get("/manifest.webmanifest").status_code == 200


def test_healthz():
    assert client.get("/healthz").json()["status"] == "ok"
