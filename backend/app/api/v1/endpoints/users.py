from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    AccountDeleteRequest,
    NotificationPreferences,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    UserProfileResponse,
)
from app.services.user_service import (
    change_password,
    delete_account,
    get_profile,
    update_notifications,
    update_profile,
)

router = APIRouter(tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """현재 사용자 프로필 조회"""
    return await get_profile(db, current_user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로필 수정 (이름, 기본 통화)"""
    return await update_profile(db, current_user, body)


@router.put("/me/password")
async def change_my_password(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """비밀번호 변경"""
    success = await change_password(db, current_user, body)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="현재 비밀번호가 일치하지 않습니다.",
        )
    return {"message": "비밀번호가 변경되었습니다."}


@router.patch("/me/notifications", response_model=NotificationPreferences)
async def update_my_notifications(
    body: NotificationPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """알림 설정 변경"""
    return await update_notifications(db, current_user, body)


@router.delete("/me")
async def delete_my_account(
    body: AccountDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """계정 삭제 (비밀번호 재확인 필수)"""
    success = await delete_account(db, current_user, body)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="비밀번호가 일치하지 않습니다.",
        )
    return {"message": "계정이 삭제되었습니다."}
