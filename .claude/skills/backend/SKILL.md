---
name: backend
description: Conventions for changing the ExamSentinel FastAPI backend — adding routes, models, migrations, roles, settings and Redis usage. Use before adding or modifying anything under backend/app.
allowed-tools: Bash, Read, Edit
---

# Backend conventions

## Adding an endpoint

1. Put it in the matching module in `backend/app/api/` (or a new module registered in `api/router.py`;
   everything is mounted under `/api`). Mind aliases: `proctoring` is mounted at both `/proctoring`
   and `/telemetry`, `sessions` at `/exam/sessions` and `/sessions`.
2. Auth: `Depends(get_current_user)`; staff-only: `Depends(require_roles([UserRole.ADMIN, …]))`.
   Candidates may only touch their own sessions — check `session.candidate_id == current_user.id`.
3. Request/response models in `backend/app/schemas/`. Use `status.HTTP_422_UNPROCESSABLE_CONTENT`
   (the `_ENTITY` constant is deprecated).
4. Static path segments must not be shadowed by a parameter route (`/risk/weights` vs
   `/risk/{session_id}` — use `{session_id:uuid}`).
5. Audit sensitive actions with `log_audit_event(...)`.
6. Then check the frontend actually calls the path with the same method (see `/frontend`).

## Models and migrations

- Models in `backend/app/models/`, imported in `models/__init__.py` (SQLite dev mode creates tables
  from `Base.metadata` on startup).
- **Every model change needs an Alembic migration** in `backend/alembic/versions/` chained to the
  current head. Guard Postgres-only SQL (`ALTER TYPE …`) with
  `op.get_bind().dialect.name == "postgresql"`.
- Enums use `values_callable=lambda obj: [e.value for e in obj]`.

## Settings, secrets, services

- Typed settings in `app/core/config.py`; `backend/.env` is also loaded into `os.environ` for services
  that call `os.getenv`. Production refuses to start with `DEBUG`, the default `SECRET_KEY`, or empty CORS.
- Never return raw exception text to clients outside DEBUG (see the middleware in `app/main.py`).
- Redis is optional everywhere: check `redis_breaker.is_open` before calling, `trip()` on failure.
- CPU-heavy work (vision, image decoding) goes through `asyncio.to_thread`.
- Code execution only via `sandbox_service` (self-hosted Piston); evidence only via `storage_service`
  (private S3 + presigned URLs; never store or return public object URLs).

## Verify

`/backend-tests`, then `python scripts/e2e_roles_smoke.py` against the running server.
