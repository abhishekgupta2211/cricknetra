"""End-to-end (Playwright) fixtures.

Spins up a real uvicorn server for the test session, configured with an EMPTY
database url so it runs on the hermetic in-memory store — the e2e suite never
touches the developer's live Postgres data. Tests talk to it through a real
(headless) Chromium via pytest-playwright.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent / "backend"


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def live_server():
    """Start uvicorn (in-memory store) on a free port; yield its base URL."""
    port = _free_port()
    base = f"http://127.0.0.1:{port}"

    env = dict(os.environ)
    env["CRICNETRA_DATABASE_URL"] = ""           # in-memory: hermetic, no live DB
    env["CRICNETRA_RATE_LIMIT_ENABLED"] = "false"  # don't throttle the test run
    env["CRICNETRA_LOG_LEVEL"] = "WARNING"
    env["CRICNETRA_SEED_ADMIN"] = "e2eadmin:secret123"  # seed an admin so scorer flows are testable
    env["CRICNETRA_SMTP_HOST"] = ""              # never send real email from the test server
    env["CRICNETRA_AUTH_DEV_DELIVERY"] = "true"

    log = tempfile.TemporaryFile(mode="w+")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(_BACKEND), env=env, stdout=log, stderr=subprocess.STDOUT,
    )

    def _fail(msg: str):
        proc.kill()
        log.seek(0)
        raise RuntimeError(f"{msg}\n--- server output ---\n{log.read()}")

    deadline = time.time() + 45
    while time.time() < deadline:
        if proc.poll() is not None:
            _fail(f"server exited early (code {proc.returncode})")
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=2) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.4)
    else:
        _fail("server did not become ready within 45s")

    yield base

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    log.close()


@pytest.fixture(scope="session")
def base_url(live_server):
    """Override pytest-base-url's fixture so relative page.goto() works too."""
    return live_server


@pytest.fixture
def js_errors(page):
    """Collect meaningful JS problems: uncaught exceptions + real console.error.

    Filters the benign "Failed to load resource" lines Chromium logs for expected
    non-2xx responses (e.g. GET /auth/me -> 401 while logged out).
    """
    errors: list[str] = []

    def on_console(msg):
        if msg.type == "error" and "Failed to load resource" not in msg.text:
            errors.append("console: " + msg.text)

    page.on("console", on_console)
    page.on("pageerror", lambda exc: errors.append("pageerror: " + str(exc)))
    return errors
