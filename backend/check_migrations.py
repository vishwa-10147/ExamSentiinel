"""Fail if a database built by the Alembic migrations differs from the SQLAlchemy models.

Production schemas come only from migrations, while tests and local SQLite use the models
(create_all), so a model change without a matching migration passes every test and then breaks
in production. Run against an empty PostgreSQL database after `alembic upgrade head`:

    DATABASE_URL=postgresql+asyncpg://... python -m alembic upgrade head
    DATABASE_URL=postgresql+asyncpg://... python check_migrations.py

Exit code 0: no differences. 1: differences (printed).
"""

import asyncio
import sys

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine

from app import models  # noqa: F401  (registers every model on Base.metadata)
from app.core.config import settings
from app.core.database import Base

# Tables that exist only on the database side by design.
IGNORED_TABLES = {"alembic_version"}


def _include_object(obj, name, type_, reflected, compare_to):
    return not (type_ == "table" and name in IGNORED_TABLES)


def _diff(connection) -> list:
    context = MigrationContext.configure(
        connection,
        opts={"compare_type": True, "compare_server_default": False, "include_object": _include_object},
    )
    return compare_metadata(context, Base.metadata)


async def main() -> int:
    if not settings.DATABASE_URL.startswith("postgresql"):
        print("Point DATABASE_URL at a PostgreSQL database migrated with `alembic upgrade head`.")
        return 2
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        differences = await connection.run_sync(_diff)
    await engine.dispose()
    if not differences:
        print("Migrations match the models.")
        return 0
    print(f"{len(differences)} difference(s) between the migrated database and the models:")
    for item in differences:
        print(f"  {item}")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
