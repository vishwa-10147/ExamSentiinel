import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.institution import Institution
from app.models.user import User, UserRole

# Use an in-memory SQLite database with async driver for isolated tests
import tempfile
import os

# Create a temporary file for the database
db_fd, db_path = tempfile.mkstemp(suffix=".sqlite")
os.close(db_fd)

TEST_DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
    # No StaticPool, use default pool so concurrent async tasks get their own connection
    connect_args={"check_same_thread": False},
)


test_async_session_maker = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
test_async_session_maker.__test__ = False


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    """Create schema before each test and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override for test database session."""
    async with test_async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override dependency in FastAPI app
app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client bound to FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def test_institution() -> Institution:
    """Create a sample institution for tests."""
    async with test_async_session_maker() as session:
        inst = Institution(
            name="Sentinel University",
            code="SENTINEL_U",
            domain="sentinel.edu",
            is_active=True,
            settings={"retention_days": 90},
        )
        session.add(inst)
        await session.commit()
        await session.refresh(inst)
        return inst


@pytest_asyncio.fixture
async def seed_users(test_institution: Institution):
    """Seed test users with different roles."""
    async with test_async_session_maker() as session:
        users = [
            User(
                email="admin@sentinel.edu",
                hashed_password=get_password_hash("AdminPass123!"),
                full_name="Admin User",
                role=UserRole.ADMIN,
                institution_id=test_institution.id,
                is_active=True,
            ),
            User(
                email="proctor@sentinel.edu",
                hashed_password=get_password_hash("ProctorPass123!"),
                full_name="Proctor User",
                role=UserRole.PROCTOR,
                institution_id=test_institution.id,
                is_active=True,
            ),
            User(
                email="reviewer@sentinel.edu",
                hashed_password=get_password_hash("ReviewerPass123!"),
                full_name="Reviewer User",
                role=UserRole.REVIEWER,
                institution_id=test_institution.id,
                is_active=True,
            ),
            User(
                email="candidate@sentinel.edu",
                hashed_password=get_password_hash("CandidatePass123!"),
                full_name="Candidate User",
                role=UserRole.CANDIDATE,
                institution_id=test_institution.id,
                is_active=True,
            ),
        ]
        session.add_all(users)
        await session.commit()
        return users
