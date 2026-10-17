# AWS Deployment

ExamSentinel supports two production topologies on AWS:

| | **A. Managed (recommended)** | **B. Single EC2 host** |
|---|---|---|
| App | ECS Fargate (frontend, backend) | `docker-compose.prod.yml` |
| Database | RDS PostgreSQL 16 | Postgres container (EBS volume) |
| Redis | ElastiCache Redis 7 | Redis container |
| Code runner | Piston on one EC2 instance (privileged) | Piston container |
| Evidence | Private S3 bucket | Private S3 bucket |
| TLS / routing | ALB + ACM | ALB + ACM, or Caddy on the host |
| Good for | real exams, autoscaling, HA | pilots, a single course |

## Contents

- [Before the first deployment](#before-the-first-deployment)
- [Option A architecture](#option-a-architecture)
- [1. Build and push images (ECR)](#1-build-and-push-images-ecr)
- [2. Data stores](#2-data-stores)
- [3. Secrets and configuration](#3-secrets-and-configuration)
- [4. Code runner (Piston on EC2)](#4-code-runner-piston-on-ec2)
- [5. Single sign-on, interviews and speech-to-text](#5-single-sign-on-interviews-and-speech-to-text)
- [6. ECS services](#6-ecs-services)
- [Metrics and alarms](#metrics-and-alarms)
- [Option B: single EC2 host](#option-b-single-ec2-host)
- [Post-deployment checks](#post-deployment-checks)

## Before the first deployment

Rehearse on one machine first: `deploy/rehearsal/` runs the production images with
`ENVIRONMENT=production` in this topology (two API replicas behind a TLS load balancer,
PostgreSQL, Redis, the code engine) and every check below runs against it. See
[Production readiness](PRODUCTION_READINESS.md) for what the rehearsal verified and what remains
for the operator.

## Option A architecture

```
                 Route 53 ─► ALB :443 (ACM cert, idle timeout 300 s for WebSockets)
                               ├─ exam.example.edu  ─► TG frontend :3000   (ECS Fargate)
                               └─ api.exam.example.edu ─► TG backend :8000 (ECS Fargate)
                                                              │  health: /api/health/live
                 private subnets                              ▼
   RDS PostgreSQL ◄── backend tasks ──► ElastiCache Redis (pub/sub fan-out for live proctoring)
                          │   │
                          │   └──► S3 evidence bucket (private, SSE, presigned GETs)
                          └──► Piston EC2 :2000 (security group: backend SG only)
```

Add an ALB listener on port **80** whose only action is a permanent redirect to HTTPS (443).
The web app does not redirect by itself: whatever terminates TLS is responsible for it.

Why these pieces:
- **Piston needs `privileged`**, which Fargate doesn't allow — run it on a small EC2 instance
  (or an ECS EC2 capacity provider) in a private subnet. The public emkc.org Piston API is
  whitelist-only since 2026-02-15, so self-hosting is required.
- **Redis is required with more than one backend task.** It carries live-proctoring events and
  interview signalling between tasks, and holds the shared state that must agree across tasks:
  rate-limit windows, one-run-per-student slots, password-reset codes and SSO tickets. Without it
  each task falls back to its own memory, which is only correct for a single task. No ALB
  stickiness is needed. Verify a multi-task setup with `scripts/multi_process_check.py`.
- **Liveness vs readiness**: `/api/health/live` is process-only (use for ALB/ECS health checks).
  `/api/health` reports the database, Redis, the code engine and the judging backlog (pending
  submissions and the age of the oldest); it returns 503 only when the database is down and
  `degraded` otherwise. Alarm on `degraded`, on `code_engine` unhealthy, and on
  `judge_queue.details.oldest_pending_seconds` above a few minutes.

## 1. Build and push images (ECR)

```bash
aws ecr create-repository --repository-name examsentinel-backend
aws ecr create-repository --repository-name examsentinel-frontend
aws ecr create-repository --repository-name examsentinel-piston
aws ecr get-login-password | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com

docker build -t $ECR/examsentinel-backend:$TAG --build-arg WITH_AI=true backend
docker build -t $ECR/examsentinel-frontend:$TAG \
  --build-arg NEXT_PUBLIC_API_URL=https://api.exam.example.edu \
  --build-arg NEXT_PUBLIC_SITE_URL=https://exam.example.edu frontend
docker build -t $ECR/examsentinel-piston:$TAG infra/piston
docker push $ECR/examsentinel-backend:$TAG   # …and the other two
```

`NEXT_PUBLIC_*` values are compiled into the frontend bundle: rebuild the frontend image when the API
URL changes. `WITH_AI=true` adds CPU PyTorch + ultralytics and bakes in the YOLO weights
(≈ 1.5 GB image); with `false` the API still runs and reports phone detection as unavailable.

## 2. Data stores

- **RDS PostgreSQL 16**, private subnets, encrypted, automated backups (Multi-AZ for production).
  `DATABASE_URL=postgresql+asyncpg://USER:PASS@ENDPOINT:5432/examsentinel`
- **ElastiCache Redis 7**, in-transit encryption on: `REDIS_URL=rediss://ENDPOINT:6379/0`
- **S3 bucket** for evidence: Block Public Access **on**, default encryption SSE-S3, and a lifecycle
  rule matching your retention policy (e.g. expire `evidence/` after 180 days).

## 3. Secrets and configuration

Store in **Secrets Manager** and reference from the task definitions:
`SECRET_KEY` (`openssl rand -hex 32`), `DATABASE_URL`, `REDIS_URL`, `ADMIN_PASSWORD`,
and optionally `OPENAI_API_KEY`, `GEMINI_API_KEY`, `SMTP_PASSWORD`.

Plain environment variables:

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production`. Start-up refuses unsafe settings and lists all of them: `DEBUG` on, a default or short `SECRET_KEY`, a CORS origin that is not public `https://`, SQLite or the development database URL, `COOKIE_SECURE=false`, `FORWARDED_ALLOW_IPS="*"`, the public emkc.org engine |
| `DEBUG` | `false` (error responses then hide internal details; `/docs` is off) |
| `CORS_ORIGINS` | `https://exam.example.edu` (comma-separated for several) |
| `FORWARDED_ALLOW_IPS` | the **ALB subnets' CIDRs**, e.g. `10.0.0.0/24,10.0.1.0/24`. Only these proxies' `X-Forwarded-For` identifies the client; per-IP sign-in limits depend on it. Never `*` |
| `CLIENT_IP_HEADER` | leave empty behind an ALB |
| `PISTON_URL` | `http://piston.internal:2000/api/v2/execute` |
| `AWS_REGION`, `AWS_BUCKET_NAME` | evidence bucket |
| `ADMIN_EMAIL` | first admin, created once by `migrate` |
| `WEB_CONCURRENCY` | uvicorn workers per task (≈ vCPUs) |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | per worker process, default 5 + 5. Keep **tasks × `WEB_CONCURRENCY` × (pool + overflow)** plus ~10 for migrations and tools below RDS `max_connections` (about 110 on `db.t4g.micro`, 225 on `db.t4g.small`, 450 on `db.t4g.medium`; check `SHOW max_connections`). When the database is saturated the API answers 503 with `Retry-After`, not 500 |
| `GRACEFUL_SHUTDOWN_SECONDS` | default 20; keep below the ECS `stopTimeout` (default 30 s) |
| `PHONE_CONFIDENCE_THRESHOLD` | optional, default `0.45` |

No AWS access keys: the **task role** grants S3 access.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject", "s3:GetObject"],
    "Resource": "arn:aws:s3:::YOUR-EVIDENCE-BUCKET/evidence/*"
  }]
}
```

## 4. Code runner (Piston on EC2)

1. Launch a small instance (e.g. `t3.medium`, Amazon Linux 2023, Docker installed) in a private
   subnet. Security group: inbound TCP 2000 **only** from the backend tasks' security group.
2. Run the image with a persistent volume:
   ```bash
   docker run -d --name piston --restart always --privileged -p 2000:2000 \
     -e PISTON_RUN_TIMEOUT=10000 -e PISTON_COMPILE_TIMEOUT=15000 \
     -e PISTON_OUTPUT_MAX_SIZE=8388608 -e PISTON_RUN_MEMORY_LIMIT=268435456 \
     -v piston_packages:/piston/packages \
     --tmpfs /piston/jobs:exec,uid=1000,gid=1000,mode=711 --tmpfs /tmp:exec \
     $ECR/examsentinel-piston:$TAG
   ```
3. Install runtimes once (they persist in the volume):
   `python scripts/install_piston_runtimes.py --url http://PISTON_PRIVATE_IP:2000`
4. Register it in Cloud Map (or use its private DNS) and set `PISTON_URL` on the backend.

**Capacity.** In load tests one API process with one Piston instance judged 500 simultaneous
submissions (a 7-test Python problem) with every verdict within 15 s, at about 33 verdicts/s;
the Piston instance alone sustains about 75 judge runs/s, so the API process saturates first.
Scale out ECS backend tasks first; add Piston instances behind an internal NLB when the
combined judge rate of the tasks approaches ~75/s per instance. Rehearse your largest exam
with `scripts/load_test.py` against a staging stack.

Related settings on the API: `JUDGE_WORKERS` (concurrent judge jobs per API process, default
8), `PISTON_MAX_CONCURRENCY` (engine calls per process, default 16), `SUBMIT_WAIT_SECONDS`
(how long Submit waits before answering 202, default 20), `DB_POOL_SIZE` / `DB_MAX_OVERFLOW`
(per process; keep the total across tasks below RDS `max_connections`), and
`LOGIN_RATE_LIMIT_PER_IP` (default 300/min, sized for an exam lab behind one NAT address).

Security notes for the code runner (details and the tests behind them: [SECURITY.md](SECURITY.md)):

- Give the Piston instance **no IAM role** (or one with no permissions) and no application
  secrets; it only needs the runtimes volume.
- Allow inbound 2000/tcp **only** from the backend security group; it needs no inbound
  internet and no outbound access at all after runtimes are installed.
- Do not mount the Docker socket into any container.
- After deploying, run `backend/tests/test_sandbox_engine.py` against it
  (`PISTON_URL=http://PISTON_PRIVATE_IP:2000/api/v2/execute`) to confirm network isolation
  and limits on that host.

## 5. Single sign-on, interviews and speech-to-text

- **SSO (OpenID Connect)**: set the `SSO_*` variables (see `.env.production.example`), `PUBLIC_API_URL` and
  `FRONTEND_URL`, and register `https://api.<domain>/api/auth/sso/<google|microsoft|oidc>/callback` as the redirect
  URI with the provider. Put client secrets in Secrets Manager.
- **Live interviews**: video is peer-to-peer WebRTC. Add a **TURN server** for candidates behind strict NATs or
  firewalls (e.g. coturn on a small EC2 instance, or a managed TURN service) and pass it to the frontend build as
  `NEXT_PUBLIC_ICE_SERVERS='[{"urls":"turn:turn.<domain>:3478","username":"…","credential":"…"},{"urls":"stun:stun.l.google.com:19302"}]'`.
  Signalling rooms are shared through Redis, so the two participants may connect to different backend tasks.
- **Speech-to-text** (`WITH_AI=true` image): faster-whisper downloads its model (`WHISPER_MODEL_SIZE`, default
  `base`, ~140 MB) on first use into `~/.cache/huggingface`. Mount an EFS volume there (or bake the model into the
  image) so new tasks don't re-download it. A 12-second clip takes about 1 s of CPU.

## 6. ECS services

| Service | Image | Size (start) | Port | Health check |
|---|---|---|---|---|
| backend | examsentinel-backend | 2 vCPU / 4 GB (with AI) | 8000 | `/api/health/live` |
| frontend | examsentinel-frontend | 0.5 vCPU / 1 GB | 3000 | `/` |

- Backend autoscaling on CPU (target 60%). Each frame analysis is ~50 ms of CPU; one candidate sends
  one frame per 10 s, so a 2-vCPU task handles roughly 200 concurrent webcams.
- ALB target groups: idle timeout **300 s** (live-proctoring WebSockets at `/api/ws/*`);
  deregistration delay **30 s** for the backend (requests in flight finish; the default 300 s only
  slows deploys).
- Rolling deploys: minimum healthy 100 %, maximum 200 %. On `SIGTERM` a task stops accepting
  connections, finishes requests in flight for up to `GRACEFUL_SHUTDOWN_SECONDS`, and hands any
  submission it was still judging back to the queue for another task. Verified in the rehearsal:
  a replica restarted in the middle of a 250-student submission rush lost nothing.
- Logs: `awslogs` driver → CloudWatch (the backend logs JSON with a correlation ID per request).

### Deploying a new version

1. Push images.
2. Run migrations as a **one-off task** with the backend image and command `["migrate"]`
   (applies Alembic migrations and bootstraps the first admin if none exists). CI checks that
   the migrations build exactly the schema the models describe (`backend/check_migrations.py`).
   Migration 017 adds one-session-per-(exam, candidate); if an older database holds duplicate
   sessions it stops and lists them rather than deleting a student's answers - keep one per
   pair (normally the one with answers) and run it again.
3. Update the services. Never set `RUN_MIGRATIONS_ON_START=true` with more than one task.
4. Seed or update the practice problem bank when it changes: one-off task with command
   `["python", "seed_practice.py"]` (idempotent).

## Metrics and alarms

With `ENVIRONMENT=production` every API worker writes one CloudWatch **Embedded Metric Format**
line per minute to its log (`METRICS_ENABLED` overrides; `METRICS_INTERVAL_SECONDS` sets the
period). With the `awslogs` driver CloudWatch turns these into metrics in the namespace
**`ExamSentinel`** (dimension `Service=api`) with no agent; counts are summed across tasks.

| Metric | Meaning | Suggested alarm |
|---|---|---|
| `Requests`, `Responses4xx`, `Responses5xx` | Requests per minute and error responses | `Responses5xx` > 5 for 3 minutes |
| `DatabaseBusy` | 503s because the database had no free connection | > 0 for 3 minutes: raise RDS size or lower pool sizes |
| `RateLimited` | 429 responses | Watch during exams: a lab behind one address may need a higher `LOGIN_RATE_LIMIT_PER_IP` |
| `LatencyP50`, `LatencyP95`, `LatencyP99`, `LatencyMax` | Request latency (ms, per process) | `LatencyP95` > 2000 for 5 minutes |
| `SubmissionsQueued` | Submits answered 202 (judging took longer than 20 s) | Sustained > 0: add tasks or engine capacity |
| `Verdicts`, `JudgeSystemErrors`, `JudgeSecondsP95` | Judging volume, engine failures, time per job | `JudgeSystemErrors` > 0 for 3 minutes |
| `JudgeBacklog`, `JudgeOldestPendingSeconds` | Submissions waiting to be judged | `JudgeOldestPendingSeconds` > 120 |

## Option B: single EC2 host

```bash
cp .env.production.example .env.production   # fill in; git-ignored
docker compose -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm migrate
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
python scripts/install_piston_runtimes.py
```
Ports are bound to `127.0.0.1`; put an ALB (or Caddy/nginx with TLS) in front and expose only 443.
Use an instance with ≥ 4 vCPU / 8 GB (e.g. `t3.xlarge`) when `WITH_AI=true`.

## Post-deployment checks

- `curl https://api.exam.example.edu/api/health` → `"status": "healthy"`.
- Sign in as the bootstrap admin, open **Practice Problems** and run the shield (validate) action on a
  problem: proves backend → Piston works.
- Open **AI Test** (`/admin/ai-test`) with a webcam and hold up a phone: proves the vision model loaded.
- On a **staging** stack (never production: these create test data), run
  `E2E_BASE_URL=https://api.staging… python scripts/e2e_roles_smoke.py`,
  `python scripts/multi_process_check.py --a https://api.staging… --b https://api.staging…`
  and the browser checks of the production build
  (`PLAYWRIGHT_BASE_URL=https://staging… npx playwright test tests/production.spec.ts`).
- Send a request with a forged `X-Forwarded-For` and confirm the API logs your real address
  (`client_ip` in CloudWatch): proves `FORWARDED_ALLOW_IPS` is right.

---

[Back to README](../README.md) · [Documentation index](README.md)
