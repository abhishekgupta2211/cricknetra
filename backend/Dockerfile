# CricNetra API — production image.
#
# Build context MUST be the repo root (so both backend/ and frontend/ are in
# scope), because app/main.py resolves the frontend as a sibling of backend/:
#
#     docker build -f backend/Dockerfile -t cricnetra .
#
# The image mirrors the repo layout under /srv so that
# `Path(__file__).resolve().parents[2] / "frontend"` resolves to /srv/frontend.
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# psycopg[binary] bundles its own libpq, so no system Postgres libraries are
# needed. The healthcheck uses Python's stdlib (urllib), so no curl either.
# ffmpeg powers auto-clipped video highlights (degrades gracefully if removed).
WORKDIR /srv/backend

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# Install dependencies first so this layer is cached across code-only changes.
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# Application code + the static frontend it serves.
COPY backend/ /srv/backend/
COPY frontend/ /srv/frontend/

# Run as an unprivileged user. chmod the entrypoint before dropping root so the
# exec bit is set regardless of the build host (e.g. Windows checkouts).
RUN chmod +x /srv/backend/docker-entrypoint.sh \
 && useradd --system --uid 10001 cricnetra \
 && chown -R cricnetra /srv
USER cricnetra

EXPOSE 8000

# Liveness probe hitting the app's /healthz endpoint (no extra packages needed).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status==200 else sys.exit(1)"]

# Entrypoint applies DB migrations (when a database is configured) then execs CMD.
# --proxy-headers + --forwarded-allow-ips=* so uvicorn honours X-Forwarded-Proto/For
# from the reverse proxy (Caddy / Fly / Railway) and sees requests as HTTPS.
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
