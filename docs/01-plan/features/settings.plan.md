# Plan: Settings (앱 설정)

> **Feature**: settings
> **Created**: 2026-02-15
> **PRD Reference**: 사용자 프로필 관리, 앱 환경 설정
> **PDCA Phase**: Plan

---

## 1. 기능 개요

사용자가 개인 프로필 정보, 보안(비밀번호), 기본 통화, 알림 설정을 관리하고, 계정 삭제/로그아웃 기능을 사용할 수 있는 종합 설정 페이지.

### 1.1 핵심 목표

- 프로필 정보 조회 및 수정 (이름, 이메일)
- 비밀번호 변경 (현재 비밀번호 확인 + 새 비밀번호)
- 기본 통화 설정 (KRW, USD 등 — User 모델의 `default_currency`)
- 알림 설정 (푸시/이메일 알림 on/off)
- 로그아웃 및 계정 삭제 (데이터 영구 삭제)

### 1.2 기존 구현 피처 연계

| 연계 피처 | 활용 데이터 | 비고 |
|-----------|-------------|------|
| auth | User 모델 (id, email, name, default_currency) | 프로필 데이터 소스 |
| auth-store | 로그인/로그아웃 상태 관리 | Zustand persist |
| security.py | password hash/verify, JWT | 비밀번호 변경에 활용 |

### 1.3 현재 상태

- **Frontend**: `pages/settings/index.tsx` — 플레이스홀더만 존재 (`<h1>설정</h1>`)
- **Backend**: 프로필/비밀번호 관련 API 없음. User 모델에 `default_currency` 필드는 존재
- **Backend**: auth 전용 엔드포인트 파일 없음 (`api/v1/endpoints/auth.py` 미존재)
- **Auth 로직**: `api/deps.py`에 `get_current_user` + `core/security.py`에 JWT/bcrypt 유틸만 존재

---

## 2. 구현 범위

### 2.1 In Scope (이번 Plan)

#### 프로필 관리

- [ ] **프로필 조회**: 현재 사용자 이름, 이메일, 기본 통화, 가입일 표시
- [ ] **프로필 수정**: 이름(닉네임), 기본 통화 변경
- [ ] **이메일 표시**: 이메일은 읽기 전용 (변경 불가)

#### 보안

- [ ] **비밀번호 변경**: 현재 비밀번호 확인 → 새 비밀번호 (최소 8자) → 확인 입력
- [ ] **비밀번호 강도 표시**: 약함/보통/강함 시각적 인디케이터

#### 기본 통화 설정

- [ ] **통화 선택**: KRW, USD, JPY, EUR 등 주요 통화 선택
- [ ] **자산 표시 영향**: default_currency 변경 시 앱 전체 금액 표시 기준 변경

#### 알림 설정

- [ ] **알림 토글**: 푸시 알림, 이메일 알림 on/off
- [ ] **알림 유형**: 예산 초과 알림, 만기 알림, 시장 변동 알림

#### 계정 관리

- [ ] **로그아웃**: 토큰 삭제 + 로그인 페이지 이동
- [ ] **계정 삭제**: 확인 모달 → 비밀번호 재확인 → 모든 데이터 영구 삭제

#### Backend API

- [ ] **`GET /api/v1/users/me`** — 현재 사용자 프로필 조회
- [ ] **`PATCH /api/v1/users/me`** — 프로필 수정 (name, default_currency)
- [ ] **`PUT /api/v1/users/me/password`** — 비밀번호 변경
- [ ] **`PATCH /api/v1/users/me/notifications`** — 알림 설정 변경
- [ ] **`DELETE /api/v1/users/me`** — 계정 삭제 (전체 데이터 cascade)

#### Frontend

- [ ] **SettingsPage**: 섹션별 구분된 설정 UI
- [ ] **ProfileSection**: 프로필 정보 표시 및 수정 폼
- [ ] **PasswordSection**: 비밀번호 변경 폼
- [ ] **NotificationSection**: 알림 토글 스위치
- [ ] **DangerZone**: 계정 삭제 (빨간색 경고 영역)

### 2.2 Out of Scope (향후)

- 소셜 로그인 연동 (Google, Kakao)
- 다국어 설정 (i18n)
- 2단계 인증 (2FA/OTP)
- 데이터 내보내기 (CSV/Excel)
- 세션 관리 (활성 디바이스 목록)

---

## 3. 기술 스택

| 카테고리 | 기술 | 용도 |
|----------|------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 async | CRUD + 비밀번호 변경 |
| 비밀번호 | passlib (bcrypt) | hash_password, verify_password |
| DB | PostgreSQL | User 모델 + notification_preferences |
| Frontend State | Zustand (auth-store) | 프로필 상태 관리 |
| Frontend Data | TanStack Query | 서버 상태 캐싱 |
| UI | Tailwind CSS | 설정 페이지 레이아웃 |

---

## 4. 비기능 요구사항

| 항목 | 기준 |
|------|------|
| 비밀번호 보안 | bcrypt 해싱, 최소 8자, 현재 비밀번호 확인 필수 |
| 계정 삭제 | CASCADE 삭제 (conversations, assets, transactions 등 전부) |
| 반응형 | 모바일/데스크톱 대응 |
| 에러 처리 | 비밀번호 불일치, 중복 요청 등 사용자 친화적 에러 메시지 |
| 성능 | 프로필 조회 < 200ms |

---

## 5. 데이터 모델 변경

### 5.1 User 모델 확장 (기존 필드 유지)

현재 User 모델:
```
users: id, email, password_hash, name, default_currency, created_at, updated_at
```

추가 필드:
```
notification_preferences: JSONB (nullable)
```

`notification_preferences` 예시:
```json
{
  "budget_alert": true,
  "maturity_alert": true,
  "market_alert": false,
  "email_notifications": false
}
```

---

## 6. API 설계 (개요)

| Method | Endpoint | 설명 | Auth |
|--------|----------|------|------|
| GET | `/api/v1/users/me` | 프로필 조회 | Required |
| PATCH | `/api/v1/users/me` | 프로필 수정 | Required |
| PUT | `/api/v1/users/me/password` | 비밀번호 변경 | Required |
| PATCH | `/api/v1/users/me/notifications` | 알림 설정 | Required |
| DELETE | `/api/v1/users/me` | 계정 삭제 | Required |

---

## 7. UI/UX 구조

```
pages/settings/index.tsx
├── ProfileSection         # 프로필 정보 + 수정 폼
│   ├── 이름 (수정 가능)
│   ├── 이메일 (읽기 전용)
│   └── 기본 통화 (드롭다운)
│
├── PasswordSection        # 비밀번호 변경 폼
│   ├── 현재 비밀번호
│   ├── 새 비밀번호 (강도 표시)
│   └── 비밀번호 확인
│
├── NotificationSection    # 알림 토글
│   ├── 예산 초과 알림  [ON/OFF]
│   ├── 만기 알림       [ON/OFF]
│   ├── 시장 변동 알림  [ON/OFF]
│   └── 이메일 알림     [ON/OFF]
│
└── DangerZone             # 계정 관리
    ├── 로그아웃 버튼
    └── 계정 삭제 버튼 (빨간색, 확인 모달)
```

---

## 8. 위험 요소 및 대응

| 위험 | 영향 | 대응 |
|------|------|------|
| 계정 삭제 시 데이터 복구 불가 | 높음 | 2단계 확인 (모달 + 비밀번호 재입력) |
| 비밀번호 변경 후 토큰 무효화 | 중간 | 변경 후 기존 토큰은 유지 (JWT stateless) |
| 통화 변경 시 기존 데이터 영향 | 낮음 | display 기준만 변경, 원본 데이터는 각 자산 통화 그대로 |
| 알림 설정 DB 미존재 | 낮음 | User 모델에 JSONB 필드 추가 |

---

## 9. 구현 순서 (예상)

```
Step 1: Backend — User 모델 확장 (notification_preferences JSONB 추가)
Step 2: Backend — Pydantic 스키마 (프로필, 비밀번호, 알림)
Step 3: Backend — 사용자 서비스 (user_service.py)
Step 4: Backend — API 엔드포인트 (users.py) + 라우터 등록
Step 5: Frontend — 타입 정의 + API Hooks
Step 6: Frontend — UI 컴포넌트 (4개 섹션)
Step 7: Frontend — 페이지 조합 + 상태 연동
```

---

## 10. 다음 단계

Plan 승인 후 → `/pdca design settings` 로 Design 문서 작성
