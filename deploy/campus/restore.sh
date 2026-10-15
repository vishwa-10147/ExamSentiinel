#!/bin/sh
# Restore the database from a dump in ./backups. REPLACES all current data.
#
#   sh restore.sh backups/examsentinel-20261015-020000.dump
set -eu
cd "$(dirname "$0")"
dump="${1:?usage: sh restore.sh backups/<file>.dump}"
[ -f "$dump" ] || { echo "No such file: $dump"; exit 1; }

printf "This replaces ALL current data with %s. Type RESTORE to continue: " "$dump"
read -r answer
[ "$answer" = "RESTORE" ] || { echo "Cancelled."; exit 1; }

docker compose stop backend frontend                 # no writes while restoring
docker compose exec -T backup sh /backup.sh now      # keep what is being replaced, just in case
docker compose exec -T -e PGPASSWORD="$(grep '^POSTGRES_PASSWORD=' .env | cut -d= -f2-)" db \
    pg_restore -h localhost -U examsentinel -d examsentinel --clean --if-exists --no-owner < "$dump"
docker compose run --rm migrate                      # bring an older dump up to the current schema
docker compose start backend frontend
echo "Restored $dump."
