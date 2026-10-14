# Deploying ExamSentinel on AWS

Two supported shapes:

| | **A. Managed (recommended)** | **B. Single EC2 host** |
|---|---|---|
| App | ECS Fargate (frontend, backend) | `docker-compose.prod.yml` |
| Database | RDS PostgreSQL 16 | Postgres container (EBS volume) |
| Redis | ElastiCache Redis 7 | Redis container |
| Code runner | Piston on one EC2 instance (privileged) | Piston container |
| Evidence | Private S3 bucket | Private S3 bucket |
| TLS / routing | ALB + ACM | ALB + ACM, or Caddy on the host |
| Good for | real exams, autoscaling, HA | pilots, a single course |

## Architecture (A)

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

Why these pieces:
- **Piston needs `privileged`**, which Fargate doesn't allow — run it on a small EC2 instance
  (or an ECS EC2 capacity provider) in a private subnet. The public emkc.org Piston API is
  whitelist-only since 2026-02-15, so self-hosting is required.
- **Redis** carries WebSocket events between backend tasks; without it, proctors only see events from
  the task their socket landed on. No ALB stickiness is needed.
- **Liveness vs readiness**: `/api/health/live` is process-only (use for ALB/ECS health checks);
  `/api/health` checks DB + Redis and returns 503 when degraded (use for dashboards/alarms).

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
| `ENVIRONMENT` | `production` (startup fails if `DEBUG`, default `SECRET_KEY` or empty CORS) |
| `DEBUG` | `false` (error responses then hide internal details) |
| `CORS_ORIGINS` | `https://exam.example.edu` |
| `PISTON_URL` | `http://piston.internal:2000/api/v2/execute` |
| `AWS_REGION`, `AWS_BUCKET_NAME` | evidence bucket |
| `ADMIN_EMAIL` | first admin, created once by `migrate` |
| `WEB_CONCURRENCY` | uvicorn workers per task (≈ vCPUs) |
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

Scale out by running several Piston instances behind an internal NLB.

## 5. ECS services

| Service | Image | Size (start) | Port | Health check |
|---|---|---|---|---|
| backend | examsentinel-backend | 2 vCPU / 4 GB (with AI) | 8000 | `/api/health/live` |
| frontend | examsentinel-frontend | 0.5 vCPU / 1 GB | 3000 | `/` |

- Backend autoscaling on CPU (target 60%). Each frame analysis is ~50 ms of CPU; one candidate sends
  one frame per 10 s, so a 2-vCPU task handles roughly 200 concurrent webcams.
- ALB target groups: idle timeout **300 s** (live-proctoring WebSockets at `/api/ws/*`).
- Logs: `awslogs` driver → CloudWatch (the backend logs JSON with a correlation ID per request).

### Deploying a new version

1. Push images.
2. Run migrations as a **one-off task** with the backend image and command `["migrate"]`
   (applies Alembic migrations and bootstraps the first admin if none exists).
3. Update the services. Never set `RUN_MIGRATIONS_ON_START=true` with more than one task.
4. Seed or update the practice problem bank when it changes: one-off task with command
   `["python", "seed_practice.py"]` (idempotent).

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

## Post-deploy checks

- `curl https://api.exam.example.edu/api/health` → `"status": "healthy"`.
- Sign in as the bootstrap admin, open **Practice Problems** and run the shield (validate) action on a
  problem: proves backend → Piston works.
- Open **AI Test** (`/admin/ai-test`) with a webcam and hold up a phone: proves the vision model loaded.
- On a **staging** stack seeded with demo users (non-production), run
  `E2E_BASE_URL=https://api.staging… python scripts/e2e_roles_smoke.py`.
