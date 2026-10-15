# Production Readiness

Where ExamSentinel stands before its first AWS deployment: what has been verified, and with what
evidence; what the operator still has to do; and the limitations to know about. The deployment
steps themselves are in [AWS deployment](AWS_DEPLOYMENT.md).

## Contents

- [Summary](#summary)
- [Rehearsal results](#rehearsal-results)
- [Problems the rehearsal found](#problems-the-rehearsal-found)
- [Operator checklist](#operator-checklist)
- [Known limitations](#known-limitations)

## Summary

The application side is ready for a staging deployment: the production images build, start
only with safe settings, run as several replicas behind a load balancer, survive rolling
restarts under load without losing work, and pass every functional, browser and security check
against the production build. **Not yet done** (they need an AWS account or real people, so no
local rehearsal can do them): the AWS resources themselves, a backup restore drill, alarms,
e-mail delivery, a TURN server, an external security review and a pilot on real student devices.
See the [operator checklist](#operator-checklist).

## Rehearsal results

`deploy/rehearsal/` runs the production images (`ENVIRONMENT=production`, `DEBUG=false`) in the
AWS topology on one machine: an nginx "ALB" terminating TLS and routing by host name, two API
replicas with two uvicorn workers each, PostgreSQL 16, Redis 7, and the code engine. Results from
2026-10-15 (Windows 11, Docker Desktop):

| Check | Result |
|---|---|
| Images build (`backend` without AI, `frontend` with the production API URL) | Built; frontend 272 MB, backend 1.04 GB |
| Release steps: `migrate` one-off task, first admin from `ADMIN_EMAIL`, problem bank seeded through the engine | Done; 127 problems seeded in 22 s |
| `/api/health` through the load balancer | `healthy`: database, Redis, code engine, judge queue |
| End-to-end role journeys (`scripts/e2e_roles_smoke.py`) | **73 / 73** |
| Several processes (`scripts/multi_process_check.py`): interview signalling, live monitoring and run slots across replicas | **11 / 11**; requests spread over both replicas |
| Browser suite on the production build over TLS (`npx playwright test --workers=1`) | **29 / 29**, including the production checks below |
| Content-Security-Policy: no violations on the problem, contest, progress, playground and exam pages; no request leaves the app or its API | Passed (`tests/production.spec.ts`); a probe confirmed the policy blocks third-party scripts and connections |
| Exam page loads the self-hosted face model and starts the (fake) camera | Passed |
| Forged `X-Forwarded-For` / `X-Real-IP` / `CF-Connecting-IP` on every password guess | Throttled after 5 guesses; the real address is logged |
| 250 students sign in and submit at the same moment, with one API replica restarted in the middle of judging | **250 / 250 accepted, 0 errors**, p95 7.6 s to verdict, ~31 verdicts/s; no submission judged twice; no 5xx at the load balancer |
| Session tokens in logs | None (redacted) |
| Migrations vs models (`backend/check_migrations.py`) | Identical schema; also in CI |

## Problems the rehearsal found

Each was invisible in development (SQLite, one process, no proxy) and is now fixed and covered
by a test:

| Problem | Impact in production | Fix |
|---|---|---|
| `CORS_ORIGINS=https://…` — the documented format — crashed start-up (the settings library JSON-decoded the value) | Backend would not start | Plain and JSON lists both accepted (`NoDecode`); `test_cors_origins_from_the_environment` |
| Client IP taken from headers the client sends (`X-Real-IP`, the first `X-Forwarded-For` entry, …), and uvicorn trusted every proxy (`--forwarded-allow-ips="*"`) | Per-IP sign-in limits and the password-guessing throttle could be bypassed by sending a new fake address each time | Only `request.client` as resolved by uvicorn from `FORWARDED_ALLOW_IPS`; production refuses `*`; plus a per-account limit (30 failures / 15 min) that ignores IPs entirely |
| The progress page imported the problem bank (5.8 s of CPU) inside a request | The first progress page on every API process froze all its requests — exam submissions and live WebSockets included — for ~6 s, after every deploy or scale-out | Topics moved to `app/core/practice_topics.py`; a test asserts the API never imports the bank |
| Connection pool 10 + 20 per process; judge workers kept a connection while the engine ran | With two tasks × two workers, PostgreSQL ran out of connections under a sign-in rush (48 of 250 sign-ins failed with 500) | Pool 5 + 5 per process; judging releases its connection while code runs; a saturated database answers 503 with `Retry-After`. 250 / 250 afterwards |
| The editor (Monaco) and face model loaded from jsDelivr and tfhub.dev at exam time | An exam network blocking either host would break the editor or proctoring mid-exam; no strict CSP possible | Both served by the app; strict CSP |
| `render.yaml` set `ENVIRONMENT=production` without `DEBUG=false` | That deployment would refuse to start | Fixed |

## Operator checklist

Do these, in order, on AWS. Each links to the relevant guide section.

**Infrastructure** ([AWS deployment](AWS_DEPLOYMENT.md))
- [ ] VPC with private subnets; ALB with an ACM certificate; Route 53 records for the web app and API.
- [ ] RDS PostgreSQL 16, Multi-AZ, encrypted, **automated backups and point-in-time recovery on**.
- [ ] ElastiCache Redis 7 with in-transit encryption (required with more than one backend task).
- [ ] Piston on its own EC2 instance: private subnet, inbound 2000 only from the backend security group, no IAM permissions; run `test_sandbox_engine.py` against it.
- [ ] Private S3 evidence bucket with a lifecycle rule matching your retention policy.
- [ ] Secrets in Secrets Manager (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `ADMIN_PASSWORD`, mail and SSO secrets).

**Settings**
- [ ] `FORWARDED_ALLOW_IPS` = the ALB subnets' CIDRs; then send a forged `X-Forwarded-For` and confirm CloudWatch logs your real address.
- [ ] Pool sizing: tasks × `WEB_CONCURRENCY` × (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`) + 10 < RDS `max_connections`.
- [ ] ECS `stopTimeout` ≥ 30 s; backend target group deregistration delay 30 s; ALB idle timeout 300 s.
- [ ] E-mail provider configured (`RESEND_API_KEY`, `BREVO_API_KEY`, `SENDGRID_API_KEY` or SMTP) and a password-reset e-mail actually received.
- [ ] TURN server for live interviews (`NEXT_PUBLIC_ICE_SERVERS`) if interviews are used.

**Operations**
- [ ] CloudWatch alarms: `/api/health` not `healthy`; `code_engine` unhealthy; `judge_queue.details.oldest_pending_seconds` > 120; ALB 5xx rate; RDS CPU and `DatabaseConnections`; ECS CPU.
- [ ] **Restore drill**: restore an RDS snapshot (or point in time) into a new instance, point a staging task at it, sign in and open a past result. Record how long it took.
- [ ] Staging: run the [post-deployment checks](AWS_DEPLOYMENT.md#post-deployment-checks) and a load test sized to your largest exam (`scripts/load_test.py`).

**People and policy**
- [ ] External security review / penetration test of the staging stack.
- [ ] Pilot on real student laptops, browsers and webcams with a low-stakes exam; review false positives before relying on proctoring signals (they are advisory; reviewers decide).
- [ ] Privacy notice, consent wording and data-retention periods for webcam evidence and interview recordings approved by your institution.

## Known limitations

- **Backend image size.** 1.04 GB without the AI extras (OpenCV and friends), ~1.5 GB with them; deploys pull it on every new task. A slimmer image is possible by splitting optional dependencies.
- **CSP allows inline scripts** (`'unsafe-inline'`), which Next.js' inline bootstrap needs. A nonce-based policy would require rendering every page dynamically. All other sources are restricted to the app and its API.
- **Sign-in is CPU-bound** (bcrypt): 250 simultaneous sign-ins took p95 2.4 s on four API processes. Scale tasks before large exams, or stagger entry.
- **The code engine runs privileged** (Piston needs it to create sandboxes). It must stay on its own host with no secrets; see [Security](SECURITY.md#deployment-requirements-and-residual-risk).
- **Bank checkers run in the API process.** They come only from the repository (the admin API cannot set them), so they are reviewed code, not user input.
- **Load balancer stand-in.** The rehearsal uses nginx where AWS uses an ALB; TLS termination, host routing, WebSockets and `X-Forwarded-For` behave the same, but ALB-specific settings (idle timeout, deregistration delay) are only exercised on AWS.

---

[Back to README](../README.md) · [Documentation index](README.md)
