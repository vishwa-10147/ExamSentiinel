#!/bin/sh
# Install a new version: back up, rebuild, migrate, restart. Run after `git pull`.
# Do it outside exam hours: the web app and API restart (about a minute).
set -eu
cd "$(dirname "$0")"

docker compose exec -T backup sh /backup.sh now      # a backup before anything changes
docker compose build
docker compose run --rm migrate                      # stops here if a migration cannot apply
docker compose up -d
docker compose exec -T backend python seed_practice.py
docker compose exec -T backend curl -sS http://localhost:8000/api/health; echo
