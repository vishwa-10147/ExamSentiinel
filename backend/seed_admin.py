import asyncio
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import async_session_maker
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from sqlalchemy import select

async def seed():
    async with async_session_maker() as db:
        # Check if admin already exists
        result = await db.execute(select(User).where(User.email == "admin@sentinel.edu"))
        existing_admin = result.scalar_one_or_none()
        
        if not existing_admin:
            print("Creating default admin account...")
            admin = User(
                email="admin@sentinel.edu",
                hashed_password=get_password_hash("DemoPass123!"),
                full_name="System Admin",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            await db.commit()
            print("Successfully created admin@sentinel.edu (Pass: DemoPass123!)")
        else:
            print("Admin account already exists.")

if __name__ == "__main__":
    asyncio.run(seed())
