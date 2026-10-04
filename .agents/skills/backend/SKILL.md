---
name: backend-workflow
description: >-
  Standard workflow and guidelines for the FastAPI backend of the ExamSentinel project. Use this when creating API routes, models, or interacting with the database.
---

# Backend Guidelines for ExamSentinel

1. **Framework & Stack**: FastAPI, SQLAlchemy 2.0 (async), Pydantic V2.
2. **Database**: PostgreSQL with `asyncpg`. Use `async_session_maker()` or `Depends(get_db)` for database sessions.
3. **Routers**: Add new routes in `app/api/...` and register them in `app/api/router.py`.
4. **Authentication**: Secure endpoints using `current_user: User = Depends(get_current_user)` or `Depends(require_roles([UserRole.ADMIN]))`.
5. **Enums**: When using Postgres Enums with SQLAlchemy, apply `native_enum=True`.

