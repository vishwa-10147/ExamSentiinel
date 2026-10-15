#!/bin/sh
# First installation of ExamSentinel on a campus server. Safe to re-run.
#
#   sh setup.sh exam.college.edu admin@college.edu
#
# 1. writes .env with random secrets (kept if it already exists)
# 2. uses certs/fullchain.pem + certs/privkey.pem if present, otherwise a temporary self-signed
#    certificate (browsers warn; replace it - see README)
# 3. builds the images, starts the database, applies migrations and creates the first admin
# 4. starts everything, installs the code-engine runtimes (needs internet once) and loads the
#    practice problem bank
set -eu
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    host="${1:?usage: sh setup.sh <host name> <admin e-mail>}"
    admin="${2:?usage: sh setup.sh <host name> <admin e-mail>}"
    admin_password="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)"
    {
        echo "# Written by setup.sh - keep this file private (it holds the secrets)."
        echo "SERVER_NAME=$host"
        echo "PUBLIC_URL=https://$host"
        echo "SECRET_KEY=$(openssl rand -hex 32)"
        echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
        echo "ADMIN_EMAIL=$admin"
        echo "ADMIN_PASSWORD=$admin_password"
        echo "WEB_CONCURRENCY=4"
        echo "BACKUP_HOUR=2"
        echo "BACKUP_KEEP_DAYS=14"
        echo "ENABLE_EMAILS=false"
        echo "# See .env.example for e-mail, single sign-on, AI and port settings."
    } > .env
    chmod 600 .env
    echo "Wrote .env. First admin: $admin / $admin_password  (change it after signing in)"
fi
set -a; . ./.env; set +a

mkdir -p certs acme backups data/evidence
# The backend runs as uid 1001 and writes webcam evidence here.
chown 1001:1001 data/evidence 2>/dev/null || true

if [ ! -f certs/fullchain.pem ] || [ ! -f certs/privkey.pem ]; then
    echo "No certificate in certs/: creating a temporary self-signed one for $SERVER_NAME."
    openssl req -x509 -newkey rsa:2048 -nodes -days 30 \
        -keyout certs/privkey.pem -out certs/fullchain.pem \
        -subj "/CN=$SERVER_NAME" -addext "subjectAltName=DNS:$SERVER_NAME" 2>/dev/null
fi

docker compose build
docker compose up -d db redis
docker compose run --rm migrate
docker compose up -d

echo "Installing code-engine runtimes (first time downloads them; installed ones are skipped)..."
docker compose run --rm --no-deps -v "$(cd ../.. && pwd)/scripts:/scripts:ro" backend \
    python /scripts/install_piston_runtimes.py --url http://engine:2000
docker compose exec -T backend python seed_practice.py

echo
echo "Waiting for the API..."
for i in $(seq 1 30); do
    if docker compose exec -T backend curl -fsS http://localhost:8000/api/health >/dev/null 2>&1; then break; fi
    sleep 2
done
docker compose exec -T backend curl -sS http://localhost:8000/api/health; echo
echo
echo "ExamSentinel is running at $PUBLIC_URL"
echo "Sign in as $ADMIN_EMAIL (password in .env). Next steps: README.md"
