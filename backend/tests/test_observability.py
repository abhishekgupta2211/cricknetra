"""Observability — request ids, JSON error envelope, and the health checks."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_response_carries_request_id_header():
    r = client.get("/api/v1/health/live")
    assert r.status_code == 200
    assert r.headers.get("x-request-id")  # generated when none is supplied


def test_inbound_request_id_is_echoed():
    r = client.get("/api/v1/health/live", headers={"X-Request-ID": "trace-abc-123"})
    assert r.headers.get("x-request-id") == "trace-abc-123"


def test_api_404_returns_json_envelope_with_request_id():
    # A real API 404 (HTTPException) — goes through our handler, not StaticFiles.
    r = client.get("/api/v1/matches/nonexistent-match-xyz")
    assert r.status_code == 404
    body = r.json()
    assert body.get("detail")  # error message preserved
    # request_id present proves OUR handler ran (FastAPI's default omits it).
    assert body["request_id"]
    assert r.headers.get("x-request-id") == body["request_id"]


def test_validation_error_keeps_detail_and_adds_request_id():
    r = client.post("/api/v1/auth/login", json={})  # missing required fields
    assert r.status_code == 422
    body = r.json()
    assert isinstance(body["detail"], list)  # FastAPI's validation detail shape
    assert body["request_id"]


def test_health_readiness_reports_db_check():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # Tests run in-memory (conftest clears database_url).
    assert body["checks"]["database"] == "not_configured"


def test_liveness_is_simple_ok():
    r = client.get("/api/v1/health/live")
    assert r.json() == {"status": "ok"}


def test_unhandled_exception_returns_500_without_leaking():
    from fastapi.routing import APIRoute

    async def _boom():
        raise RuntimeError("super secret internal detail")

    # Insert before the catch-all StaticFiles mount at "/", else it's shadowed.
    app.router.routes.insert(0, APIRoute("/api/v1/__boom_test", _boom, methods=["GET"]))
    try:
        safe = TestClient(app, raise_server_exceptions=False)
        r = safe.get("/api/v1/__boom_test")
        assert r.status_code == 500
        body = r.json()
        assert body["detail"] == "Internal Server Error"  # generic, not the real message
        assert "super secret internal detail" not in r.text
        assert body["request_id"]
        assert r.headers.get("x-request-id") == body["request_id"]
    finally:
        app.router.routes = [
            rt for rt in app.router.routes
            if getattr(rt, "path", None) != "/api/v1/__boom_test"
        ]
