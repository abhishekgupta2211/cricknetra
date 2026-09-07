# Deploying CricNetra

CricNetra is one Docker image (FastAPI serving the API + the scoring SPA + the
marketing site) plus a PostgreSQL database. Pick **one** path below. All three
use the same image; only the hosting differs.

> The container **auto-applies DB migrations** (`alembic upgrade head`) on every
> start — you never run migrations by hand.

---

## 0. Before you deploy (hardening)

| Setting | Value | Status |
|---|---|---|
| `CRICNETRA_SECRET_KEY` | a long random string (`python -c "import secrets; print(secrets.token_urlsafe(64))"`) | set locally ✅ — **also set it on the host** |
| `CRICNETRA_AUTH_DEV_DELIVERY` | `false` | ✅ |
| Brevo SMTP key | regenerate in Brevo → **SMTP & API → SMTP keys**, revoke the old one | ⚠️ do this |

**Three golden rules**

1. **Never commit `.env`** (it's git-ignored). Put secrets in the host's env/secret store.
2. **Keep `CRICNETRA_SECRET_KEY` identical** across restarts and instances, or every deploy logs all users out.
3. **`CRICNETRA_DATABASE_URL`** must point at your production Postgres, and **take backups** (see the bottom).

---

## Path A — VPS + Docker Compose + Caddy (self-contained, recommended for control)

A single server (e.g. DigitalOcean Bangalore, AWS Mumbai, Hetzner) running the
app + Postgres + automatic HTTPS. Uses `docker-compose.yml` + `docker-compose.prod.yml` + `Caddyfile`.

1. **Provision** a small VM (1–2 GB RAM) and install Docker + the compose plugin.
2. **Point DNS**: an `A` record for your domain → the server's public IP.
3. **Copy the repo** to the server (`git clone` / `scp`).
4. **Configure**:
   ```bash
   cp .env.example .env
   nano .env        # fill: POSTGRES_PASSWORD, CRICNETRA_SECRET_KEY, the SMTP_* vars,
                    #       DOMAIN, LETSENCRYPT_EMAIL
   ```
5. **Launch** (Caddy fetches certs automatically):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```
6. Visit `https://your-domain` → marketing site; `/app` → scoring app; `/docs` → API.

Update later: `git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.

---

## Path B — Fly.io (Mumbai region, managed)

Uses `fly.toml`. Install the CLI (`flyctl`) and `fly auth login` first.

1. **Create the app** and set `app = "<name>"` in `fly.toml` to match:
   ```bash
   fly apps create your-cricnetra-name
   ```
2. **Database** — managed Postgres in Mumbai:
   ```bash
   fly postgres create --region bom
   fly postgres attach <db-app-name>          # prints a DATABASE_URL
   ```
   The app reads `CRICNETRA_DATABASE_URL`, so copy the value across:
   ```bash
   fly secrets set CRICNETRA_DATABASE_URL="postgres://...":  # from the attach output
   ```
3. **Secrets** (never in `fly.toml`):
   ```bash
   fly secrets set \
     CRICNETRA_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(64))')" \
     CRICNETRA_SMTP_USER="..." CRICNETRA_SMTP_PASSWORD="..." CRICNETRA_SMTP_FROM="..."
   ```
4. **Deploy**:
   ```bash
   fly deploy
   ```
   Fly gives you `https://<name>.fly.dev` with HTTPS built in; add a custom domain with `fly certs add`.

---

## Path C — Railway / Render (simplest, Singapore region)

1. New project → **Deploy from repo**; set the **Dockerfile path** to `backend/Dockerfile`
   and the **build context / root** to the repo root.
2. Add a **managed PostgreSQL** plugin/instance.
3. Set environment variables (Variables tab): `CRICNETRA_SECRET_KEY`,
   `CRICNETRA_DATABASE_URL` (from the managed PG), `CRICNETRA_AUTH_DEV_DELIVERY=false`,
   and the `CRICNETRA_SMTP_*` values.
4. Expose port **8000**; deploy. Both platforms give you an HTTPS URL automatically.

---

## After it's live

1. **Create your admin account** (the app blocks admin self-registration). Register
   normally in the UI, then promote yourself:
   ```bash
   # VPS:   docker compose exec app python scripts/make_admin.py --username <you>
   # Fly:   fly ssh console -C "python scripts/make_admin.py --username <you>"
   ```
2. **Smoke test**: `GET /health` returns 200; sign up a test user and confirm the
   OTP email actually arrives (proves SMTP works in prod).
3. **Back up the database** — a daily `pg_dump` is the minimum:
   ```bash
   # VPS example (cron):
   docker compose exec -T db pg_dump -U postgres CricNetra_db | gzip > backup-$(date +%F).sql.gz
   ```
   Managed Postgres (Fly/Railway/Render) has automated backups — turn them on.

---

## Files in this setup

| File | Purpose |
|---|---|
| `backend/Dockerfile` | the production image (API + static frontend) |
| `docker-compose.yml` | base stack: Postgres + app |
| `docker-compose.prod.yml` | overlay adding Caddy for HTTPS (Path A) |
| `Caddyfile` | reverse-proxy + auto-TLS config |
| `fly.toml` | Fly.io config (Path B) |
| `.env.example` | copy to `.env`, fill in your values |
