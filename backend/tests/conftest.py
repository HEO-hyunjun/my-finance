import asyncio
import os

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# 테스트용 고정 Fernet 키 (settings 임포트 전에 설정)
os.environ.setdefault(
    "ENCRYPTION_KEY", "U-KEBJXtxkC53JHAcAPbU3IgxHLtnq3qNPa2asVT5Xs="
)

from app.core.database import Base

import app.models.account  # noqa: F401
import app.models.security  # noqa: F401
import app.models.entry  # noqa: F401
import app.models.category  # noqa: F401
import app.models.recurring_schedule  # noqa: F401
import app.models.portfolio  # noqa: F401
import app.models.budget_v2  # noqa: F401
import app.models.user  # noqa: F401


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
