---
name: aws-deploy
description: Build, configure and deploy ExamSentinel to AWS (ECS Fargate + RDS + ElastiCache + S3 + Piston on EC2, or a single EC2 host with docker-compose.prod.yml). Use when preparing a release, changing Dockerfiles/infra, or debugging a deployed environment.
disable-model-invocation: true
argument-hint: "[managed|single-host]"
allowed-tools: Bash, Read
---

# AWS deploy

Full guide: `docs/AWS_DEPLOYMENT.md`. This skill is the release checklist.

## Before building

1. Backend suite green and E2E green locally (`/backend-tests`).
2. `cd frontend && npm run build` succeeds.
3. New migrations chain from the current head (`ls backend/alembic/versions`).

## Images

```bash
docker build -t examsentinel-backend:$TAG --build-arg WITH_AI=true backend
docker build -t examsentinel-frontend:$TAG \
  --build-arg NEXT_PUBLIC_API_URL=https://api.<domain> --build-arg NEXT_PUBLIC_SITE_URL=https://<domain> frontend
docker build -t examsentinel-piston:$TAG infra/piston
```
Sanity check the backend image has no local secrets:
`docker run --rm --entrypoint sh examsentinel-backend:$TAG -c 'test ! -e .env && test ! -e examsentinel_dev.db && echo clean'`

## Release order

1. Push images to ECR.
2. One-off task: backend image, command `["migrate"]`.
3. If problems changed: one-off task `["python", "seed_practice.py"]`.
4. Update ECS services (frontend, backend). Piston only when `infra/piston` changed.
5. Post-deploy: `/api/health` healthy, validate one practice problem (backend → Piston), AI Test page
   with a phone (vision model loaded).

## Never

- Never run more than one backend task with `RUN_MIGRATIONS_ON_START=true`.
- Never put AWS keys in env: the ECS task role grants S3 access.
- Never make the evidence bucket public or store public object URLs — presigned GETs only.
- Never point `PISTON_URL` at emkc.org (whitelist-only since 2026-02-15).
- Never seed demo users in production (`seed_admin.py` refuses; it bootstraps one admin from
  `ADMIN_EMAIL`/`ADMIN_PASSWORD` instead).
