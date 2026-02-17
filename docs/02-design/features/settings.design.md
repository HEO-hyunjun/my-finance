# Design: Settings (앱 설정)

> **Feature**: settings
> **Created**: 2026-02-15
> **Plan Reference**: `docs/01-plan/features/settings.plan.md`
> **PDCA Phase**: Design

---

## 1. Backend 상세 설계

### 1.1 User 모델 확장

**파일**: `backend/app/models/user.py` (기존 파일 수정)

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    default_currency: Mapped[str] = mapped_column(
        String(3), default="KRW", nullable=False
    )
    notification_preferences: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

**변경 사항**: `notification_preferences: JSONB` 필드 1개 추가. 기존 필드 변경 없음.

**notification_preferences 기본값** (None이면 프론트에서 기본값 사용):
```json
{
  "budget_alert": true,
  "maturity_alert": true,
  "market_alert": false,
  "email_notifications": false
}
```

---

### 1.2 Pydantic 스키마

**파일**: `backend/app/schemas/user.py`

```python
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
    notification_preferences: NotificationPreferences | None = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    """프로필 수정 요청"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    default_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


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
```

---

### 1.3 서비스 레이어

**파일**: `backend/app/services/user_service.py`

```python
import uuid

from sqlalchemy import select
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
    """비밀번호 변경 (현재 비밀번호 검증 → 새 비밀번호 저장)"""
    if not verify_password(data.current_password, user.password_hash):
        return False

    user.password_hash = hash_password(data.new_password)
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
    if not verify_password(data.password, user.password_hash):
        return False

    await db.delete(user)
    await db.commit()
    return True
```

**핵심 설계 원칙:**
- **get_current_user 재활용**: deps.py에서 이미 로드된 User 객체를 파라미터로 받아 추가 DB 조회 없음
- **verify_password 활용**: 비밀번호 변경/계정 삭제 시 현재 비밀번호 재확인
- **CASCADE 삭제**: User 삭제 시 PostgreSQL FK `ondelete="CASCADE"`로 관련 데이터 자동 삭제

---

### 1.4 API 엔드포인트

**파일**: `backend/app/api/v1/endpoints/users.py`

```python
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

router = APIRouter(prefix="/users", tags=["Users"])


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
```

**API 명세:**

```
GET /api/v1/users/me
  - Auth: Required (JWT Bearer)
  - Response: UserProfileResponse

PATCH /api/v1/users/me
  - Auth: Required
  - Request: ProfileUpdateRequest { name?, default_currency? }
  - Response: UserProfileResponse

PUT /api/v1/users/me/password
  - Auth: Required
  - Request: PasswordChangeRequest { current_password, new_password }
  - 200: { message: "비밀번호가 변경되었습니다." }
  - 400: 현재 비밀번호 불일치

PATCH /api/v1/users/me/notifications
  - Auth: Required
  - Request: NotificationPreferences { budget_alert, maturity_alert, market_alert, email_notifications }
  - Response: NotificationPreferences

DELETE /api/v1/users/me
  - Auth: Required
  - Request: AccountDeleteRequest { password }
  - 200: { message: "계정이 삭제되었습니다." }
  - 400: 비밀번호 불일치
```

**라우터 등록 (`backend/app/main.py`):**

```python
from app.api.v1.endpoints import users

app.include_router(users.router, prefix="/api/v1")
```

---

## 2. Frontend 상세 설계

### 2.1 TypeScript 타입 정의

**파일**: `frontend/src/shared/types/index.ts` (기존 파일 하단에 추가)

```typescript
// ========== Settings Types ==========

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  default_currency: string;
  notification_preferences: NotificationPreferences | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdateRequest {
  name?: string;
  default_currency?: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface NotificationPreferences {
  budget_alert: boolean;
  maturity_alert: boolean;
  market_alert: boolean;
  email_notifications: boolean;
}

export interface AccountDeleteRequest {
  password: string;
}
```

---

### 2.2 TanStack Query Hooks

**파일**: `frontend/src/features/settings/api/index.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  UserProfile,
  ProfileUpdateRequest,
  PasswordChangeRequest,
  NotificationPreferences,
  AccountDeleteRequest,
} from '@/shared/types';

export const userKeys = {
  all: ['user'] as const,
  profile: () => [...userKeys.all, 'profile'] as const,
};

export function useProfile() {
  return useQuery({
    queryKey: userKeys.profile(),
    queryFn: async (): Promise<UserProfile> => {
      const { data } = await apiClient.get('/v1/users/me');
      return data;
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (body: ProfileUpdateRequest): Promise<UserProfile> => {
      const { data } = await apiClient.patch('/v1/users/me', body);
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(userKeys.profile(), data);
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (body: PasswordChangeRequest) => {
      const { data } = await apiClient.put('/v1/users/me/password', body);
      return data;
    },
  });
}

export function useUpdateNotifications() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      body: NotificationPreferences,
    ): Promise<NotificationPreferences> => {
      const { data } = await apiClient.patch('/v1/users/me/notifications', body);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.profile() });
    },
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: async (body: AccountDeleteRequest) => {
      const { data } = await apiClient.delete('/v1/users/me', { data: body });
      return data;
    },
  });
}
```

---

### 2.3 UI 컴포넌트 설계

#### 2.3.1 컴포넌트 트리

```
pages/settings/index.tsx
├── ProfileSection               # 프로필 정보 + 수정 폼
│   ├── 이름 input (수정 가능)
│   ├── 이메일 (읽기 전용, 회색)
│   └── 기본 통화 select 드롭다운
│
├── PasswordSection              # 비밀번호 변경 폼
│   ├── 현재 비밀번호 input
│   ├── 새 비밀번호 input
│   ├── PasswordStrength 인디케이터
│   └── 비밀번호 확인 input
│
├── NotificationSection          # 알림 토글 스위치
│   ├── 예산 초과 알림 toggle
│   ├── 만기 알림 toggle
│   ├── 시장 변동 알림 toggle
│   └── 이메일 알림 toggle
│
└── DangerZone                   # 위험 영역
    ├── 로그아웃 버튼
    └── 계정 삭제 버튼 + DeleteAccountModal
```

#### 2.3.2 컴포넌트 상세

**ProfileSection** — `features/settings/ui/ProfileSection.tsx`

```
┌─── 프로필 정보 ──────────────────────────────────┐
│                                                   │
│  이름                                             │
│  ┌───────────────────────────────────────┐        │
│  │ 홍길동                                │        │
│  └───────────────────────────────────────┘        │
│                                                   │
│  이메일                                           │
│  ┌───────────────────────────────────────┐        │
│  │ hong@example.com          🔒 읽기전용  │        │
│  └───────────────────────────────────────┘        │
│                                                   │
│  기본 통화                                        │
│  ┌───────────────────────────────────────┐        │
│  │ KRW (대한민국 원)                ▼    │        │
│  └───────────────────────────────────────┘        │
│                                                   │
│                              [ 저장 ]             │
└───────────────────────────────────────────────────┘
```

- Props: `profile: UserProfile, onSave: (data: ProfileUpdateRequest) => void, isSaving: boolean`
- 이름: `input[type=text]` 수정 가능
- 이메일: `input[type=email]` 읽기 전용, `bg-gray-100 cursor-not-allowed`
- 통화: `<select>` (KRW, USD, JPY, EUR, GBP, CNY)
- 저장 버튼: `bg-blue-500 text-white`, 변경 사항 있을 때만 활성화

**통화 옵션:**
```typescript
const CURRENCIES = [
  { code: 'KRW', label: '대한민국 원 (₩)' },
  { code: 'USD', label: '미국 달러 ($)' },
  { code: 'JPY', label: '일본 엔 (¥)' },
  { code: 'EUR', label: '유로 (€)' },
  { code: 'GBP', label: '영국 파운드 (£)' },
  { code: 'CNY', label: '중국 위안 (¥)' },
];
```

**PasswordSection** — `features/settings/ui/PasswordSection.tsx`

```
┌─── 비밀번호 변경 ──────────────────────────────┐
│                                                 │
│  현재 비밀번호                                  │
│  ┌─────────────────────────────────────┐        │
│  │ ••••••••                    [👁]    │        │
│  └─────────────────────────────────────┘        │
│                                                 │
│  새 비밀번호                                    │
│  ┌─────────────────────────────────────┐        │
│  │ ••••••••                    [👁]    │        │
│  └─────────────────────────────────────┘        │
│  ████████░░░░ 보통 (8자 이상 충족)              │
│                                                 │
│  새 비밀번호 확인                               │
│  ┌─────────────────────────────────────┐        │
│  │ ••••••••                    [👁]    │        │
│  └─────────────────────────────────────┘        │
│                                                 │
│                        [ 비밀번호 변경 ]         │
└─────────────────────────────────────────────────┘
```

- Props: `onSubmit: (data: PasswordChangeRequest) => void, isSubmitting: boolean`
- 3개 input: 현재/새/확인 비밀번호, 각각 show/hide 토글
- 비밀번호 강도: 약함(빨강)/보통(주황)/강함(초록) 바 + 텍스트
- 강도 기준: 8자 미만=약함, 8자 이상=보통, 8자+대문자+숫자+특수=강함
- 변경 버튼: 새 비밀번호와 확인이 일치하고 현재 비밀번호 입력 시 활성화
- 성공 시: 폼 리셋 + "비밀번호가 변경되었습니다" 성공 메시지
- 실패 시 (400): "현재 비밀번호가 일치하지 않습니다" 에러 표시

**비밀번호 강도 계산:**
```typescript
function getPasswordStrength(password: string): 'weak' | 'medium' | 'strong' {
  if (password.length < 8) return 'weak';
  const hasUpper = /[A-Z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
  if (hasUpper && hasNumber && hasSpecial) return 'strong';
  return 'medium';
}
```

**NotificationSection** — `features/settings/ui/NotificationSection.tsx`

```
┌─── 알림 설정 ──────────────────────────────────┐
│                                                 │
│  예산 초과 알림                         [🔵 ON] │
│  설정된 예산을 초과하면 알림을 받습니다          │
│                                                 │
│  만기 알림                              [🔵 ON] │
│  예금/적금 만기일이 가까워지면 알림을 받습니다   │
│                                                 │
│  시장 변동 알림                        [⚪ OFF] │
│  환율/시세 큰 변동 시 알림을 받습니다           │
│                                                 │
│  이메일 알림                           [⚪ OFF] │
│  중요 알림을 이메일로도 받습니다                │
│                                                 │
└─────────────────────────────────────────────────┘
```

- Props: `preferences: NotificationPreferences, onToggle: (key: string, value: boolean) => void`
- 각 항목: 라벨 + 설명 텍스트 + 커스텀 토글 스위치
- 토글 시 즉시 API 호출 (debounce 없이, 개별 토글)
- 토글 스위치: `w-11 h-6 rounded-full`, ON=`bg-blue-500`, OFF=`bg-gray-300`

**알림 항목 정의:**
```typescript
const NOTIFICATION_ITEMS = [
  { key: 'budget_alert', label: '예산 초과 알림', description: '설정된 예산을 초과하면 알림을 받습니다' },
  { key: 'maturity_alert', label: '만기 알림', description: '예금/적금 만기일이 가까워지면 알림을 받습니다' },
  { key: 'market_alert', label: '시장 변동 알림', description: '환율/시세 큰 변동 시 알림을 받습니다' },
  { key: 'email_notifications', label: '이메일 알림', description: '중요 알림을 이메일로도 받습니다' },
];
```

**DangerZone** — `features/settings/ui/DangerZone.tsx`

```
┌─── 계정 관리 ──────────────────────────── 빨강 border ─┐
│                                                         │
│  로그아웃                                               │
│  현재 세션에서 로그아웃합니다.                            │
│                                        [ 로그아웃 ]     │
│                                                         │
│  ─────────────────────────────────────────────          │
│                                                         │
│  계정 삭제                                              │
│  계정과 모든 데이터가 영구적으로 삭제됩니다.              │
│  이 작업은 되돌릴 수 없습니다.                           │
│                                        [ 계정 삭제 ]    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

- Props: `onLogout: () => void, onDeleteAccount: () => void`
- 섹션 스타일: `border-red-200 bg-red-50`
- 로그아웃 버튼: `border border-gray-300 text-gray-700 hover:bg-gray-100`
- 계정 삭제 버튼: `bg-red-500 text-white hover:bg-red-600`
- 계정 삭제 클릭 시: `DeleteAccountModal` 오픈

**DeleteAccountModal** — `features/settings/ui/DeleteAccountModal.tsx`

```
┌─────── 계정 삭제 확인 ──────────────────┐
│                                          │
│  ⚠️  정말 계정을 삭제하시겠습니까?       │
│                                          │
│  이 작업은 되돌릴 수 없으며,             │
│  모든 데이터가 영구적으로 삭제됩니다:    │
│  • 자산 정보                             │
│  • 거래 내역                             │
│  • 예산 설정                             │
│  • 대화 기록                             │
│                                          │
│  비밀번호 확인                           │
│  ┌────────────────────────────────┐      │
│  │                                │      │
│  └────────────────────────────────┘      │
│                                          │
│        [ 취소 ]    [ 계정 영구 삭제 ]    │
│                                          │
└──────────────────────────────────────────┘
```

- Props: `isOpen: boolean, onClose: () => void, onConfirm: (password: string) => void, isDeleting: boolean`
- 배경 overlay: `bg-black/50`
- 삭제 확인 버튼: `bg-red-600 text-white`, 비밀번호 입력 시 활성화
- 삭제 실패 (400): "비밀번호가 일치하지 않습니다" 에러 표시

---

### 2.4 페이지 레이아웃

**파일**: `frontend/src/pages/settings/index.tsx`

```typescript
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  useProfile,
  useUpdateProfile,
  useChangePassword,
  useUpdateNotifications,
  useDeleteAccount,
} from '@/features/settings/api';
import { useAuthStore } from '@/features/auth/model/auth-store';
import { ProfileSection } from '@/features/settings/ui/ProfileSection';
import { PasswordSection } from '@/features/settings/ui/PasswordSection';
import { NotificationSection } from '@/features/settings/ui/NotificationSection';
import { DangerZone } from '@/features/settings/ui/DangerZone';
import { DeleteAccountModal } from '@/features/settings/ui/DeleteAccountModal';
import type {
  ProfileUpdateRequest,
  PasswordChangeRequest,
  NotificationPreferences,
} from '@/shared/types';

export function Component() {
  const navigate = useNavigate();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const updateNotifications = useUpdateNotifications();
  const deleteAccount = useDeleteAccount();
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleDeleteAccount = (password: string) => {
    deleteAccount.mutate(
      { password },
      {
        onSuccess: () => {
          logout();
          navigate('/login');
        },
      },
    );
  };

  if (isLoading || !profile) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-2xl font-bold">설정</h1>

      <ProfileSection
        profile={profile}
        onSave={(data) => updateProfile.mutate(data)}
        isSaving={updateProfile.isPending}
      />

      <PasswordSection
        onSubmit={(data) => changePassword.mutate(data)}
        isSubmitting={changePassword.isPending}
      />

      <NotificationSection
        preferences={
          profile.notification_preferences || {
            budget_alert: true,
            maturity_alert: true,
            market_alert: false,
            email_notifications: false,
          }
        }
        onToggle={(key, value) => {
          const current = profile.notification_preferences || {
            budget_alert: true,
            maturity_alert: true,
            market_alert: false,
            email_notifications: false,
          };
          updateNotifications.mutate({ ...current, [key]: value });
        }}
      />

      <DangerZone
        onLogout={handleLogout}
        onDeleteAccount={() => setDeleteModalOpen(true)}
      />

      <DeleteAccountModal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        onConfirm={handleDeleteAccount}
        isDeleting={deleteAccount.isPending}
      />
    </div>
  );
}
```

**레이아웃:**

| 구성 요소 | 스타일 |
|-----------|--------|
| 컨테이너 | `max-w-2xl mx-auto p-6` (가운데 정렬, 최대 672px) |
| 섹션 간격 | `space-y-6` (1.5rem) |
| 각 섹션 | `rounded-lg border p-6` 카드 스타일 |
| DangerZone | `border-red-200 bg-red-50` 빨간 경고 스타일 |

---

## 3. 구현 순서 (Implementation Order)

```
Step 1: Backend — User 모델 확장
  └── backend/app/models/user.py              (notification_preferences JSONB 추가)

Step 2: Backend — Pydantic 스키마
  └── backend/app/schemas/user.py             (5개 스키마)

Step 3: Backend — 사용자 서비스
  └── backend/app/services/user_service.py    (5개 함수)

Step 4: Backend — API 엔드포인트 + 라우터 등록
  ├── backend/app/api/v1/endpoints/users.py   (5개 엔드포인트)
  └── backend/app/main.py                     (라우터 등록)

Step 5: Frontend — 타입 정의
  └── frontend/src/shared/types/index.ts      (Settings 타입 추가)

Step 6: Frontend — API Hooks
  └── frontend/src/features/settings/api/index.ts (5개 hooks)

Step 7: Frontend — UI 컴포넌트
  ├── features/settings/ui/ProfileSection.tsx
  ├── features/settings/ui/PasswordSection.tsx
  ├── features/settings/ui/NotificationSection.tsx
  ├── features/settings/ui/DangerZone.tsx
  └── features/settings/ui/DeleteAccountModal.tsx

Step 8: Frontend — 페이지 조합
  └── frontend/src/pages/settings/index.tsx   (전체 레이아웃)
```

---

## 4. 에러 처리 전략

### 4.1 Backend

| 상황 | 처리 |
|------|------|
| 현재 비밀번호 불일치 | 400 "현재 비밀번호가 일치하지 않습니다." |
| 계정 삭제 비밀번호 불일치 | 400 "비밀번호가 일치하지 않습니다." |
| 잘못된 통화 코드 | Pydantic validation (pattern `^[A-Z]{3}$`) |
| 이름 빈 문자열 | Pydantic validation (min_length=1) |
| 새 비밀번호 8자 미만 | Pydantic validation (min_length=8) |

### 4.2 Frontend

| 상황 | 처리 |
|------|------|
| 프로필 수정 성공 | auth-store user 업데이트 + 성공 토스트 |
| 비밀번호 변경 성공 | 폼 리셋 + 성공 메시지 표시 |
| 비밀번호 불일치 (서버 400) | 에러 메시지 빨간색 표시 |
| 새 비밀번호 ≠ 확인 | 클라이언트 측 검증, 버튼 비활성화 |
| 계정 삭제 성공 | logout() + /login 리다이렉트 |
| 프로필 로딩 실패 | 로딩 스피너 표시 |

---

## 5. 검증 체크리스트

Design → Do 전환 시 구현 검증 기준:

- [ ] **BE-1**: User 모델에 `notification_preferences: JSONB` 필드 추가
- [ ] **BE-2**: `user.py` Pydantic 스키마 (UserProfileResponse, ProfileUpdateRequest, PasswordChangeRequest, NotificationPreferences, AccountDeleteRequest)
- [ ] **BE-3**: `user_service.get_profile()` — 프로필 조회
- [ ] **BE-4**: `user_service.update_profile()` — 이름/통화 수정
- [ ] **BE-5**: `user_service.change_password()` — 비밀번호 변경 (verify + hash)
- [ ] **BE-6**: `user_service.update_notifications()` — 알림 설정 JSONB 저장
- [ ] **BE-7**: `user_service.delete_account()` — 비밀번호 재확인 + CASCADE 삭제
- [ ] **BE-8**: `GET /api/v1/users/me` 프로필 조회 엔드포인트
- [ ] **BE-9**: `PATCH /api/v1/users/me` 프로필 수정 엔드포인트
- [ ] **BE-10**: `PUT /api/v1/users/me/password` 비밀번호 변경 엔드포인트
- [ ] **BE-11**: `PATCH /api/v1/users/me/notifications` 알림 설정 엔드포인트
- [ ] **BE-12**: `DELETE /api/v1/users/me` 계정 삭제 엔드포인트
- [ ] **BE-13**: `main.py`에 users 라우터 등록
- [ ] **FE-1**: Settings 타입 정의 (`shared/types`) — UserProfile, ProfileUpdateRequest, PasswordChangeRequest, NotificationPreferences, AccountDeleteRequest
- [ ] **FE-2**: `useProfile`, `useUpdateProfile`, `useChangePassword`, `useUpdateNotifications`, `useDeleteAccount` hooks
- [ ] **FE-3**: `ProfileSection` — 이름 수정 + 이메일 읽기전용 + 통화 드롭다운 + 저장
- [ ] **FE-4**: `PasswordSection` — 3개 비밀번호 입력 + 강도 표시 + show/hide 토글
- [ ] **FE-5**: `NotificationSection` — 4개 알림 토글 스위치 + 설명 텍스트
- [ ] **FE-6**: `DangerZone` — 로그아웃 버튼 + 계정 삭제 버튼 (빨간 스타일)
- [ ] **FE-7**: `DeleteAccountModal` — 확인 모달 + 비밀번호 재입력 + 삭제 실행
- [ ] **FE-8**: 설정 페이지 레이아웃 (max-w-2xl 카드형 섹션 배치)
- [ ] **FE-9**: 로딩 스피너 표시 (프로필 로드 중)
- [ ] **FE-10**: 성공/에러 메시지 표시 (비밀번호 변경 결과 등)

---

## 6. 다음 단계

Design 승인 후 → `/pdca do settings` 로 구현 시작
