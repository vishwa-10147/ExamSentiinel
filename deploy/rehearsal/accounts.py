"""Rehearsal only: staff and candidate accounts for the role journeys and checks.

The first admin comes from `migrate` (ADMIN_EMAIL / ADMIN_PASSWORD), exactly as in production.
This adds a proctor, a reviewer and a candidate with the same rehearsal password. Never run it
against a real deployment. Usage (from deploy/rehearsal):

    docker compose exec -T backend python - < accounts.py
"""

import asyncio
import os

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.user import User, UserRole

ACCOUNTS = [
    ("proctor@sentinel.edu", "Chief Proctor", UserRole.PROCTOR),
    ("reviewer@sentinel.edu", "Senior Reviewer", UserRole.REVIEWER),
    ("candidate@sentinel.edu", "Test Candidate", UserRole.CANDIDATE),
]


async def main() -> None:
    password = os.environ["ADMIN_PASSWORD"]
    async with async_session_maker() as db:
        for email, name, role in ACCOUNTS:
            if (await db.execute(select(User.id).where(User.email == email))).scalar_one_or_none():
                print(f"exists: {email}")
                continue
            db.add(User(email=email, full_name=name, role=role, is_active=True, hashed_password=get_password_hash(password)))
            print(f"created: {email}")
        await db.commit()


asyncio.run(main())
