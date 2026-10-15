#!/bin/sh
# Database backups for the campus stack (runs inside the "backup" container).
#
#   backup.sh now        one dump now
#   backup.sh schedule   a dump every day at BACKUP_HOUR (server time), keeping BACKUP_KEEP_DAYS days
set -eu

dump() {
    name="examsentinel-$(date +%Y%m%d-%H%M%S).dump"
    pg_dump -h db -U examsentinel -d examsentinel -Fc -f "/backups/$name.partial"
    mv "/backups/$name.partial" "/backups/$name"       # only complete dumps get the final name
    find /backups -name 'examsentinel-*.dump' -mtime +"${BACKUP_KEEP_DAYS:-14}" -delete
    echo "backup: wrote $name ($(du -h "/backups/$name" | cut -f1))"
}

if [ "${1:-}" = "now" ]; then
    dump
    exit 0
fi

echo "backup: daily at ${BACKUP_HOUR:-2}:00, keeping ${BACKUP_KEEP_DAYS:-14} days"
last=""
while true; do
    today=$(date +%Y%m%d)
    if [ "$(date +%H | sed 's/^0//')" = "${BACKUP_HOUR:-2}" ] && [ "$last" != "$today" ]; then
        dump || echo "backup: FAILED"
        last=$today
    fi
    sleep 300
done
