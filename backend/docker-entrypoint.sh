#!/bin/sh
# Container entrypoint.
#
#   (default)  serve the API with uvicorn
#   migrate    apply Alembic migrations and bootstrap the first admin, then exit
#              (run as a one-off ECS task / `docker compose run backend migrate`)
#
# RUN_MIGRATIONS_ON_START=true runs `migrate` before serving — only for
# single-instance setups (Render, one EC2 host), never with several replicas.
set -e

migrate() {
    python -m alembic upgrade head
    # Production: creates one admin from ADMIN_EMAIL/ADMIN_PASSWORD if none exists.
    python seed_admin.py || echo "Admin bootstrap skipped (see message above)."
}

if [ "$1" = "migrate" ]; then
    migrate
    exit 0
fi

if [ "$RUN_MIGRATIONS_ON_START" = "true" ]; then
    migrate
fi

exec uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers "${WEB_CONCURRENCY:-2}" \
    --proxy-headers --forwarded-allow-ips="*"
