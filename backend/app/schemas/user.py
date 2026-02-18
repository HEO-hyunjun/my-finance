from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# --- Profile ---


class UserProfileResponse(BaseModel):
    """사용자 프로필 응답"""

    id: str
    email: str
    name: str
    default_currency: str
    salary_day: int = 1
    salary_asset_id: str | None = None
    salary_asset_name: str | None = None
    salary_amount: int | None = None
    notification_preferences: NotificationPreferences | None = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    """프로필 수정 요청"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    default_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    salary_day: int | None = Field(default=None, ge=1, le=28)
    salary_asset_id: str | None = None
    salary_amount: int | None = Field(default=None, ge=0)


# --- Password ---


class PasswordChangeRequest(BaseModel):
    """비밀번호 변경 요청"""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


# --- Notifications ---


class NotificationPreferences(BaseModel):
    """알림 설정"""

    budget_alert: bool = True
    maturity_alert: bool = True
    market_alert: bool = False
    email_notifications: bool = False


# --- Account Deletion ---


class AccountDeleteRequest(BaseModel):
    """계정 삭제 요청 (비밀번호 재확인)"""

    password: str = Field(..., min_length=1)
