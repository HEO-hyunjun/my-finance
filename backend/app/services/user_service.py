
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
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
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        default_currency=user.default_currency,
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
    """프로필 수정 (name, default_currency)"""
    if data.name is not None:
        user.name = data.name
    if data.default_currency is not None:
        user.default_currency = data.default_currency

    await db.commit()
    await db.refresh(user)
    return await get_profile(db, user)


async def change_password(
    db: AsyncSession,
    user: User,
    data: PasswordChangeRequest,
) -> bool:
    """비밀번호 변경 (현재 비밀번호 검증 -> 새 비밀번호 저장)"""
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
