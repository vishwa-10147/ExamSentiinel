#!/bin/sh
# Container entrypoint.
#
#   (default)  serve the API with uvicorn
#   migrate    apply Alembic migrations and bootstrap the first admin, then exit
#              (run as a one-off ECS task / `docker compose run backend migrate`)
#   <command>  run any other command, e.g. `python seed_practice.py`
#
# RUN_MIGRATIONS_ON_START=true runs `migrate` before serving — only for
# single-instance setups (Render, one EC2 host), never with several replicas.
set -e

migrate() {
    python -m alembic upgrade head
    # Production: creates one admin from ADMIN_EMAIL/ADMIN_PASSWORD if none exists.
    python seed_admin.py || echo "Admin bootstrap skipped (see message above)."
}

if [ "${1:-}" = "migrate" ]; then
    migrate
    exit 0
fi

# Any other command runs as given, e.g. `docker compose run --rm backend python seed_practice.py`.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

if [ "$RUN_MIGRATIONS_ON_START" = "true" ]; then
    migrate
fi

# FORWARDED_ALLOW_IPS: the load balancer's network (e.g. the VPC CIDR "10.0.0.0/16"); only
# those proxies' X-Forwarded-For identifies the client. Never "*" - clients could then fake
# their IP and escape per-IP sign-in limits (production start-up refuses it).
# On SIGTERM (ECS stopTimeout defaults to 30 s) uvicorn stops accepting connections, waits up to
# GRACEFUL_SHUTDOWN_SECONDS for requests in flight, then the app hands unfinished judging jobs
# back to the queue.
exec uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers "${WEB_CONCURRENCY:-2}" \
    --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
    --timeout-graceful-shutdown "${GRACEFUL_SHUTDOWN_SECONDS:-20}" \
    --no-server-header
