import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.asset import Asset
from app.models.user import User
from app.schemas.user import (
    AccountDeleteRequest,
    NotificationPreferences,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    UserProfileResponse,
)


async def get_profile(
    db: AsyncSession,
    user: User,
) -> UserProfileResponse:
    """사용자 프로필 조회"""
    # 급여 자산 이름 조회
    salary_asset_name = None
    if user.salary_asset_id:
        asset = (await db.execute(
            select(Asset).where(Asset.id == user.salary_asset_id)
        )).scalar_one_or_none()
        if asset:
            salary_asset_name = asset.name

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        default_currency=user.default_currency,
        salary_day=user.salary_day,
        salary_asset_id=str(user.salary_asset_id) if user.salary_asset_id else None,
        salary_asset_name=salary_asset_name,
        salary_amount=user.salary_amount,
        notification_preferences=(
            NotificationPreferences(**user.notification_preferences)
            if user.notification_preferences
            else None
        ),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def update_profile(
    db: AsyncSession,
    user: User,
    data: ProfileUpdateRequest,
) -> UserProfileResponse:
    """프로필 수정 (name, default_currency, salary_day, salary_asset_id)"""
    if data.name is not None:
        user.name = data.name
    if data.default_currency is not None:
        user.default_currency = data.default_currency
    if data.salary_day is not None:
        user.salary_day = data.salary_day
    if "salary_asset_id" in data.model_fields_set:
        user.salary_asset_id = uuid.UUID(data.salary_asset_id) if data.salary_asset_id else None
    if "salary_amount" in data.model_fields_set:
        user.salary_amount = data.salary_amount

    await db.commit()
    await db.refresh(user)
    return await get_profile(db, user)


async def change_password(
    db: AsyncSession,
    user: User,
    data: PasswordChangeRequest,
) -> bool:
    """비밀번호 변경 (현재 비밀번호 검증 → 새 비밀번호 저장)"""
    if not verify_password(data.current_password, user.hashed_password):
        return False

    user.hashed_password = hash_password(data.new_password)
    await db.commit()
    return True


async def update_notifications(
    db: AsyncSession,
    user: User,
    prefs: NotificationPreferences,
) -> NotificationPreferences:
    """알림 설정 변경"""
    user.notification_preferences = prefs.model_dump()
    await db.commit()
    await db.refresh(user)
    return prefs


async def delete_account(
    db: AsyncSession,
    user: User,
    data: AccountDeleteRequest,
) -> bool:
    """계정 삭제 (비밀번호 재확인 후 CASCADE 삭제)"""
    if not verify_password(data.password, user.hashed_password):
        return False

    await db.delete(user)
    await db.commit()
    return True
