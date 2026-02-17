# Gap Analysis: Settings (앱 설정)

> **Feature**: settings
> **Analyzed**: 2026-02-15
> **Design Reference**: `docs/02-design/features/settings.design.md`
> **PDCA Phase**: Check

---

## 1. 분석 요약

| 항목 | 값 |
|------|-----|
| 전체 체크리스트 | 23개 |
| 일치 항목 | 22개 |
| 부분 일치 | 1개 |
| 미구현 | 0개 |
| **Match Rate** | **96%** (22/23) |

---

## 2. 체크리스트 상세 비교

### Backend (BE-1 ~ BE-13): 13/13 일치

| ID | 항목 | 상태 | 비고 |
|----|------|------|------|
| BE-1 | User 모델 `notification_preferences: JSONB` | ✅ 일치 | `models/user.py:23-25` — Design과 정확히 동일 |
| BE-2 | Pydantic 스키마 5개 | ✅ 일치 | `schemas/user.py` — UserProfileResponse, ProfileUpdateRequest, PasswordChangeRequest, NotificationPreferences, AccountDeleteRequest 모두 구현. Field 검증 (min_length, pattern) 포함 |
| BE-3 | `get_profile()` | ✅ 일치 | `services/user_service.py:14-31` — NotificationPreferences 변환 로직 포함 |
| BE-4 | `update_profile()` | ✅ 일치 | `services/user_service.py:34-47` — name/default_currency 조건부 업데이트, commit+refresh |
| BE-5 | `change_password()` | ✅ 일치 | `services/user_service.py:50-61` — verify_password + hash_password 사용 |
| BE-6 | `update_notifications()` | ✅ 일치 | `services/user_service.py:64-73` — model_dump()로 JSONB 저장 |
| BE-7 | `delete_account()` | ✅ 일치 | `services/user_service.py:76-87` — verify_password + db.delete (CASCADE) |
| BE-8 | `GET /users/me` | ✅ 일치 | `api/v1/endpoints/users.py:25-31` — response_model=UserProfileResponse |
| BE-9 | `PATCH /users/me` | ✅ 일치 | `api/v1/endpoints/users.py:34-41` |
| BE-10 | `PUT /users/me/password` | ✅ 일치 | `api/v1/endpoints/users.py:44-57` — 400 에러 반환 |
| BE-11 | `PATCH /users/me/notifications` | ✅ 일치 | `api/v1/endpoints/users.py:60-67` — response_model=NotificationPreferences |
| BE-12 | `DELETE /users/me` | ✅ 일치 | `api/v1/endpoints/users.py:70-83` — 400 에러 반환 |
| BE-13 | `main.py` 라우터 등록 | ✅ 일치 | `main.py:8,45` — import + include_router |

### Frontend (FE-1 ~ FE-10): 9/10 일치

| ID | 항목 | 상태 | 비고 |
|----|------|------|------|
| FE-1 | Settings 타입 정의 | ✅ 일치 | `shared/types/index.ts:576-607` — 5개 인터페이스 모두 일치 |
| FE-2 | TanStack Query Hooks 5개 | ✅ 일치 | `features/settings/api/index.ts` — userKeys, useProfile, useUpdateProfile, useChangePassword, useUpdateNotifications, useDeleteAccount |
| FE-3 | ProfileSection | ✅ 일치 | 이름 수정 input + 이메일 readonly (bg-gray-100 cursor-not-allowed) + 통화 select (6개 옵션) + 저장 버튼 (변경시만 활성화) |
| FE-4 | PasswordSection | ✅ 일치 | 3개 비밀번호 input + show/hide 토글 + 강도 바 (weak/medium/strong) + 확인 불일치 검증 |
| FE-5 | NotificationSection | ✅ 일치 | 4개 알림 토글 (h-6 w-11 rounded-full, role="switch" aria-checked) + 설명 텍스트. NOTIFICATION_ITEMS 정의 일치 |
| FE-6 | DangerZone | ✅ 일치 | border-red-200 bg-red-50 + 로그아웃 버튼 (gray) + 계정 삭제 버튼 (red-500) |
| FE-7 | DeleteAccountModal | ✅ 일치 | bg-black/50 overlay + 삭제 데이터 목록 + 비밀번호 입력 + 취소/삭제 버튼 (red-600) |
| FE-8 | 페이지 레이아웃 | ✅ 일치 | max-w-2xl mx-auto space-y-6 p-6 + 4 섹션 + 모달. useAuthStore logout + navigate('/login') |
| FE-9 | 로딩 스피너 | ✅ 일치 | animate-spin h-8 w-8 border-blue-500 스피너 |
| FE-10 | 성공/에러 메시지 표시 | ⚠️ 부분 | 아래 Gap 상세 참조 |

---

## 3. Gap 상세

### Gap-1: FE-10 — 비밀번호 변경 성공/에러 콜백 미연결 (부분 구현)

**설계 요구사항 (에러 처리 4.2):**
- 비밀번호 변경 성공 → 폼 리셋 + "비밀번호가 변경되었습니다" 성공 메시지
- 비밀번호 불일치 (서버 400) → "현재 비밀번호가 일치하지 않습니다" 에러 표시

**현재 구현:**
- `PasswordSection.tsx`에 `message` state (success/error) 인프라 존재 (line 31)
- 메시지 렌더링 UI 존재 (line 48-58)
- **문제**: 페이지에서 `changePassword.mutate(data)` 호출 시 `onSuccess`/`onError` 콜백 없음
- 따라서 성공 시 폼 리셋 안 됨, 성공/에러 메시지 표시 안 됨

**영향도**: 낮음 (기능 자체는 동작하나 사용자 피드백 부재)

**수정 방안**:
1. PasswordSection에 `onSuccess`/`onError` 콜백 props 추가
2. 또는 페이지에서 mutation 결과를 PasswordSection에 전달

---

## 4. 설계 대비 개선사항

| 항목 | 설명 |
|------|------|
| NotificationSection 접근성 | `role="switch"` + `aria-checked` 추가로 스크린 리더 지원 향상 |
| ProfileSection 변경 감지 | `hasChanges` 비교로 불필요한 API 호출 방지 (설계에 명시되었고 정확히 구현) |
| 통화 코드 CURRENCIES | 디자인 스펙과 정확히 동일한 6개 통화 옵션 |

---

## 5. 결론

| 항목 | 결과 |
|------|------|
| Match Rate | **96%** (22/23) |
| 미구현 기능 | 없음 |
| 부분 구현 | 1건 (비밀번호 변경 피드백 콜백) |
| 설계 일탈 | 없음 |
| 판정 | **PASS** (>= 90% 기준 충족) |

---

## 6. 구현 파일 목록

### Backend
- `backend/app/models/user.py` — User 모델 (JSONB 필드 추가)
- `backend/app/schemas/user.py` — Pydantic 스키마 5개
- `backend/app/services/user_service.py` — 서비스 함수 5개
- `backend/app/api/v1/endpoints/users.py` — API 엔드포인트 5개
- `backend/app/main.py` — 라우터 등록

### Frontend
- `frontend/src/shared/types/index.ts` — Settings 타입 정의
- `frontend/src/features/settings/api/index.ts` — TanStack Query hooks
- `frontend/src/features/settings/ui/ProfileSection.tsx` — 프로필 섹션
- `frontend/src/features/settings/ui/PasswordSection.tsx` — 비밀번호 섹션
- `frontend/src/features/settings/ui/NotificationSection.tsx` — 알림 섹션
- `frontend/src/features/settings/ui/DangerZone.tsx` — 위험 영역
- `frontend/src/features/settings/ui/DeleteAccountModal.tsx` — 삭제 모달
- `frontend/src/pages/settings/index.tsx` — 설정 페이지
