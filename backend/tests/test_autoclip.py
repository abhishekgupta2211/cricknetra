"""Auto-clipped video highlights (Option B #1) — ffmpeg cuts a clip around each
key moment from an uploaded recording, synced to the ball log via per-ball ts.

Skipped where ffmpeg isn't installed (the pipeline needs it)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.core import clipper
from app.main import app

client = TestClient(app)

pytestmark = pytest.mark.skipif(not clipper.available(), reason="ffmpeg not installed")


def _make_video(seconds: int = 30) -> bytes:
    d = tempfile.mkdtemp(prefix="cnvid_")
    p = os.path.join(d, "v.mp4")
    subprocess.run(
        [clipper.FFMPEG, "-y", "-f", "lavfi", "-i",
         f"testsrc=duration={seconds}:size=320x240:rate=15", "-c:v", "libx264", p],
        capture_output=True, check=True,
    )
    return open(p, "rb").read()


def _match_with_moments() -> str:
    mid = client.post(
        "/api/v1/matches",
        json={"team_a": "Alpha", "team_b": "Bravo", "format_id": "t20", "bat_first": "a"},
    ).json()["id"]
    client.post(f"/api/v1/matches/{mid}/bowler", json={"bowler": "Bravo 1"})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 6})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "runs", "value": 4})
    client.post(f"/api/v1/matches/{mid}/balls", json={"action": "wicket", "dismissal": "bowled"})
    return mid


def _cleanup(mid: str) -> None:
    shutil.rmtree(clipper.media_root() / "clips" / str(mid), ignore_errors=True)
    for f in (clipper.media_root() / "rec").glob(f"{mid}.*"):
        f.unlink(missing_ok=True)


def test_highlights_now_carry_timestamps():
    mid = _match_with_moments()
    hls = client.get(f"/api/v1/matches/{mid}/highlights").json()
    moments = [h for h in hls if h["kind"] in ("six", "four", "wicket")]
    assert moments and all(h.get("ts") for h in moments)  # wall-clock ts for video sync


def test_autoclip_end_to_end():
    mid = _match_with_moments()
    try:
        # ffmpeg is present; no recording yet → a clean 400
        assert client.post(f"/api/v1/matches/{mid}/clips/auto", json={"anchor": 5}).status_code == 400

        vid = _make_video(30)
        r = client.post(f"/api/v1/matches/{mid}/recording", files={"file": ("m.mp4", vid, "video/mp4")})
        assert r.status_code == 201 and r.json()["duration"] > 25

        # first ball sits ~5s into the video → every moment's clip lands inside it
        r = client.post(f"/api/v1/matches/{mid}/clips/auto", json={"anchor": 5})
        assert r.status_code == 201, r.text
        autos = [c for c in r.json() if c["source"] == "auto"]
        assert len(autos) >= 3  # six, four, wicket
        assert all(c["kind"] == "video" and c["url"].startswith(f"/media/{mid}/") for c in autos)

        # the cut clip is served and is a real, playable video
        got = client.get(autos[0]["url"])
        assert got.status_code == 200 and got.headers["content-type"].startswith("video/")
        assert len(got.content) > 1000

        # regenerating replaces the auto clips (doesn't pile up)
        again = client.post(f"/api/v1/matches/{mid}/clips/auto", json={"anchor": 5}).json()
        assert len([c for c in again if c["source"] == "auto"]) == len(autos)
    finally:
        _cleanup(mid)


def test_recording_rejects_non_video():
    mid = _match_with_moments()
    try:
        r = client.post(f"/api/v1/matches/{mid}/recording", files={"file": ("x.mp4", b"not a video", "video/mp4")})
        assert r.status_code == 400
    finally:
        _cleanup(mid)
