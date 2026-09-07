"""Real-time live updates — the Server-Sent Events match stream."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_stream_emits_a_score_frame():
    mid = client.post(
        "/api/v1/matches", json={"team_a": "A", "team_b": "B", "format_id": "t20"}
    ).json()["id"]
    with client.stream("GET", f"/api/v1/matches/{mid}/stream?once=1") as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        frame = None
        for line in r.iter_lines():
            if line.startswith("data:"):
                frame = json.loads(line[len("data:"):].strip())
                break
        assert frame is not None
        assert frame["runs"] == 0
        assert frame["wickets"] == 0
        assert frame["done"] is False
    client.delete(f"/api/v1/matches/{mid}")


def test_stream_signals_gone_for_a_missing_match():
    with client.stream("GET", "/api/v1/matches/99999999/stream") as r:
        assert r.status_code == 200
        body = ""
        for line in r.iter_lines():
            body += line + "\n"
            if "gone" in body:
                break
        assert "gone" in body
