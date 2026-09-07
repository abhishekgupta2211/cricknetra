#!/bin/sh
# CricNetra container entrypoint.
#
# When a database is configured, bring the schema to the latest Alembic revision
# before serving. Migration is idempotent, so it's safe to run on every start
# (including multiple replicas — Alembic takes a lock). If it fails, we still
# start the app: app/db/session.py falls back to create_all on first request, so
# a dev/demo container boots even without a reachable migrations path.
set -e

if [ -n "$CRICNETRA_DATABASE_URL" ]; then
  echo "[entrypoint] applying database migrations (alembic upgrade head)..."
  if alembic upgrade head; then
    echo "[entrypoint] migrations applied."
  else
    echo "[entrypoint] WARNING: alembic upgrade failed; the app will fall back to create_all." >&2
  fi
else
  echo "[entrypoint] CRICNETRA_DATABASE_URL not set — running with the in-memory store."
fi

echo "[entrypoint] starting: $*"
exec "$@"
