# Production rehearsal

Runs the production images with `ENVIRONMENT=production` in the AWS topology, on one machine:

```
nginx "ALB" (TLS, host routing, WebSockets) ─┬─ frontend (Next.js standalone build)
                                              └─ backend × 2 replicas (2 uvicorn workers each)
PostgreSQL 16 (RDS) · Redis 7 (ElastiCache) · Piston on the host (the engine EC2 instance)
```

Use it before the first deployment and before releases that change infrastructure, settings or
dependencies. Everything here is for rehearsal only: generated secrets, a self-signed
certificate and test accounts.

## Run

Needs Docker and the code engine on `localhost:2000` (`docker compose -f docker-compose.piston.yml up -d`
from the repository root).

```bash
cd deploy/rehearsal
sh setup.sh                                  # .env with random secrets + a self-signed certificate
docker compose build
docker compose up -d db redis
docker compose run --rm migrate              # migrations + first admin, as the ECS one-off task does
docker compose up -d
docker compose exec -T backend python - < accounts.py   # proctor, reviewer, candidate (rehearsal only)
docker compose exec -T backend python seed_practice.py
```

- Browser: <https://exam.localhost:8443> (accept the self-signed certificate). Sign in as
  `admin@sentinel.edu` with `REHEARSAL_PASSWORD` from `.env`.
- Scripts: the API is also on <http://127.0.0.1:8080>.

## Checks

From the repository root, with the rehearsal password exported (`set -a; . deploy/rehearsal/.env; set +a`):

```bash
curl -s http://127.0.0.1:8080/api/health          # every component healthy, "environment": "production"
E2E_PASSWORD=$REHEARSAL_PASSWORD python scripts/e2e_roles_smoke.py --base-url http://127.0.0.1:8080
E2E_PASSWORD=$REHEARSAL_PASSWORD python scripts/multi_process_check.py --a http://127.0.0.1:8080 --b http://127.0.0.1:8080

cd frontend
PLAYWRIGHT_BASE_URL=https://exam.localhost:8443 PLAYWRIGHT_IGNORE_HTTPS_ERRORS=1 \
  E2E_API_URL=http://127.0.0.1:8080 E2E_PASSWORD=$REHEARSAL_PASSWORD npx playwright test --workers=1
cd ..

# Exam rush with a rolling restart in the middle (accounts go straight into the rehearsal database)
DATABASE_URL=postgresql+asyncpg://postgres:$POSTGRES_PASSWORD@127.0.0.1:55433/examsentinel \
  python scripts/load_test.py --students 250 --api http://127.0.0.1:8080 &
docker restart -t 30 examsentinel-rehearsal-backend-1   # once submissions are being judged
```

Run Playwright with one worker: signing in ends a user's other sessions, so parallel specs that
share an account sign each other out. All traffic from this machine comes from one address, so
wait a minute between load-test runs (300 sign-ins per minute per IP).

Latest results: [Production readiness](../../docs/PRODUCTION_READINESS.md#rehearsal-results).

## Tear down

```bash
docker compose down -v      # removes the containers and the rehearsal database
```
