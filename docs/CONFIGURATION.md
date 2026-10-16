# Configuration

ExamSentinel is configured only through environment variables. This page lists every variable
the code reads, where it belongs, and what changes between development and production.
[`.env.example`](../.env.example) is the template (placeholders only).

## Contents

- [Where settings live](#where-settings-live)
- [Development vs production](#development-vs-production)
- [Reference](#reference)
- [Secrets](#secrets)

## Where settings live

| File / place | Read by | Holds |
|---|---|---|
| `backend/.env` | the API when run locally (`backend/app/core/config.py` loads it; real environment variables win) | development settings |
| `frontend/.env.local` | the web app | `NEXT_PUBLIC_*` only - compiled into the bundle and visible to every browser, so never a secret |
| `.env` (repository root) | `docker-compose.yml` only, for variable substitution | `SECRET_KEY`, optional ports and database password |
| `deploy/campus/.env` | the campus server stack | written by `setup.sh`; see [its README](../deploy/campus/README.md) |
| ECS task definitions + AWS Secrets Manager | production on AWS | see [AWS deployment](AWS_DEPLOYMENT.md#3-secrets-and-configuration) |

All of these files are git-ignored. Only `.env.example`, `.env.production.example` and
`deploy/campus/.env.example` are committed, and they contain placeholders.

## Development vs production

`ENVIRONMENT=production` switches on safety checks: the API **refuses to start** and lists every
problem if any of these holds (`production_problems` in `backend/app/core/config.py`):

| Check | Development default | Production requirement |
|---|---|---|
| `DEBUG` | `true` (detailed errors, `/docs` enabled) | `false` |
| `SECRET_KEY` | a built-in development key | random, at least 32 characters |
| `CORS_ORIGINS` | `http://localhost:3000` | public `https://` origin(s) only |
| `DATABASE_URL` | SQLite file | PostgreSQL |
| `COOKIE_SECURE` | off for plain-HTTP development | not `false` |
| `COOKIE_SAMESITE` | `lax` | `lax` or `strict` |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | the load balancer / proxy network, never `*` |
| `PISTON_URL` | local engine | your own engine, never the public emkc.org API |

Production also never creates demo accounts, emits CloudWatch metric lines by default, and
answers database saturation with `503` + `Retry-After`.

## Reference

Defaults are shown where the code defines one. "Prod" marks variables you normally set in
production.

### Core and security

| Variable | Default | Prod | Purpose |
|---|---|:---:|---|
| `ENVIRONMENT` | `development` | ✓ | `production` turns on the checks above |
| `DEBUG` | `true` | ✓ | detailed errors and `/docs`; must be `false` in production |
| `LOG_LEVEL` | `INFO` | | log verbosity (JSON logs) |
| `SECRET_KEY` | development key | ✓ | signs session tokens and evidence links |
| `ALGORITHM` | `HS256` | | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | | access-token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | | refresh-token lifetime |
| `COOKIE_SECURE` | on in production | | session cookies only over HTTPS |
| `COOKIE_SAMESITE` | `lax` | | cookie same-site policy |
| `COOKIE_DOMAIN` | unset | | only if the web app needs the cookie on a sibling subdomain |
| `CORS_ORIGINS` | localhost | ✓ | web app origin(s); comma-separated or a JSON list |
| `FRONTEND_URL` | `http://localhost:3000` | ✓ | links in e-mails, SSO redirects |
| `PUBLIC_API_URL` | `http://localhost:8000` | ✓ | SSO callback URLs, absolute evidence links |

### Client IP and rate limits

| Variable | Default | Prod | Purpose |
|---|---|:---:|---|
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | ✓ | proxies trusted to report the client IP (`X-Forwarded-For`) |
| `CLIENT_IP_HEADER` | unset | | one header set by a sanitising proxy (e.g. `CF-Connecting-IP`); leave unset behind an ALB |
| `LOGIN_RATE_LIMIT_PER_IP` | `300` | | sign-ins per minute per address (a lab behind one NAT shares an address) |

### Database and cache

| Variable | Default | Prod | Purpose |
|---|---|:---:|---|
| `DATABASE_URL` | PostgreSQL on localhost:5440 (backend/.env sets SQLite) | ✓ | `sqlite+aiosqlite:///...` or `postgresql+asyncpg://...` (`postgres://` is converted) |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `5` / `5` | | connections per worker process; keep tasks × workers × (size + overflow) below `max_connections` |
| `DB_POOL_TIMEOUT` | `30` | | seconds to wait for a pooled connection |
| `SQL_ECHO` | `false` | | log every SQL statement (diagnosis only) |
| `REDIS_URL` | `redis://localhost:6379/0` | ✓ | optional for one API process, **required** for several |

### Code execution and judging

| Variable | Default | Prod | Purpose |
|---|---|:---:|---|
| `PISTON_URL` | `http://127.0.0.1:2000/api/v2/execute` | ✓ | the self-hosted engine |
| `PISTON_MAX_CONCURRENCY` | `16` | | engine calls in flight per API process |
| `JUDGE_WORKERS` | `8` | | concurrent judge jobs per API process |
| `SUBMIT_WAIT_SECONDS` | `20` | | Submit waits this long for a verdict, then answers 202 |

### AI (optional)

| Variable | Default | Purpose |
|---|---|---|
| `CV_MODEL_PATH` | `ai/models/yolo11n.pt` | YOLO weights for server-side phone/person detection (AI build only) |
| `PHONE_CONFIDENCE_THRESHOLD` | `0.45` | phone detection threshold |
| `PERSON_CONFIDENCE_THRESHOLD` | `0.5` | extra-person detection threshold |
| `WHISPER_MODEL_SIZE` | `base` | interview speech-to-text model (`tiny`, `base`, `small`, ...) |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | unset, `gpt-4o-mini` | AI question generation |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | unset, `gemini-2.0-flash` | advisory grade suggestions |

### E-mail (password-reset codes)

| Variable | Default | Purpose |
|---|---|---|
| `ENABLE_EMAILS` | `false` | send e-mails at all |
| `BREVO_API_KEY` or `SENDGRID_API_KEY` | unset | HTTPS providers (tried first) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | unset, `587` | SMTP (a campus relay works without internet) |
| `SMTP_SENDER` | `SMTP_USER` | From address |

### Evidence storage

| Variable | Default | Purpose |
|---|---|---|
| `AWS_BUCKET_NAME`, `AWS_REGION` | unset, `us-east-1` | private S3 bucket (credentials from the IAM role, never keys in config) |
| `EVIDENCE_DIR` | unset | store on the server's disk instead (campus servers); served through signed links |
| `EVIDENCE_URL_TTL_SECONDS` | `900` | lifetime of evidence links |

Neither bucket nor directory set: proctoring events are recorded without images.

### Single sign-on (optional)

`SSO_GOOGLE_CLIENT_ID` / `_SECRET`, `SSO_MICROSOFT_CLIENT_ID` / `_SECRET` / `_TENANT`,
`SSO_OIDC_ISSUER` / `_CLIENT_ID` / `_CLIENT_SECRET` / `_NAME`, `SSO_ALLOWED_DOMAINS`,
`SSO_AUTO_PROVISION`. A provider's button appears only when its client ID is set. Register
`<PUBLIC_API_URL>/api/auth/sso/<google|microsoft|oidc>/callback` with the provider.

### First admin (production)

`ADMIN_EMAIL`, `ADMIN_PASSWORD` (12+ characters): `migrate` / `seed_admin.py` creates this one
administrator if no admin exists.

### Container and operations

| Variable | Default | Purpose |
|---|---|---|
| `WEB_CONCURRENCY` | `2` | uvicorn worker processes per container |
| `GRACEFUL_SHUTDOWN_SECONDS` | `20` | finish requests in flight on `SIGTERM` |
| `RUN_MIGRATIONS_ON_START` | `false` | single-instance hosts only |
| `METRICS_ENABLED` | on in production | CloudWatch Embedded Metric Format lines |
| `METRICS_INTERVAL_SECONDS` | `60` | metric period |
| `WITH_AI` (build argument) | `false` | include PyTorch, YOLO and faster-whisper in the backend image |

### Web app (`NEXT_PUBLIC_*`, compiled in at build time)

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | API origin used by the browser; **a production build fails without it** |
| `NEXT_PUBLIC_SITE_URL` | public site address |
| `NEXT_PUBLIC_ICE_SERVERS` | JSON list of STUN/TURN servers for live interviews |

Changing a `NEXT_PUBLIC_*` value requires rebuilding the web app.

## Secrets

- Never commit real values; keep them in the git-ignored files above or a secret manager.
- Generate secrets randomly: `openssl rand -hex 32` for `SECRET_KEY`.
- Never put a secret in a `NEXT_PUBLIC_*` variable.
- Rotating `SECRET_KEY` signs everyone out and invalidates outstanding evidence links.

---

[Back to README](../README.md) · [Documentation index](README.md)
