import uuid
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import hash_password
from app.services.settings_service import (
    generate_personal_api_key,
    get_personal_api_key_status,
    revoke_personal_api_key,
    reveal_personal_api_key,
    authenticate_by_api_key,
)


async def _create_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("testpass123"),
        name="Test",
    )
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_generate_personal_api_key(db: AsyncSession):
    user = await _create_user(db)
    result = await generate_personal_api_key(db, user)

    assert result.api_key.startswith("myf_")
    assert result.prefix == result.api_key[:12]
    assert isinstance(result.created_at, datetime)


@pytest.mark.asyncio
async def test_get_status_no_key(db: AsyncSession):
    user = await _create_user(db)
    status = await get_personal_api_key_status(db, user)

    assert status.is_set is False
    assert status.prefix is None


@pytest.mark.asyncio
async def test_get_status_with_key(db: AsyncSession):
    user = await _create_user(db)
    created = await generate_personal_api_key(db, user)
    status = await get_personal_api_key_status(db, user)

    assert status.is_set is True
    assert status.prefix == created.prefix


@pytest.mark.asyncio
async def test_regenerate_replaces_old_key(db: AsyncSession):
    user = await _create_user(db)
    first = await generate_personal_api_key(db, user)
    second = await generate_personal_api_key(db, user)

    assert first.api_key != second.api_key
    assert second.prefix == second.api_key[:12]


@pytest.mark.asyncio
async def test_revoke_personal_api_key(db: AsyncSession):
    user = await _create_user(db)
    await generate_personal_api_key(db, user)
    await revoke_personal_api_key(db, user)

    status = await get_personal_api_key_status(db, user)
    assert status.is_set is False


@pytest.mark.asyncio
async def test_reveal_with_correct_password(db: AsyncSession):
    user = await _create_user(db)
    created = await generate_personal_api_key(db, user)
    revealed = await reveal_personal_api_key(db, user, "testpass123")

    assert revealed is not None
    assert revealed.api_key == created.api_key


@pytest.mark.asyncio
async def test_reveal_with_wrong_password(db: AsyncSession):
    user = await _create_user(db)
    await generate_personal_api_key(db, user)
    revealed = await reveal_personal_api_key(db, user, "wrongpass")

    assert revealed is None


@pytest.mark.asyncio
async def test_authenticate_by_api_key(db: AsyncSession):
    user = await _create_user(db)
    created = await generate_personal_api_key(db, user)
    found = await authenticate_by_api_key(db, created.api_key)

    assert found is not None
    assert found.id == user.id


@pytest.mark.asyncio
async def test_authenticate_by_invalid_key(db: AsyncSession):
    found = await authenticate_by_api_key(db, "myf_invalid_key_here")
    assert found is None
