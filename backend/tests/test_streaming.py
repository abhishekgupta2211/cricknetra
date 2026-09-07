"""Bring-your-own live-stream link (Option A) — embed helper + match route."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.streaming import stream_info
from app.main import app

client = TestClient(app)


# ----- embed helper (pure) --------------------------------------------------
def test_youtube_watch_url_becomes_embed():
    s = stream_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert s and s.kind == "youtube"
    assert s.embed_url == "https://www.youtube.com/embed/dQw4w9WgXcQ"


def test_youtube_short_and_live_urls():
    assert stream_info("https://youtu.be/dQw4w9WgXcQ").embed_url.endswith("/embed/dQw4w9WgXcQ")
    assert stream_info("https://www.youtube.com/live/dQw4w9WgXcQ").embed_url.endswith("/embed/dQw4w9WgXcQ")


def test_facebook_url_becomes_plugin_embed():
    s = stream_info("https://www.facebook.com/somepage/videos/123456789/")
    assert s and s.kind == "facebook"
    assert s.embed_url.startswith("https://www.facebook.com/plugins/video.php?")
    assert "facebook.com%2Fsomepage" in s.embed_url  # the href is url-encoded (no raw injection)


def test_other_https_is_external_no_iframe():
    s = stream_info("https://example.com/live")
    assert s and s.kind == "external" and s.embed_url is None


def test_blank_and_dangerous_urls_rejected():
    for bad in (None, "", "   ", "not a url", "javascript:alert(1)", "ftp://x/y", "//evil.com"):
        assert stream_info(bad) is None, bad


# ----- match route ----------------------------------------------------------
def _match() -> str:
    body = {"team_a": "Strikers", "team_b": "Blasters", "format_id": "t20", "bat_first": "a"}
    return client.post("/api/v1/matches", json=body).json()["id"]


def test_set_get_and_clear_stream():
    mid = _match()
    assert client.get(f"/api/v1/matches/{mid}").json()["stream"] is None

    r = client.put(f"/api/v1/matches/{mid}/stream", json={"stream_url": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 200
    st = r.json()["stream"]
    assert st["kind"] == "youtube" and st["embed_url"].endswith("/embed/dQw4w9WgXcQ")

    # persists on a fresh read
    assert client.get(f"/api/v1/matches/{mid}").json()["stream"]["kind"] == "youtube"

    # clearing (blank) removes it
    r = client.put(f"/api/v1/matches/{mid}/stream", json={"stream_url": ""})
    assert r.status_code == 200 and r.json()["stream"] is None


def test_bad_stream_url_is_400():
    mid = _match()
    r = client.put(f"/api/v1/matches/{mid}/stream", json={"stream_url": "not-a-real-link"})
    assert r.status_code == 400


def test_stream_on_missing_match_is_404():
    r = client.put("/api/v1/matches/999999/stream", json={"stream_url": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 404
