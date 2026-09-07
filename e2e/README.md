# CricNetra — End-to-End (Playwright) smoke tests

Browser smoke tests for the marketing site, the public pages, and the scoring
SPA. They drive a real headless Chromium (via `pytest-playwright`) against a
uvicorn server that this suite starts itself.

The test server runs on the **in-memory store** (`CRICNETRA_DATABASE_URL=""`), so
the e2e suite is fully hermetic — it never touches your live Postgres data.

## Setup (one time)

From the repo root, using the backend virtualenv:

```bash
backend/.venv/Scripts/python -m pip install -r e2e/requirements.txt
backend/.venv/Scripts/python -m playwright install chromium
```

> On a machine behind a TLS-inspecting proxy, the browser download may fail SSL
> verification. Work around it for that one command:
> `NODE_TLS_REJECT_UNAUTHORIZED=0` (PowerShell: `$env:NODE_TLS_REJECT_UNAUTHORIZED="0"`).

## Run

```bash
backend/.venv/Scripts/python -m pytest e2e
```

Useful flags (from `pytest-playwright`):

- `--headed` — watch the browser run
- `--slowmo 500` — slow each action by 500 ms
- `--browser firefox` / `--browser webkit` — other engines (run `playwright install <name>` first)
- `--tracing on` / `--video on` / `--screenshot on` — capture artifacts to `test-results/`

## What's covered

- Marketing landing (`/`) loads with the right title + nav
- Public pages (`/contact`, `/tools`, `/tips`, `/live-matches`, `/tournaments`) return 200 and render
- The SPA (`/app`) boots with **no uncaught JS errors**
- `/login` and `/register` render their forms
- SPA hash-route navigation (`#/teams`) renders
- Full flow: register → auto-login → redirected into `/app` with a stored token
- A guard test asserts the server is the in-memory one (not the live DB)

These are intentionally **smoke** tests (does it load / boot / basic flow), complementing
the 201 backend unit/integration tests. Add deeper journeys here as needed.
