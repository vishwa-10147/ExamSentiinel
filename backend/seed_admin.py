import asyncio
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from sqlalchemy import select


async def bootstrap_production_admin():
    """Production: create a single admin from ADMIN_EMAIL / ADMIN_PASSWORD, once.

    Demo accounts with a published password are never created in production.
    """
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    async with async_session_maker() as db:
        if (await db.execute(select(User.id).where(User.role == UserRole.ADMIN).limit(1))).scalar_one_or_none():
            print("An admin already exists; nothing to do.")
            return
        if not email or len(password) < 12:
            print("No admin exists. Set ADMIN_EMAIL and ADMIN_PASSWORD (12+ characters) and run again.")
            sys.exit(1)
        db.add(User(email=email, hashed_password=get_password_hash(password), full_name="Administrator",
                    role=UserRole.ADMIN, is_active=True))
        await db.commit()
        print(f"Created initial admin: {email}")


async def seed():
    default_users = [
        {"email": "admin@sentinel.edu", "name": "System Admin", "role": UserRole.ADMIN},
        {"email": "proctor@sentinel.edu", "name": "Chief Proctor", "role": UserRole.PROCTOR},
        {"email": "reviewer@sentinel.edu", "name": "Senior Reviewer", "role": UserRole.REVIEWER},
        {"email": "candidate@sentinel.edu", "name": "Test Candidate", "role": UserRole.CANDIDATE},
    ]

    async with async_session_maker() as db:
        print("Seeding default testing accounts...")
        for user_data in default_users:
            result = await db.execute(select(User).where(User.email == user_data["email"]))
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                new_user = User(
                    email=user_data["email"],
                    hashed_password=get_password_hash("DemoPass123!"),
                    full_name=user_data["name"],
                    role=user_data["role"],
                    is_active=True
                )
                db.add(new_user)
                print(f"Created: {user_data['email']} (Role: {user_data['role'].value})")
            else:
                print(f"Already exists: {user_data['email']}")
        
        await db.commit()
        print("Done seeding accounts. (All passwords are 'DemoPass123!')")

if __name__ == "__main__":
    if settings.ENVIRONMENT.lower() == "production":
        asyncio.run(bootstrap_production_admin())
    else:
        asyncio.run(seed())