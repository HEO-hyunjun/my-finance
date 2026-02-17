# Plan: Budget Management (가계부 & 예산 관리)

> **Feature**: budget-management
> **Created**: 2026-02-05
> **PRD Reference**: 섹션 2.2 (가계부 & 예산 관리), 섹션 2.7 (설정), 섹션 5.1 (데이터 모델)
> **PDCA Phase**: Plan

---

## 1. 기능 개요

월별 카테고리별 예산을 설정하고, 실제 지출을 기록하여 예산 대비 소비를 추적한다. 고정비·할부금을 별도 관리하며, 미사용 예산은 사용자가 선택한 방식으로 이월한다. 월급일 기준 예산 사이클을 지원하고, 예산 분석 대시보드를 제공한다.

### 1.1 핵심 목표

- 카테고리별 월 예산 설정 및 지출 추적
- 지출 기록 CRUD (금액, 카테고리, 결제수단, 메모, 태그)
- 고정 비용 관리 (월세, 구독료 등 자동 차감)
- 할부금 관리 (진행률 추적, 완료 시 자동 비활성화)
- 예산 이월 정책 (소멸, 이월, 저축, 투자, 예금)
- 월급일 기준 예산 기간 및 전환 관리
- 예산 분석 (일별 사용 가능 금액, 카테고리별 소진율, 이월 예측)

### 1.2 PRD 근거

| PRD 섹션 | 내용 |
|----------|------|
| 2.2.1 | 예산 설정 (월별 총 예산, 카테고리별 예산, 월급일 기준 사이클) |
| 2.2.2 | 지출 기록 (날짜, 금액, 카테고리, 메모, 결제수단, 태그) |
| 2.2.3 | 고정 비용 관리 (자동 차감, 활성/비활성) |
| 2.2.4 | 할부금 관리 (진행률, 완료 시 자동 비활성화) |
| 2.2.5 | 예산 이월 정책 (5가지 이월 방식, 카테고리별 개별 설정) |
| 2.2.6 | 월급일 전후 예산 전환 관리 |
| 2.2.7 | 예산 분석 (일별 가용, 주별 현황, 카테고리별 소진율) |
| 2.7.1 | 카테고리 관리 |
| 2.7.2 | 수입 & 고정 지출 & 할부 관리 |
| 5.1 | 데이터 모델 (budget_categories, expenses, fixed_expenses, installments, carryover 등) |

---

## 2. 구현 범위

### 2.1 In Scope

#### Phase 1: Core (카테고리 + 지출 + 예산 요약)

**Backend**:
- [ ] `budget_categories` 모델/스키마/서비스/라우터 (CRUD)
  - 기본 카테고리 세트 제공 (식비, 교통, 주거, 문화/여가, 쇼핑, 의료, 교육, 저축, 기타)
  - 카테고리별 월 예산 금액 설정
  - 정렬, 활성/비활성
- [ ] `expenses` 모델/스키마/서비스/라우터 (CRUD)
  - 필수: 날짜, 금액, 카테고리
  - 선택: 메모, 결제수단 (cash/card/transfer), 태그
  - 기간/카테고리 필터, 페이징
- [ ] `budget/summary` API
  - 카테고리별 예산 대비 지출 비율
  - 총 예산 / 총 지출 / 잔여 예산

**Frontend**:
- [ ] 예산 카테고리 관리 UI
- [ ] 지출 기록/목록 UI
- [ ] 예산 요약 대시보드 (카테고리별 소진율 프로그레스 바)

#### Phase 2: 고정비 + 할부금

**Backend**:
- [ ] `fixed_expenses` 모델/스키마/서비스/라우터 (CRUD + toggle)
  - 이름, 금액, 결제일, 카테고리, 결제수단
  - 활성/비활성 토글
- [ ] `installments` 모델/스키마/서비스/라우터 (CRUD + progress)
  - 총 금액, 월 할부금, 결제일, 시작/종료, 총 회차, 납부 회차
  - 진행률 추적, 완료 시 자동 비활성화
- [ ] 가변 예산 계산 (총 예산 - 고정비 - 할부금)

**Frontend**:
- [ ] 고정비 관리 UI (목록, 추가, 수정, 토글)
- [ ] 할부금 관리 UI (목록, 추가, 진행률 표시)
- [ ] 예산 요약에 고정비/할부금 차감 현황 표시

#### Phase 3: 수입 + 이월 정책

**Backend**:
- [ ] `incomes` 모델/스키마/서비스/라우터
  - 유형: salary, side, investment, other
  - 반복 수입 (급여일, 금액)
- [ ] `budget_carryover_settings` 모델/스키마/서비스/라우터
  - 카테고리별 이월 방식 (expire, next_month, savings, investment, deposit)
  - 이월 상한액, 대상 자산/저축/예금 설정
- [ ] `budget_carryover_logs` 모델 (이월 실행 기록)
- [ ] 이월 미리보기 API (현재 소비 추세 기반 예상 이월 금액)

**Frontend**:
- [ ] 수입 관리 UI
- [ ] 카테고리별 이월 정책 설정 UI
- [ ] 이월 예측/기록 조회 UI

#### Phase 4: 월급일 전환 + 예산 분석

**Backend**:
- [ ] 월급일 기준 예산 기간 계산 로직
- [ ] `budget/transition` API (전환 기간 데이터)
- [ ] 예산 분석 API
  - 일별 사용 가능 금액
  - 주별 사용 현황 (주간 평균 예산 배분)
  - 카테고리별 소진율
  - 초과 알림 (80%, 100%)

**Frontend**:
- [ ] 예산 기간 설정 (월급일 기준)
- [ ] 전환 기간 UI (이전/새 예산 탭 전환)
- [ ] 예산 분석 대시보드 (일별 가용, 주별 현황, 소진율 차트)

### 2.2 Out of Scope (1차)

- Celery Beat 자동 차감 스케줄 (수동 기록으로 대체)
- 푸시 알림 (알림 기능은 별도 feature)
- 이월 자동 실행 (수동 실행 + 이력 기록)
- 예산-자산 연동 (투자/예금 이월 시 실제 자산 생성은 향후)

---

## 3. 기술 설계 방향

### 3.1 데이터 모델

PRD 섹션 5.1에 정의된 테이블 구조를 따른다:

| 테이블 | 설명 | 주요 필드 |
|--------|------|-----------|
| `budget_categories` | 예산 카테고리 | name, icon, color, monthly_budget, sort_order, is_active |
| `expenses` | 지출 기록 | category_id, amount, memo, payment_method, tags, spent_at |
| `incomes` | 수입 기록 | type, amount, is_recurring, recurring_day, received_at |
| `fixed_expenses` | 고정 비용 | category_id, name, amount, payment_day, is_active |
| `installments` | 할부금 | category_id, name, total_amount, monthly_amount, payment_day, total/paid_installments |
| `budget_carryover_settings` | 이월 설정 | category_id, carryover_type, carryover_limit, target_asset_id |
| `budget_carryover_logs` | 이월 기록 | category_id, budget_period, carryover_type, amount |

### 3.2 API 엔드포인트 (PRD 기준)

```
Budget Categories
  GET    /api/v1/budget/categories
  POST   /api/v1/budget/categories
  PUT    /api/v1/budget/categories/{id}

Budget Summary
  GET    /api/v1/budget/summary?period=
  GET    /api/v1/budget/transition

Expenses
  GET    /api/v1/expenses
  POST   /api/v1/expenses
  PUT    /api/v1/expenses/{id}
  DELETE /api/v1/expenses/{id}

Fixed Expenses
  GET    /api/v1/fixed-expenses
  POST   /api/v1/fixed-expenses
  PUT    /api/v1/fixed-expenses/{id}
  DELETE /api/v1/fixed-expenses/{id}
  PATCH  /api/v1/fixed-expenses/{id}/toggle

Installments
  GET    /api/v1/installments
  POST   /api/v1/installments
  PUT    /api/v1/installments/{id}
  DELETE /api/v1/installments/{id}
  GET    /api/v1/installments/{id}/progress

Budget Carryover
  GET    /api/v1/budget/carryover/settings
  PUT    /api/v1/budget/carryover/settings/{cat_id}
  GET    /api/v1/budget/carryover/logs
  GET    /api/v1/budget/carryover/preview
```

### 3.3 예산 기간 계산 로직

```
월급일: payday (사용자 설정, 예: 25)
예산 기간: payday일 ~ 다음달 (payday-1)일
  예: 25일 설정 → 1/25 ~ 2/24가 1월 예산 기간

전환 기간 (payday 전후 1주):
  시작: payday - 7일
  종료: payday + 7일

가변 예산:
  = 총 예산 - 고정비 합계 - 할부금 합계

일별 사용 가능 금액:
  = (가변 예산 - 현재까지 가변 지출) ÷ 남은 일수
```

### 3.4 기본 카테고리 세트

| 카테고리 | 아이콘 | 색상 |
|----------|--------|------|
| 식비 | 🍽️ | #FF6B6B |
| 교통 | 🚗 | #4ECDC4 |
| 주거 | 🏠 | #45B7D1 |
| 문화/여가 | 🎬 | #96CEB4 |
| 쇼핑 | 🛍️ | #FFEAA7 |
| 의료 | 🏥 | #DDA0DD |
| 교육 | 📚 | #74B9FF |
| 저축 | 💰 | #00B894 |
| 기타 | 📌 | #B2BEC3 |

### 3.5 Frontend 컴포넌트 구조 (FSD)

```
frontend/src/features/budget/
├── api/index.ts          (React Query hooks)
├── ui/
│   ├── BudgetSummaryCard.tsx    (예산 요약: 총 예산, 지출, 잔여)
│   ├── CategoryBudgetList.tsx   (카테고리별 소진율 프로그레스)
│   ├── ExpenseList.tsx          (지출 목록)
│   ├── AddExpenseModal.tsx      (지출 추가 모달)
│   ├── CategoryManager.tsx      (카테고리 관리)
│   ├── FixedExpenseList.tsx     (고정비 목록)
│   ├── AddFixedExpenseModal.tsx (고정비 추가)
│   ├── InstallmentList.tsx     (할부금 목록)
│   ├── AddInstallmentModal.tsx (할부금 추가)
│   ├── IncomeManager.tsx       (수입 관리)
│   ├── CarryoverSettings.tsx   (이월 정책 설정)
│   ├── BudgetAnalysis.tsx      (예산 분석 대시보드)
│   └── BudgetTransition.tsx    (전환 기간 탭)
```

---

## 4. 의존성

### 4.1 선행 조건

| 의존성 | 상태 | 비고 |
|--------|------|------|
| 인증 (auth) | ✅ 완료 | JWT 인증, get_current_user |
| 자산 관리 (asset-management) | ✅ 완료 | 이월 정책에서 대상 자산 참조 |
| 예금/적금/파킹 (deposit-savings) | ✅ 완료 | 이월 정책에서 예금 계좌 참조 |
| Frontend 라우팅 | ✅ 완료 | `/budget` 경로 설정 완료 (스텁 페이지) |
| Frontend Budget 타입 | ✅ 부분 | `shared/types/index.ts`에 기본 Budget 인터페이스 있음 |

### 4.2 구현 순서 (Phase별)

```
Phase 1: Core (카테고리 + 지출 + 예산 요약)
  Step 1: Backend 모델 (budget_categories, expenses)
  Step 2: Backend 스키마 + 서비스 (CRUD, 예산 요약)
  Step 3: Backend API 라우터
  Step 4: Frontend 타입 확장 + API hooks
  Step 5: Frontend UI (카테고리 관리, 지출 기록, 예산 요약)
  Step 6: 빌드 검증

Phase 2: 고정비 + 할부금
  Step 1: Backend 모델 (fixed_expenses, installments)
  Step 2: Backend 스키마 + 서비스
  Step 3: Backend API 라우터 + 가변 예산 계산
  Step 4: Frontend 타입 + UI

Phase 3: 수입 + 이월 정책
  Step 1: Backend 모델 (incomes, carryover_settings, carryover_logs)
  Step 2: Backend 스키마 + 서비스 (이월 미리보기)
  Step 3: Backend API 라우터
  Step 4: Frontend 타입 + UI

Phase 4: 월급일 전환 + 예산 분석
  Step 1: Backend 예산 기간 계산 로직
  Step 2: Backend 분석 API (일별 가용, 주별, 소진율)
  Step 3: Frontend 전환 UI + 분석 대시보드
  Step 4: 전체 빌드 검증
```

---

## 5. 리스크 및 고려사항

| 리스크 | 영향 | 대응 방안 |
|--------|------|-----------|
| 기능 범위가 매우 큼 | 구현 기간 증가 | Phase별 분리하여 단계적 구현, 각 Phase마다 Design 문서 작성 |
| 예산 기간 계산 복잡도 | 월급일 기준 사이클 경계 처리 | 유틸리티 함수로 분리, edge case 테스트 (월말, 윤년 등) |
| 이월 정책과 자산 연동 | deposit-savings 기능과의 의존성 | 1차에서는 이월 기록만 생성, 실제 자산 생성은 수동 |
| Celery Beat 자동 차감 미구현 | 고정비/할부금 수동 기록 필요 | 1차에서는 수동 기록, 향후 스케줄러 추가 |
| 카테고리 삭제 시 참조 무결성 | expenses, fixed_expenses 등에서 FK 참조 | soft delete (is_active 토글) 권장 |
| Frontend 페이지 크기 | budget 페이지에 많은 컴포넌트 | 탭 구성으로 분리 (요약/지출/고정비/할부/설정) |

---

## 6. 성공 기준

### Phase 1 (Core)
- [ ] 카테고리 CRUD (기본 카테고리 자동 생성 포함)
- [ ] 지출 기록 CRUD (날짜, 금액, 카테고리, 메모, 결제수단)
- [ ] 예산 요약 (카테고리별 예산 대비 소진율)
- [ ] Frontend 예산 관리 페이지 (요약 + 지출 목록 + 카테고리 관리)
- [ ] 기존 기능에 영향 없음 (하위 호환)
- [ ] Frontend 빌드 통과

### Phase 2 (고정비 + 할부금)
- [ ] 고정비 CRUD + 활성/비활성 토글
- [ ] 할부금 CRUD + 진행률 추적 + 완료 시 자동 비활성화
- [ ] 가변 예산 = 총 예산 - 고정비 - 할부금
- [ ] Frontend 고정비/할부금 관리 UI

### Phase 3 (수입 + 이월)
- [ ] 수입 기록 CRUD (급여, 부수입)
- [ ] 카테고리별 이월 정책 설정
- [ ] 이월 미리보기 (현재 소비 추세 기반)
- [ ] 이월 실행 기록

### Phase 4 (월급일 전환 + 분석)
- [ ] 월급일 기준 예산 기간 계산
- [ ] 전환 기간 UI (이전/새 예산 동시 조회)
- [ ] 일별 사용 가능 금액, 주별 사용 현황
- [ ] 카테고리별 소진율 차트
- [ ] 초과 알림 (80%, 100%)

---

## 7. 다음 단계

Plan 승인 후 → `/pdca design budget-management` 로 Phase 1 상세 설계 문서 작성
(Phase 2~4는 각 Phase 완료 후 순차적으로 Design → Do → Check 반복)
