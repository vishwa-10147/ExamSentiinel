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
    asyncio.run(seed())