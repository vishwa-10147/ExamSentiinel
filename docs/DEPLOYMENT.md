# Deployment

How to choose where ExamSentinel runs, what every production deployment needs, and how to roll
back or recover. The step-by-step guides are:

- [Campus server](../deploy/campus/README.md) - one Linux server with Docker
- [AWS](AWS_DEPLOYMENT.md) - ECS Fargate, RDS, ElastiCache, S3, and EC2 for the code engine

## Contents

- [Choosing a target](#choosing-a-target)
- [What every deployment needs](#what-every-deployment-needs)
- [Releasing a new version](#releasing-a-new-version)
- [Rollback](#rollback)
- [Disaster recovery](#disaster-recovery)
- [What has been verified](#what-has-been-verified)

## Choosing a target

| | Campus server | AWS |
|---|---|---|
| Best for | one college; exams run in its own labs | several institutions, remote candidates, high availability |
| Hardware | one Linux server (8 cores / 16 GB / 100 GB SSD for about 500 concurrent students) | managed services; see the AWS guide for sizes |
| Internet during exams | not needed | needed by every candidate |
| Single point of failure | yes, the server | no (several API tasks, Multi-AZ database if chosen) |
| Backups | nightly `pg_dump` to disk; copy off the server yourself | RDS automated backups and snapshots |
| Webcam evidence | the server's disk (`EVIDENCE_DIR`) | private S3 bucket |
| Effort | `sh setup.sh <host-name> <admin-email>` | infrastructure set up by hand following the guide |

The Docker Compose stack in [Setup](../SETUP.md#option-c-the-whole-stack-in-docker) is for
evaluation only: it serves plain HTTP and uses development defaults.

## What every deployment needs

- **HTTPS.** Browsers allow the webcam and microphone only on secure pages. TLS ends at the front
  door (nginx on the campus server, the load balancer on AWS), which also redirects HTTP to HTTPS.
- **`ENVIRONMENT=production`.** The API then refuses to start with unsafe settings (debug mode, a
  default secret key, SQLite, non-HTTPS origins, a wildcard proxy trust); see
  [Configuration](CONFIGURATION.md#development-vs-production).
- **PostgreSQL 16** with the Alembic migrations applied (`migrate` command of the backend image).
- **Redis** whenever more than one API process runs (the campus server runs 4 worker processes,
  so it always includes Redis).
- **The self-hosted code engine** (Piston), reachable only from the API. It runs privileged to
  isolate programs, so keep it on a dedicated host or container with no secrets and no public port.
- **The web app built with `NEXT_PUBLIC_API_URL`** pointing at the public API address; the build
  fails without it.

## Releasing a new version

1. Merge to `main` with CI green (backend tests, frontend checks, migration check, Docker builds).
2. Deploy outside exam hours.
3. Campus server: `git pull && sh deploy/campus/update.sh` - backs up, rebuilds, migrates,
   restarts (about a minute of downtime) and reloads the problem bank. It stops before restarting
   if a migration cannot apply.
4. AWS: push images, run the `migrate` one-off task, then update the services (rolling, no
   downtime); see [Deploying a new version](AWS_DEPLOYMENT.md#deploying-a-new-version).
5. Check `/api/health` and run the [post-deployment checks](AWS_DEPLOYMENT.md#post-deployment-checks).

## Rollback

Application code and database schema are rolled back separately.

**Code only (the release added no migration):**

- Campus: `git checkout <previous-commit-or-tag>` in the repository, then `sh deploy/campus/update.sh`.
- AWS: update the ECS services to the previous task-definition revision.

**The release added a migration:** CI checks only that the latest migration downgrades on an
empty database, not on real data, so do not rely on `alembic downgrade` in production. Restore
the backup taken before the update instead:

- Campus: `update.sh` takes a backup first. Check out the previous version, rebuild with
  `docker compose build`, then `sh deploy/campus/restore.sh backups/<the dump taken before the update>`
  (it asks for confirmation and saves the current data before replacing it).
- AWS: restore the RDS snapshot taken before the migration to a new instance, point
  `DATABASE_URL` at it, and deploy the previous task-definition revision.

Answers and submissions recorded after the backup are lost by a restore, so roll back as soon as
a problem is found and never during an exam.

## Disaster recovery

| Lost | Campus server | AWS |
|---|---|---|
| A container | restarts automatically (`restart: unless-stopped`) | ECS replaces the task |
| The code engine | `docker compose up -d engine`; runtimes survive in their volume | replace the EC2 instance and reinstall runtimes (`scripts/install_piston_runtimes.py`) |
| The database | `restore.sh` from the latest dump | restore an RDS snapshot or point in time |
| The whole server | new server: `setup.sh`, then `restore.sh` with the off-server copy of `backups/`, and copy back `data/evidence/` | not applicable |
| `SECRET_KEY` leaked | change it in `.env` and restart: everyone is signed out and evidence links expire | rotate it in Secrets Manager and redeploy |

A backup that has never been restored is not a backup: rehearse a restore on a spare machine
before the first exam.

## What has been verified

On 2026-10-16, on a Windows 11 workstation with Docker Desktop:

- The campus kit: `setup.sh`, the nightly-backup container, a backup and restore drill, and
  `update.sh`, followed by the browser test suite against the HTTPS stack.
- The AWS topology rehearsed locally (`deploy/rehearsal/`: nginx as the load balancer, two API
  replicas, PostgreSQL, Redis, the engine), including a replica restart during a 250-student
  submission rush with nothing lost.

Neither has yet been run on a real campus server or a real AWS account. Details:
[Production readiness](PRODUCTION_READINESS.md).

---

[Back to README](../README.md) · [Documentation index](README.md)
