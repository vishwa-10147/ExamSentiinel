#!/bin/sh
# Generates rehearsal-only secrets (.env) and a self-signed certificate for exam.localhost and
# api.exam.localhost. Both are git-ignored. Safe to re-run: existing files are kept.
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    {
        echo "SECRET_KEY=$(openssl rand -hex 32)"
        echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)"
        echo "REHEARSAL_PASSWORD=Rehearsal-$(openssl rand -hex 8)"
    } > .env
    echo "Wrote deploy/rehearsal/.env"
fi

mkdir -p certs
if [ ! -f certs/rehearsal.crt ]; then
    MSYS_NO_PATHCONV=1 openssl req -x509 -newkey rsa:2048 -nodes -days 30 \
        -keyout certs/rehearsal.key -out certs/rehearsal.crt \
        -subj "/CN=exam.localhost" \
        -addext "subjectAltName=DNS:exam.localhost,DNS:api.exam.localhost" 2>/dev/null
    echo "Wrote deploy/rehearsal/certs (self-signed, 30 days)"
fi
