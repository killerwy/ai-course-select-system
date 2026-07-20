"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.database import Base
from app.main import app
from app.storage import get_optional_db
from app.store import InMemoryStore, build_store


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Return test settings."""
    return Settings(
        app_storage="memory",
        jwt_secret="test-secret-key-for-testing",
        jwt_algorithm="HS256",
        jwt_expire_minutes=60,
    )


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a test database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with database session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_optional_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def memory_client() -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client in memory mode."""
    async def override_get_db():
        yield None

    app.dependency_overrides[get_optional_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user() -> dict:
    """Return a sample user dict."""
    return {
        "id": "test-user-001",
        "username": "teststudent",
        "role": "STUDENT",
        "student_no": "2024001",
        "major": "计算机科学",
        "grade": 1,
    }


@pytest.fixture
def sample_academic() -> dict:
    """Return a sample academic user dict."""
    return {
        "id": "test-academic-001",
        "username": "testacademic",
        "role": "ACADEMIC",
    }


@pytest.fixture
def sample_course() -> dict:
    """Return a sample course dict."""
    return {
        "id": "course-test-001",
        "code": "CS101",
        "name": "程序设计基础",
        "teacher_name": "王老师",
        "credits": 3,
        "capacity": 30,
        "status": "OPEN",
        "version": 1,
        "schedules": [
            {"weekday": 1, "start_minute": 480, "end_minute": 570, "room": "A101"},
            {"weekday": 3, "start_minute": 480, "end_minute": 570, "room": "A101"},
        ],
        "prerequisites": [],
    }


@pytest.fixture
def sample_enrollment() -> dict:
    """Return a sample enrollment dict."""
    return {
        "id": "enrollment-test-001",
        "student_id": "test-user-001",
        "course_id": "course-test-001",
        "status": "ENROLLED",
        "source": "DIRECT",
    }


@pytest.fixture
def in_memory_store() -> InMemoryStore:
    """Return a fresh in-memory store with seed data."""
    return build_store()


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Return a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock(return_value=None)
    return session
