# Plan: Calendar (금융 일정 캘린더)

> **Feature**: calendar
> **Created**: 2026-02-13
> **PDCA Phase**: Plan
> **Level**: Dynamic

---

## 1. 기능 개요

### 1.1 목적

기존에 분산된 금융 일정 정보(고정비 결제일, 할부 결제일, 예금/적금 만기일, 일별 지출 내역)를 **월별 캘린더 뷰** 하나로 통합하여, 사용자가 한눈에 자신의 금융 일정을 파악할 수 있게 한다.

### 1.2 핵심 가치

- **기존 데이터 재활용**: 새 DB 테이블 없이 기존 FixedExpense, Installment, Asset(만기), Expense 데이터를 조합
- **시각적 통합**: 흩어진 금융 이벤트를 달력 형태로 한눈에 조회
- **모바일 친화**: 날짜 클릭 시 해당 일의 이벤트 목록을 아래에 표시

---

## 2. 기존 데이터 소스 분석

| 데이터 소스 | 테이블/서비스 | 캘린더 이벤트 변환 |
|-------------|--------------|-------------------|
| 고정비 | `FixedExpense` (budget_service) | 매월 `payment_day`일에 반복 이벤트 |
| 할부 | `Installment` (budget_service) | `start_date` ~ `end_date` 범위 내 매월 `payment_day`일 |
| 예금/적금 만기 | `Asset` (asset_service) | `maturity_date`에 1회 이벤트 |
| 지출 내역 | `Expense` (budget_service) | `spent_at` 날짜에 실제 지출 이벤트 |

**새 DB 테이블: 불필요** (기존 데이터 조합만으로 충분)

---

## 3. 기능 범위 (Scope)

### 3.1 포함 (In-Scope)

| # | 기능 | 설명 |
|---|------|------|
| 1 | 월별 캘린더 뷰 | 달력 그리드에 이벤트 dot 표시 |
| 2 | 날짜 선택 시 이벤트 목록 | 선택한 날짜의 금융 이벤트 리스트 |
| 3 | 이벤트 유형 구분 | 고정비(회색), 할부(파랑), 만기(초록), 지출(빨강) 색상 구분 |
| 4 | 월 이동 | 이전/다음 월 네비게이션 |
| 5 | 오늘 표시 | 오늘 날짜 하이라이트 |
| 6 | 월 요약 | 이번 달 총 예정 지출액, 이벤트 수 요약 |
| 7 | API 엔드포인트 | `GET /api/v1/calendar/events?year=2026&month=2` |

### 3.2 제외 (Out-of-Scope)

- 커스텀 일정 등록/수정/삭제 (별도 calendar_events 테이블 필요)
- 알림/리마인더 (Push notification)
- 주간 뷰 / 일간 뷰
- 드래그 앤 드롭 일정 이동
- Google Calendar 연동

---

## 4. 기술 설계 방향

### 4.1 Backend

- **새 서비스**: `CalendarService` — 기존 4개 데이터 소스를 조합하여 월별 이벤트 목록 생성
- **API**: `GET /api/v1/calendar/events` — year, month 파라미터로 해당 월의 모든 금융 이벤트 반환
- **캐싱**: Redis 5분 TTL (기존 데이터 변경이 잦지 않으므로)
- **응답 구조**: `CalendarEventsResponse` — 날짜별 이벤트 그룹핑

### 4.2 Frontend

- **캘린더 라이브러리**: 직접 구현 (7x6 그리드, 외부 라이브러리 불필요)
- **상태 관리**: useState로 currentMonth, selectedDate 관리
- **API Hook**: TanStack Query `useCalendarEvents(year, month)`
- **컴포넌트 구조**:
  - `CalendarGrid` — 월별 달력 그리드
  - `CalendarHeader` — 월 네비게이션 (이전/다음 월)
  - `CalendarDayCell` — 개별 날짜 셀 (이벤트 dot 표시)
  - `EventList` — 선택 날짜의 이벤트 목록
  - `MonthSummary` — 월 요약 카드

---

## 5. 이벤트 유형 정의

| 유형 | 코드 | 색상 | 아이콘 | 소스 |
|------|------|------|--------|------|
| 고정비 결제 | `fixed_expense` | Gray (#6B7280) | 반복 | FixedExpense.payment_day |
| 할부 결제 | `installment` | Blue (#3B82F6) | 카드 | Installment.payment_day |
| 만기 도래 | `maturity` | Green (#10B981) | 달러 | Asset.maturity_date |
| 지출 기록 | `expense` | Red (#EF4444) | 마이너스 | Expense.spent_at |

---

## 6. 성공 기준

| # | 기준 | 측정 방법 |
|---|------|----------|
| 1 | 캘린더 API 응답에 4가지 이벤트 유형 포함 | API 테스트 |
| 2 | 월별 캘린더 그리드 정상 렌더링 | UI 확인 |
| 3 | 날짜 클릭 시 해당 일자 이벤트 목록 표시 | UI 확인 |
| 4 | 이전/다음 월 네비게이션 작동 | UI 확인 |
| 5 | 오늘 날짜 하이라이트 | UI 확인 |
| 6 | 이벤트 유형별 색상 구분 | UI 확인 |
| 7 | 월 요약 (총 예정 지출, 이벤트 수) 표시 | UI 확인 |
| 8 | 빈 달에 Empty State 표시 | UI 확인 |
| 9 | 모바일 반응형 레이아웃 | UI 확인 |
| 10 | Redis 캐싱 (5분 TTL) 적용 | 로그 확인 |

---

## 7. 리스크

| # | 리스크 | 영향 | 대응 |
|---|--------|------|------|
| 1 | 데이터 조합 쿼리 성능 | 중 | asyncio.gather로 병렬 조회, Redis 캐싱 |
| 2 | 고정비 payment_day가 해당 월에 없는 경우 (예: 31일) | 저 | 해당 월 마지막 날로 대체 |
| 3 | 지출 내역이 많은 월 | 저 | 지출은 일자별 합산 금액만 표시 (개수 + 총액) |
| 4 | 할부 종료일 이후에도 표시되는 경우 | 저 | is_active 및 날짜 범위 필터링 |

---

## 8. 구현 순서

```
Phase 1: Backend — 스키마 + 서비스 + API
  ├── schemas/calendar.py (CalendarEvent, CalendarEventsResponse)
  ├── services/calendar_service.py (4개 소스 조합)
  ├── api/v1/endpoints/calendar.py (GET /calendar/events)
  └── main.py (라우터 등록)

Phase 2: Frontend — 타입 + API Hook + 상수
  ├── shared/types/index.ts (Calendar 타입 추가)
  ├── features/calendar/api/index.ts (useCalendarEvents hook)
  └── features/calendar/lib/constants.ts (이벤트 유형 색상 매핑)

Phase 3: Frontend — UI 컴포넌트
  ├── features/calendar/ui/CalendarHeader.tsx
  ├── features/calendar/ui/CalendarGrid.tsx
  ├── features/calendar/ui/CalendarDayCell.tsx
  ├── features/calendar/ui/EventList.tsx
  └── features/calendar/ui/MonthSummary.tsx

Phase 4: Frontend — 페이지 통합
  ├── pages/calendar/index.tsx
  └── app/routes/index.tsx (라우트 등록)
```

---

## 9. 다음 단계

Plan 승인 후 -> `/pdca design calendar` 로 상세 설계 시작
