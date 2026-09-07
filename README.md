# 🏏 CricNetra

A cricket scoring + community platform — a CricHeroes-style product with a
**configurable custom-rules engine** as the headline feature. Score matches
ball-by-ball, run leagues & knockouts, build player careers, and share live
public scorecards.

**API-first.** A versioned JSON REST API (`/api/v1`, OpenAPI at `/docs`) is the
real interface. The scoring core is pure, framework-free Python — event-sourced,
unit-tested, and reusable by any client.

## Status — a launchable product (✅ **204 backend tests + 12 e2e**)

**Scoring & rules**
- **Event-sourced engine** — every delivery is an append-only `BallEvent`; the
  scorecard, batting/bowling cards, fall-of-wickets, manhattan/worm/wagon charts
  and stats are all *projections* folded from the log. UNDO = pop + replay.
- **Configurable rules** — presets (T20, T10, ODI, Box, Gully, Street rule-out) +
  a custom-rule builder (powerplays, wides/no-balls, free hit, **DLS**,
  **super-over on tie**, fielding limits, **rule-out** = over-boundary is OUT).
- **Charts** — runs-per-over (manhattan), cumulative (worm), and a **wagon wheel**
  with optional shot-direction capture.

**Teams, players & competitions**
- Teams, players & rosters; matches pick a playing XI from a squad.
- **Career stats**, **leaderboards** (runs/avg/SR/wickets/econ/MVP/…), team records,
  fielding & recent form, player **insights** + **head-to-head compare**.
- **Tournaments** — round-robin leagues (auto fixtures, **points table + NRR**) and
  single-elimination **knockouts** (byes, progressive rounds, champion), with
  **per-tournament squads** (a player plays for one team per tournament).

**Accounts & community**
- **Auth** — JWT **access + rotating refresh tokens**, argon2 hashing, mobile +
  password login, account verification (OTP) + password reset, per-IP rate limiting.
- **Roles & permissions** — player / umpire / commentator / team_owner / organizer /
  admin / general_user; elevated roles need **admin approval** at sign-up.
  Per-match **umpire approval** lets an organizer grant scoring to any umpire.
- **Social** — follow members, an activity **feed**, and **notifications**.
- **Media** — player/team **photo & logo uploads**.
- **Network directory & search**, **ball-by-ball commentary feed**.

**Surfaces**
- **`/`** marketing site · **`/app`** the scoring PWA (installable, offline shell) ·
  **`/m/{id}`** & **`/t/{id}`** shareable public pages with **live SSE updates** ·
  `/live-matches`, `/tournaments`, `/tools`, `/tips`, `/contact`.

**Production-ready foundation**
- **Alembic migrations** (schema source of truth) · **Docker + docker-compose** ·
  **GitHub Actions CI** (tests / migrations-on-Postgres / image build / e2e) ·
  structured **logging** with request-id correlation, JSON **error envelope**, and a
  real **`/health`** (DB ping) + `/health/live` liveness probe.

## Architecture

**Event sourcing (the one decision that matters).** The innings is an
**append-only list of `BallEvent`s** — the single source of truth. Everything
derived is a projection folded from that log:

```
BallEvent log  ──fold──▶  InningsScorecard (runs, cards, extras, fall, charts)
     ▲
     └─ UNDO = pop last event + replay   ·   EDIT = patch event + replay
```

So UNDO, live editing, and editing finished scorecards never corrupt stats:
derived numbers are recomputed from the log, never stored as truth. Persistence
stores the match setup + the `ball_events` log; the engine is rebuilt by replay.

**Layering.**

```
HTTP ─▶ api/v1/routes ─▶ services ─▶ domain engine (pure)
   (thin)                  │
                           └─▶ repositories  ──▶  in-memory  ▸  SQL (Postgres)
```

Routes are thin; orchestration + DTO mapping live in the services; the database
only ever appears in the repository layer (a `settings.database_url` switch picks
the SQL or in-memory implementation), so the engine never changes underneath.

## Authorization — roles, ownership and scope

Three checks, and a request must pass all of them. Getting this wrong is how one
organizer ends up running another's competition, so the layers are deliberate:

```
capability   what KIND of thing this role may do        core/permissions.py
     +
ownership    who created this resource                  resource_owners table
     +
scope        whose competition it belongs to            services/scope_service.py
```

**A capability is never enough on its own.** Every organizer holds
`tournament.manage`; that says they may run competitions, not that they may
touch *yours*. `ScopeService` is the single place that answers "whose is this",
and it always reads ownership from the database — never from anything in the
request.

| Role | What it can do |
|---|---|
| `admin` | Everything, everywhere. Creates organizers, assigns roles. |
| `organizer` | Complete operational control of **their own** tournaments: fixtures, squads, staff, matches, scores — and nothing outside them. |
| `umpire` | Scores the matches they were approved for, one match at a time. |
| `commentator` | Posts on the competitions they were staffed on. |
| `player` | Reads. Participates in any organizer's tournament. |
| `general_user` | Reads public pages. |

**Sign-up grants no role.** Every account is created as a `general_user`; what
the form asked for is recorded as a request for an admin to act on. Otherwise
anyone could register as an organizer and start running competitions.

**A player is not owned by an organizer.** Identity and participation are
separate — `tournament_squads` is a many-to-many, so the same person plays in
several organizers' competitions and their career adds up across all of them.

`backend/tests/test_authorization_matrix.py` is the specification: it builds two
organizers with their own competitions, staff and players, then attacks the
boundary between them — including the IDOR case of changing the id in the URL.

```bash
# Build that world on a running server, to click around in:
bash mobile/tool/seed_rbac.sh
```

## Tech stack

FastAPI · Pydantic v2 · SQLAlchemy 2.0 · psycopg 3 · PostgreSQL · Alembic ·
python-jose (JWT) · passlib/argon2 · pytest · Playwright (e2e). Frontend is a
vanilla HTML/CSS/JS PWA (no framework); marketing/public pages are Jinja2.

## Run it

### Docker (one command)

```bash
cp .env.example .env          # set CRICNETRA_SECRET_KEY for anything real
docker compose up --build
# → http://localhost:8000   (/ marketing · /app scoring · /docs API)
```

Compose brings up Postgres + the app, applies migrations on start, and serves
everything on port 8000.

### Local (Python venv)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
#   behind a TLS-inspecting proxy add: --trusted-host pypi.org --trusted-host files.pythonhosted.org

copy .env.example .env        # set CRICNETRA_DATABASE_URL (or leave empty for the in-memory store)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8023
```

- App: http://127.0.0.1:8023/app · Marketing: http://127.0.0.1:8023/ · Swagger: `/docs`
- Health: `/api/v1/health` (readiness, pings the DB) · `/healthz` (liveness)

**Create the first admin** (admins can't self-register):

```powershell
.\.venv\Scripts\python.exe -m scripts.make_admin --create -u admin -n "Admin" -m 9000000000 -p "<password>"
#   or promote an existing user:  python -m scripts.make_admin <username>
```

## Tests

```powershell
# backend — hermetic (in-memory store, no DB needed)
cd backend ;  .\.venv\Scripts\python.exe -m pytest          # 204 passing

# end-to-end browser smoke (Playwright; spins up its own in-memory server)
cd .. ;  .\backend\.venv\Scripts\python.exe -m pip install -r e2e\requirements.txt
.\backend\.venv\Scripts\python.exe -m playwright install chromium
.\backend\.venv\Scripts\python.exe -m pytest e2e            # 12 passing
```

## Project layout

```
backend/
  app/
    domain/            # pure cricket logic: enums, rules, presets, events, engine
    schemas/           # Pydantic request/response DTOs (the API contract)
    repositories/      # data access — InMemory* + Sql* per aggregate
    services/          # orchestration + DTO mapping (MatchService, AuthService, …)
    api/
      deps.py          # DI: repo/service singletons, auth + capability guards
      v1/router.py     # aggregates all v1 routers
      v1/routes/       # auth, admin, users, search, health, presets, rule_templates,
                       #   players, teams, leaderboards, insights, tournaments,
                       #   matches, social
    public/            # marketing site + public shareable pages (Jinja2)
    core/              # config, security, permissions, ratelimit,
                       #   logging_config, middleware, errors
    db/                # SQLAlchemy base, models, lazy session + init_db
    main.py            # app composition (logging, middleware, routers, static)
  alembic/             # migrations (env.py + versions/)
  scripts/             # make_admin.py, db_check.py
  tests/               # pytest (engine, api, persistence, auth, charts, observability…)
frontend/              # the PWA SPA (index.html, js/app.js, js/api.js, css/styles.css,
                       #   sw.js) + auth/landing/site/live/tools assets
e2e/                   # Playwright smoke tests (pytest-playwright)
docs/                  # CricHeroes teardown + API reference
Dockerfile · docker-compose.yml · .env.example · .github/workflows/ci.yml
```

## API

See **[docs/02-api.md](docs/02-api.md)** for the reference (auth, scoring, the full
`MatchState` shape, and the grouped endpoint index) and **`/docs`** for the live,
exhaustive OpenAPI. The design teardown that shaped the build is in
[docs/01-cricheroes-teardown.md](docs/01-cricheroes-teardown.md).

> **Security:** set a strong `CRICNETRA_SECRET_KEY` and turn off
> `CRICNETRA_AUTH_DEV_DELIVERY` (which returns OTP/reset codes in API responses for
> testing) before deploying.
