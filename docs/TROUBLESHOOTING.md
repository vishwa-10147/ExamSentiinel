# Troubleshooting

Common problems and their fixes. Start with the health report, which names the failing part:

```bash
curl http://localhost:8000/api/health
```

On a campus server run it inside the stack:
`docker compose exec backend curl -s localhost:8000/api/health` (in `deploy/campus/`).

## Contents

- [Installation](#installation)
- [Code execution](#code-execution)
- [Signing in](#signing-in)
- [Exams and proctoring](#exams-and-proctoring)
- [Docker Compose](#docker-compose)
- [Production start-up](#production-start-up)
- [Database](#database)

## Installation

| Symptom | Cause and fix |
|---|---|
| `pip install` fails building a wheel | Use Python **3.12**; newer versions may lack wheels for some dependencies. |
| `start-local.cmd` waits for Docker | Docker Desktop is not running or still starting. Start it and run the command again. |
| `Address already in use` / port busy | Something else uses 8000 (API), 3000 (web app), 2000 (engine), 5440 (PostgreSQL in Compose) or 6379 (Redis). Stop it, or stop the other ExamSentinel stack (`start-local.cmd stop`, `docker compose down`). |
| `next build` fails with a message about `NEXT_PUBLIC_API_URL` | Production builds require it. Set it in `frontend/.env.local` or as a build argument. |
| The engine image will not run on an Apple Silicon Mac | The image is amd64-only; emulation in Docker Desktop is untested. Use an x86-64 machine for code execution. |

## Code execution

| Symptom | Cause and fix |
|---|---|
| "Code execution engine is unavailable" | The engine is not running or `PISTON_URL` is wrong. Check `docker ps` for `examsentinel-piston` and that `PISTON_URL` points at it (`http://127.0.0.1:2000/api/v2/execute` for local development). |
| Health shows `code_engine` unhealthy, or one language never runs | The runtimes are not installed: `python scripts/install_piston_runtimes.py` (about 1 GB, once). |
| Submit shows "queued" and the verdict arrives later | Judging took longer than `SUBMIT_WAIT_SECONDS` (20 s); the page polls for the verdict. Persistent queueing means the engine or API needs more capacity; see `judge_queue` in the health report. |
| A problem's validation fails after editing it | The reference solution does not produce the expected outputs on the engine. See [Code execution](CODE_EXECUTION.md) and the `/practice-problems` workflow. |

## Signing in

| Symptom | Cause and fix |
|---|---|
| Signed out in one browser after signing in elsewhere | By design: each account has one active session. |
| "Too many failed sign-in attempts" | Wait a minute (per address) or 15 minutes (per account), or reset the password. |
| A whole lab gets "Too many requests" | The lab shares one NAT address. Raise `LOGIN_RATE_LIMIT_PER_IP` (default 300 per minute). |
| Sign-in succeeds but every page returns to the login screen | The session cookie is not stored. Check that the web app's origin is listed in `CORS_ORIGINS`, and that a site served over plain HTTP does not set `COOKIE_SECURE=true`. |
| Demo accounts do not exist | `seed_admin.py` creates them only when `ENVIRONMENT` is not `production`. In production the first admin comes from `ADMIN_EMAIL` / `ADMIN_PASSWORD`. |
| No password-reset e-mail arrives | `ENABLE_EMAILS` is off or no provider is configured; see [Configuration](CONFIGURATION.md#e-mail-password-reset-codes). |

## Exams and proctoring

| Symptom | Cause and fix |
|---|---|
| The browser does not ask for the webcam | Webcam and microphone work only on `https://` pages or on `localhost`. Serve the site over HTTPS with a trusted certificate. |
| Phone detection reported as unavailable | The optional AI packages are not installed (`backend/requirements-ai.txt`, or an image built with `WITH_AI=true`). In-browser face detection works without them. |
| A candidate lost connection during an exam | Answers are kept in the browser and re-sent when the connection returns; reopening the exam resumes the same session. The exam is only shown as submitted once the server confirms it. |
| A high risk score | Scores are advisory and never penalise a candidate automatically. Review the case under **Reviewer**. |
| Live interview video does not connect across networks | Configure a TURN server in `NEXT_PUBLIC_ICE_SERVERS` and rebuild the web app. |

## Docker Compose

| Symptom | Cause and fix |
|---|---|
| Containers start but the API cannot reach the database or engine | The root `.env` was copied from `.env.example`, passing the development `DATABASE_URL` and `PISTON_URL` into the containers. The root `.env` should contain only `SECRET_KEY` (and optionally ports); see [Setup](../SETUP.md#option-c-the-whole-stack-in-docker). |
| `examsentinel-piston` name conflict | `docker-compose.piston.yml` and `docker-compose.yml` both define it. Run only one of them. |
| Changes to `NEXT_PUBLIC_*` have no effect | They are compiled in at build time: `docker compose up -d --build frontend`. |
| `docker compose exec backend ...` fails on Windows Git Bash with a path like `C:/Program Files/Git/...` | Git Bash rewrites paths starting with `/`. Prefix the command with `MSYS_NO_PATHCONV=1`. |

## Production start-up

| Symptom | Cause and fix |
|---|---|
| The API exits immediately with a list of problems | `ENVIRONMENT=production` refuses unsafe settings. Fix each listed item; see [Configuration](CONFIGURATION.md#development-vs-production). |
| Logs show the proxy's address instead of the student's | `FORWARDED_ALLOW_IPS` does not include the proxy or load balancer network. |
| Responses `503` with `Retry-After` under load | The database connection pool is exhausted. Raise the database size or lower `DB_POOL_SIZE` × workers × tasks below `max_connections`; watch the `DatabaseBusy` metric. |
| HTTP is not redirected to HTTPS | The front door must do it (nginx on the campus server, an ALB listener on port 80 on AWS); the web app does not. |

## Database

| Symptom | Cause and fix |
|---|---|
| An older local SQLite database lacks new columns | The API adds new columns on start-up. To start over in development only, stop the API, delete `backend/examsentinel_dev.db` and seed again. |
| Migration `017` stops with a list of duplicate exam sessions | An older database has more than one session for the same exam and candidate. Keep one per pair (normally the one with answers), delete the others, and run the migration again. |
| `alembic upgrade head` fails on SQLite | Migrations are for PostgreSQL. SQLite creates its schema on API start-up. |

Still stuck? Collect the health report and the API logs (`docker compose logs backend`, or the
API terminal) and open an issue.

---

[Back to README](../README.md) · [Documentation index](README.md)
