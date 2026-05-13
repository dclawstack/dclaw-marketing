import os
from uuid import uuid4

import pytest_asyncio
from fastapi_users.password import PasswordHelper
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool

from app.api.main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.organization import Organization
from app.models.user import User

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/dclaw_app_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


async def override_get_db():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


_TEST_SUPERUSER_EMAIL = "test-superuser@example.com"
_TEST_SUPERUSER_PASSWORD = "TestPassword123!"


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        # pgvector extension — required by DocumentChunk.embedding column
        # (Q3 / Theme Q3 knowledge graph). pgvector/pgvector:pg16 image
        # ships the extension; we just need to enable it for this DB.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed a default superuser. Tests that need a superuser identity can log in
    # against /api/v1/auth/jwt/login with these credentials (see the
    # `superuser_token` fixture below).
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        helper = PasswordHelper()
        session.add(
            User(
                id=uuid4(),
                email=_TEST_SUPERUSER_EMAIL,
                hashed_password=helper.hash(_TEST_SUPERUSER_PASSWORD),
                is_active=True,
                is_verified=True,
                is_superuser=True,
                password_reset_required=False,
            )
        )
        await session.commit()

    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def superuser_token(client) -> str:
    """JWT for the seeded test superuser — used by SP3-1 legacy-router tests
    that need an authenticated identity without setting up their own user.
    """
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": _TEST_SUPERUSER_EMAIL,
            "password": _TEST_SUPERUSER_PASSWORD,
        },
    )
    res.raise_for_status()
    return res.json()["access_token"]


@pytest_asyncio.fixture
async def auth_client(client, superuser_token):
    """`client` with a default superuser bearer token. Convenience for tests
    that authenticate every request as the seeded superuser.
    """
    client.headers["Authorization"] = f"Bearer {superuser_token}"
    yield client


@pytest_asyncio.fixture
async def test_org_id() -> str:
    """Seed an Organization that legacy-router tests can scope to."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug=f"test-org-{uuid4().hex[:8]}", name="Test Org")
        session.add(org)
        await session.commit()
        await session.refresh(org)
        return str(org.id)
