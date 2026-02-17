# Design: Calendar (금융 일정 캘린더)

> **Feature**: calendar
> **Created**: 2026-02-13
> **Plan Reference**: `docs/01-plan/features/calendar.plan.md`
> **PDCA Phase**: Design

---

## 1. Backend 상세 설계

### 1.1 Pydantic 스키마

**파일**: `backend/app/schemas/calendar.py`

```python
from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class CalendarEventType:
    """캘린더 이벤트 유형 상수"""
    FIXED_EXPENSE = "fixed_expense"
    INSTALLMENT = "installment"
    MATURITY = "maturity"
    EXPENSE = "expense"


class CalendarEvent(BaseModel):
    """캘린더 이벤트"""
    date: date
    type: str  # CalendarEventType 값
    title: str
    amount: float
    color: str  # HEX 색상 코드
    description: str | None = None  # 보조 설명 (카테고리명, 은행명 등)
    payment_method: str | None = None


class DaySummary(BaseModel):
    """일자별 요약"""
    date: date
    total_amount: float
    event_count: int
    event_types: list[str]  # 해당 일자에 존재하는 이벤트 유형 목록


class MonthSummary(BaseModel):
    """월 요약"""
    year: int
    month: int
    total_scheduled_amount: float  # 고정비 + 할부 예정 총액
    total_expense_amount: float  # 실제 지출 총액
    event_count: int
    maturity_count: int  # 만기 도래 건수


class CalendarEventsResponse(BaseModel):
    """캘린더 이벤트 응답"""
    events: list[CalendarEvent]
    day_summaries: list[DaySummary]
    month_summary: MonthSummary
```

**이벤트 색상 매핑:**

```python
EVENT_COLOR_MAP = {
    CalendarEventType.FIXED_EXPENSE: "#6B7280",  # Gray
    CalendarEventType.INSTALLMENT: "#3B82F6",    # Blue
    CalendarEventType.MATURITY: "#10B981",        # Green
    CalendarEventType.EXPENSE: "#EF4444",          # Red
}
```

---

### 1.2 서비스 레이어

**파일**: `backend/app/services/calendar_service.py`

```python
import asyncio
import hashlib
import json
import logging
import uuid
from calendar import monthrange
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.models.asset import Asset, AssetType
from app.models.budget import BudgetCategory, Expense, FixedExpense, Installment
from app.schemas.calendar import (
    CalendarEvent,
    CalendarEventType,
    CalendarEventsResponse,
    DaySummary,
    EVENT_COLOR_MAP,
    MonthSummary,
)

logger = logging.getLogger(__name__)

CALENDAR_CACHE_TTL = 300  # 5분

MATURITY_ASSET_TYPES = {AssetType.DEPOSIT, AssetType.SAVINGS}


async def get_calendar_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
    redis_client: redis.Redis | None = None,
) -> CalendarEventsResponse:
    """
    월별 캘린더 이벤트를 조합하여 반환.

    4개 데이터 소스를 병렬 조회:
    1. FixedExpense → 매월 payment_day에 반복
    2. Installment → start_date~end_date 범위 내 payment_day
    3. Asset(만기) → maturity_date가 해당 월인 경우
    4. Expense → spent_at이 해당 월인 경우
    """
    cache_key = f"calendar:{user_id}:{year}:{month}"

    # 1. 캐시 확인
    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return CalendarEventsResponse.model_validate_json(cached)
        except Exception:
            logger.warning(f"Redis cache read failed for {cache_key}")

    # 2. 날짜 범위 계산
    _, last_day = monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    # 3. 병렬 조회
    fixed_expenses, installments, maturity_assets, expenses = await asyncio.gather(
        _get_fixed_expenses(db, user_id),
        _get_installments(db, user_id, month_start, month_end),
        _get_maturity_assets(db, user_id, month_start, month_end),
        _get_expenses(db, user_id, month_start, month_end),
    )

    # 4. 이벤트 조합
    events: list[CalendarEvent] = []

    # 4-1. 고정비 → 매월 payment_day
    for fe, cat in fixed_expenses:
        if not fe.is_active:
            continue
        day = min(fe.payment_day, last_day)  # 31일 → 해당 월 마지막 날
        events.append(CalendarEvent(
            date=date(year, month, day),
            type=CalendarEventType.FIXED_EXPENSE,
            title=fe.name,
            amount=float(fe.amount),
            color=EVENT_COLOR_MAP[CalendarEventType.FIXED_EXPENSE],
            description=cat.name if cat else None,
            payment_method=fe.payment_method.value if fe.payment_method else None,
        ))

    # 4-2. 할부 → 범위 내 payment_day
    for inst, cat in installments:
        if not inst.is_active:
            continue
        day = min(inst.payment_day, last_day)
        events.append(CalendarEvent(
            date=date(year, month, day),
            type=CalendarEventType.INSTALLMENT,
            title=inst.name,
            amount=float(inst.monthly_amount),
            color=EVENT_COLOR_MAP[CalendarEventType.INSTALLMENT],
            description=f"{inst.paid_installments}/{inst.total_installments}회" + (f" ({cat.name})" if cat else ""),
            payment_method=inst.payment_method.value if inst.payment_method else None,
        ))

    # 4-3. 만기 도래
    for asset in maturity_assets:
        events.append(CalendarEvent(
            date=asset.maturity_date,
            type=CalendarEventType.MATURITY,
            title=f"{asset.name} 만기",
            amount=float(asset.principal) if asset.principal else 0,
            color=EVENT_COLOR_MAP[CalendarEventType.MATURITY],
            description=asset.bank_name,
        ))

    # 4-4. 지출 내역 (일자별 합산)
    expense_by_day: dict[date, list[tuple]] = {}
    for exp, cat in expenses:
        expense_by_day.setdefault(exp.spent_at, []).append((exp, cat))

    for day_date, day_expenses in expense_by_day.items():
        total = sum(float(e.amount) for e, _ in day_expenses)
        count = len(day_expenses)
        events.append(CalendarEvent(
            date=day_date,
            type=CalendarEventType.EXPENSE,
            title=f"지출 {count}건",
            amount=total,
            color=EVENT_COLOR_MAP[CalendarEventType.EXPENSE],
            description=f"총 {count}건의 지출",
        ))

    # 5. 정렬 (날짜순 → 유형순)
    type_order = {
        CalendarEventType.MATURITY: 0,
        CalendarEventType.FIXED_EXPENSE: 1,
        CalendarEventType.INSTALLMENT: 2,
        CalendarEventType.EXPENSE: 3,
    }
    events.sort(key=lambda e: (e.date, type_order.get(e.type, 99)))

    # 6. 일자별 요약 생성
    day_summaries = _build_day_summaries(events)

    # 7. 월 요약 생성
    month_summary = _build_month_summary(events, year, month)

    result = CalendarEventsResponse(
        events=events,
        day_summaries=day_summaries,
        month_summary=month_summary,
    )

    # 8. 캐시 저장
    if redis_client:
        try:
            await redis_client.set(
                cache_key,
                result.model_dump_json(),
                ex=CALENDAR_CACHE_TTL,
            )
        except Exception:
            logger.warning(f"Redis cache write failed for {cache_key}")

    return result


# ─── 내부 조회 함수 ───


async def _get_fixed_expenses(
    db: AsyncSession, user_id: uuid.UUID
) -> list[tuple[FixedExpense, BudgetCategory | None]]:
    """활성 고정비 + 카테고리 조회"""
    stmt = (
        select(FixedExpense, BudgetCategory)
        .outerjoin(BudgetCategory, FixedExpense.category_id == BudgetCategory.id)
        .where(FixedExpense.user_id == user_id, FixedExpense.is_active.is_(True))
    )
    result = await db.execute(stmt)
    return list(result.all())


async def _get_installments(
    db: AsyncSession, user_id: uuid.UUID, month_start: date, month_end: date
) -> list[tuple[Installment, BudgetCategory | None]]:
    """해당 월 범위에 해당하는 활성 할부 + 카테고리 조회"""
    stmt = (
        select(Installment, BudgetCategory)
        .outerjoin(BudgetCategory, Installment.category_id == BudgetCategory.id)
        .where(
            Installment.user_id == user_id,
            Installment.is_active.is_(True),
            Installment.start_date <= month_end,
            Installment.end_date >= month_start,
        )
    )
    result = await db.execute(stmt)
    return list(result.all())


async def _get_maturity_assets(
    db: AsyncSession, user_id: uuid.UUID, month_start: date, month_end: date
) -> list[Asset]:
    """해당 월에 만기 도래하는 예금/적금 조회"""
    stmt = (
        select(Asset)
        .where(
            Asset.user_id == user_id,
            Asset.asset_type.in_([t.value for t in MATURITY_ASSET_TYPES]),
            Asset.maturity_date.isnot(None),
            Asset.maturity_date >= month_start,
            Asset.maturity_date <= month_end,
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_expenses(
    db: AsyncSession, user_id: uuid.UUID, month_start: date, month_end: date
) -> list[tuple[Expense, BudgetCategory | None]]:
    """해당 월 지출 내역 + 카테고리 조회"""
    stmt = (
        select(Expense, BudgetCategory)
        .outerjoin(BudgetCategory, Expense.category_id == BudgetCategory.id)
        .where(
            Expense.user_id == user_id,
            Expense.spent_at >= month_start,
            Expense.spent_at <= month_end,
        )
    )
    result = await db.execute(stmt)
    return list(result.all())


# ─── 요약 생성 ───


def _build_day_summaries(events: list[CalendarEvent]) -> list[DaySummary]:
    """이벤트 목록에서 일자별 요약 생성"""
    day_map: dict[date, dict] = {}
    for e in events:
        if e.date not in day_map:
            day_map[e.date] = {"total": 0.0, "count": 0, "types": set()}
        day_map[e.date]["total"] += e.amount
        day_map[e.date]["count"] += 1
        day_map[e.date]["types"].add(e.type)

    return [
        DaySummary(
            date=d,
            total_amount=info["total"],
            event_count=info["count"],
            event_types=sorted(info["types"]),
        )
        for d, info in sorted(day_map.items())
    ]


def _build_month_summary(
    events: list[CalendarEvent], year: int, month: int
) -> MonthSummary:
    """이벤트 목록에서 월 요약 생성"""
    scheduled = sum(
        e.amount for e in events
        if e.type in {CalendarEventType.FIXED_EXPENSE, CalendarEventType.INSTALLMENT}
    )
    expense_total = sum(
        e.amount for e in events if e.type == CalendarEventType.EXPENSE
    )
    maturity_count = sum(
        1 for e in events if e.type == CalendarEventType.MATURITY
    )

    return MonthSummary(
        year=year,
        month=month,
        total_scheduled_amount=scheduled,
        total_expense_amount=expense_total,
        event_count=len(events),
        maturity_count=maturity_count,
    )
```

**핵심 설계 원칙:**
- **standalone 함수**: dashboard_service 패턴과 동일하게 `async def get_calendar_events(db, user_id, ...)` 형태
- **asyncio.gather**: 4개 데이터 소스 병렬 조회
- **Redis 캐싱**: `calendar:{user_id}:{year}:{month}`, 5분 TTL
- **지출 합산**: 지출은 일자별로 합산하여 1개 이벤트로 변환 (다수 지출 시 성능 최적화)
- **payment_day 보정**: `min(payment_day, last_day)`로 해당 월에 없는 날짜(31일 등) 처리

---

### 1.3 API 엔드포인트

**파일**: `backend/app/api/v1/endpoints/calendar.py`

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.calendar import CalendarEventsResponse
from app.services.calendar_service import get_calendar_events

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get("/events", response_model=CalendarEventsResponse)
async def get_events(
    year: int = Query(..., ge=2020, le=2100, description="조회 연도"),
    month: int = Query(..., ge=1, le=12, description="조회 월"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """월별 캘린더 이벤트 조회"""
    redis = await get_redis()
    return await get_calendar_events(
        db=db,
        user_id=current_user.id,
        year=year,
        month=month,
        redis_client=redis,
    )
```

**API 명세:**

```
GET /api/v1/calendar/events?year=2026&month=2
  - Auth: Required (JWT Bearer)
  - Params:
    - year: 조회 연도 (2020~2100, 필수)
    - month: 조회 월 (1~12, 필수)
  - Response: CalendarEventsResponse
  - 200: 캘린더 이벤트 + 일자별 요약 + 월 요약
  - 401: 인증 실패
  - 422: 파라미터 유효성 오류
```

**라우터 등록 (`backend/app/main.py`):**

```python
from app.api.v1.endpoints import calendar

app.include_router(calendar.router, prefix="/api/v1")
```

---

## 2. Frontend 상세 설계

### 2.1 TypeScript 타입 정의

**파일**: `frontend/src/shared/types/index.ts` (기존 파일에 추가)

```typescript
// ========== Calendar Types ==========

export type CalendarEventType = 'fixed_expense' | 'installment' | 'maturity' | 'expense';

export interface CalendarEvent {
  date: string;  // "2026-02-15"
  type: CalendarEventType;
  title: string;
  amount: number;
  color: string;
  description?: string;
  payment_method?: string;
}

export interface DaySummary {
  date: string;
  total_amount: number;
  event_count: number;
  event_types: CalendarEventType[];
}

export interface MonthSummary {
  year: number;
  month: number;
  total_scheduled_amount: number;
  total_expense_amount: number;
  event_count: number;
  maturity_count: number;
}

export interface CalendarEventsResponse {
  events: CalendarEvent[];
  day_summaries: DaySummary[];
  month_summary: MonthSummary;
}
```

---

### 2.2 TanStack Query Hook

**파일**: `frontend/src/features/calendar/api/index.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type { CalendarEventsResponse } from '@/shared/types';

export const calendarKeys = {
  all: ['calendar'] as const,
  events: (year: number, month: number) =>
    [...calendarKeys.all, 'events', year, month] as const,
};

export function useCalendarEvents(year: number, month: number) {
  return useQuery({
    queryKey: calendarKeys.events(year, month),
    queryFn: async (): Promise<CalendarEventsResponse> => {
      const { data } = await apiClient.get(
        `/v1/calendar/events?year=${year}&month=${month}`,
      );
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
```

---

### 2.3 상수 & 유틸

**파일**: `frontend/src/features/calendar/lib/constants.ts`

```typescript
import type { CalendarEventType } from '@/shared/types';

export const EVENT_TYPE_CONFIG: Record<
  CalendarEventType,
  { label: string; color: string; bgColor: string }
> = {
  fixed_expense: { label: '고정비', color: '#6B7280', bgColor: 'bg-gray-100' },
  installment: { label: '할부', color: '#3B82F6', bgColor: 'bg-blue-100' },
  maturity: { label: '만기', color: '#10B981', bgColor: 'bg-green-100' },
  expense: { label: '지출', color: '#EF4444', bgColor: 'bg-red-100' },
};

export const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'] as const;
```

**파일**: `frontend/src/features/calendar/lib/utils.ts`

```typescript
/**
 * 해당 월의 캘린더 그리드 데이터를 생성.
 * 7열 x N행 (이전 달 / 현재 달 / 다음 달 날짜 포함)
 */
export function getCalendarDays(year: number, month: number): CalendarDay[] {
  const firstDay = new Date(year, month - 1, 1);
  const lastDay = new Date(year, month, 0);
  const startDayOfWeek = firstDay.getDay(); // 0(일) ~ 6(토)
  const totalDays = lastDay.getDate();

  const days: CalendarDay[] = [];

  // 이전 달 날짜 (빈 칸)
  const prevLastDay = new Date(year, month - 1, 0).getDate();
  for (let i = startDayOfWeek - 1; i >= 0; i--) {
    days.push({
      date: new Date(year, month - 2, prevLastDay - i),
      isCurrentMonth: false,
    });
  }

  // 현재 달 날짜
  for (let d = 1; d <= totalDays; d++) {
    days.push({
      date: new Date(year, month - 1, d),
      isCurrentMonth: true,
    });
  }

  // 다음 달 날짜 (6행 채우기)
  const remaining = 42 - days.length;
  for (let d = 1; d <= remaining; d++) {
    days.push({
      date: new Date(year, month, d),
      isCurrentMonth: false,
    });
  }

  return days;
}

export interface CalendarDay {
  date: Date;
  isCurrentMonth: boolean;
}

/** "2026-02-15" → Date 비교용 문자열 생성 */
export function toDateString(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** 금액 포맷 */
export function formatAmount(amount: number): string {
  if (amount >= 10000) {
    return `${Math.round(amount / 10000)}만`;
  }
  return amount.toLocaleString();
}
```

---

### 2.4 UI 컴포넌트 설계

#### 2.4.1 컴포넌트 트리

```
pages/calendar/index.tsx
├── MonthSummaryCard              # 월 요약 카드
├── CalendarHeader                # 월 네비게이션 (< 2026년 2월 >)
├── CalendarGrid                  # 달력 그리드
│   └── CalendarDayCell (반복)    # 개별 날짜 셀 (이벤트 dot)
├── EventList                     # 선택 날짜 이벤트 목록
└── CalendarSkeleton              # 로딩 스켈레톤
```

#### 2.4.2 컴포넌트 상세

**CalendarHeader** — `features/calendar/ui/CalendarHeader.tsx`

```
┌────────────────────────────────────────────┐
│    <       2026년 2월       >    [오늘]    │
└────────────────────────────────────────────┘
```

```typescript
interface Props {
  year: number;
  month: number;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
}

export function CalendarHeader({ year, month, onPrev, onNext, onToday }: Props) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <button
          onClick={onPrev}
          className="rounded-lg p-2 hover:bg-gray-100"
        >
          <span className="text-gray-600">&lt;</span>
        </button>
        <h2 className="text-lg font-semibold">
          {year}년 {month}월
        </h2>
        <button
          onClick={onNext}
          className="rounded-lg p-2 hover:bg-gray-100"
        >
          <span className="text-gray-600">&gt;</span>
        </button>
      </div>
      <button
        onClick={onToday}
        className="rounded-lg border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
      >
        오늘
      </button>
    </div>
  );
}
```

- Props: `year`, `month`, `onPrev`, `onNext`, `onToday`
- 이전/다음 월 버튼 + 오늘 버튼

**CalendarGrid** — `features/calendar/ui/CalendarGrid.tsx`

```
┌──────────────────────────────────────────────┐
│  일    월    화    수    목    금    토        │
├──────────────────────────────────────────────┤
│       1     2     3     4     5     6        │
│       ●           ●●                         │
│  7    8     9    10    11    12    13        │
│            ●                ●●●              │
│ ...                                          │
└──────────────────────────────────────────────┘
```

```typescript
import type { DaySummary } from '@/shared/types';
import { WEEKDAYS } from '../lib/constants';
import { getCalendarDays, toDateString } from '../lib/utils';
import { CalendarDayCell } from './CalendarDayCell';

interface Props {
  year: number;
  month: number;
  selectedDate: string | null;  // "2026-02-15"
  daySummaries: DaySummary[];
  onSelectDate: (date: string) => void;
}

export function CalendarGrid({ year, month, selectedDate, daySummaries, onSelectDate }: Props) {
  const days = getCalendarDays(year, month);
  const summaryMap = new Map(daySummaries.map((s) => [s.date, s]));
  const today = toDateString(new Date());

  return (
    <div className="rounded-xl border bg-white">
      {/* 요일 헤더 */}
      <div className="grid grid-cols-7 border-b">
        {WEEKDAYS.map((day, i) => (
          <div
            key={day}
            className={`py-2 text-center text-xs font-medium ${
              i === 0 ? 'text-red-400' : i === 6 ? 'text-blue-400' : 'text-gray-500'
            }`}
          >
            {day}
          </div>
        ))}
      </div>

      {/* 날짜 그리드 */}
      <div className="grid grid-cols-7">
        {days.map((day) => {
          const dateStr = toDateString(day.date);
          return (
            <CalendarDayCell
              key={dateStr}
              date={day.date}
              isCurrentMonth={day.isCurrentMonth}
              isToday={dateStr === today}
              isSelected={dateStr === selectedDate}
              summary={summaryMap.get(dateStr)}
              onClick={() => onSelectDate(dateStr)}
            />
          );
        })}
      </div>
    </div>
  );
}
```

- Props: `year`, `month`, `selectedDate`, `daySummaries`, `onSelectDate`
- 7x6 그리드 (42셀)
- 요일 헤더: 일(빨강), 토(파랑), 나머지(회색)

**CalendarDayCell** — `features/calendar/ui/CalendarDayCell.tsx`

```typescript
import type { DaySummary } from '@/shared/types';
import { EVENT_TYPE_CONFIG } from '../lib/constants';

interface Props {
  date: Date;
  isCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  summary?: DaySummary;
  onClick: () => void;
}

export function CalendarDayCell({
  date,
  isCurrentMonth,
  isToday,
  isSelected,
  summary,
  onClick,
}: Props) {
  return (
    <button
      onClick={onClick}
      className={`flex h-14 flex-col items-center justify-start gap-0.5 border-b border-r p-1 transition-colors md:h-20 ${
        !isCurrentMonth ? 'text-gray-300' : ''
      } ${isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
    >
      <span
        className={`text-xs md:text-sm ${
          isToday
            ? 'flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-white'
            : ''
        }`}
      >
        {date.getDate()}
      </span>

      {/* 이벤트 dot 표시 */}
      {summary && (
        <div className="flex gap-0.5">
          {summary.event_types.map((type) => (
            <span
              key={type}
              className="h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: EVENT_TYPE_CONFIG[type].color }}
            />
          ))}
        </div>
      )}
    </button>
  );
}
```

- 오늘: 파란 원 배경 + 흰 텍스트
- 선택된 날: `bg-blue-50`
- 이벤트 dot: 이벤트 유형별 색상 (최대 4개)
- 모바일 `h-14` / 데스크톱 `md:h-20`

**EventList** — `features/calendar/ui/EventList.tsx`

```
선택된 날짜: 2월 15일 (토)
┌──────────────────────────────────────────┐
│ ● 통신비                    45,000원     │
│   고정비 · 카드                          │
├──────────────────────────────────────────┤
│ ● 삼성카드 할부             120,000원    │
│   할부 3/12회                            │
├──────────────────────────────────────────┤
│ ● 지출 3건                   52,000원    │
│   총 3건의 지출                          │
└──────────────────────────────────────────┘
```

```typescript
import type { CalendarEvent } from '@/shared/types';
import { EVENT_TYPE_CONFIG } from '../lib/constants';

interface Props {
  date: string;  // "2026-02-15"
  events: CalendarEvent[];
}

export function EventList({ date, events }: Props) {
  if (events.length === 0) {
    return (
      <div className="rounded-xl border bg-white p-6 text-center">
        <p className="text-sm text-gray-500">이 날에는 일정이 없습니다.</p>
      </div>
    );
  }

  const d = new Date(date);
  const label = `${d.getMonth() + 1}월 ${d.getDate()}일`;

  return (
    <div className="rounded-xl border bg-white">
      <div className="border-b px-4 py-3">
        <p className="text-sm font-medium text-gray-700">{label}</p>
      </div>
      <div className="divide-y">
        {events.map((event, i) => {
          const config = EVENT_TYPE_CONFIG[event.type];
          return (
            <div key={i} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3 min-w-0">
                <span
                  className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                  style={{ backgroundColor: config.color }}
                />
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{event.title}</p>
                  <p className="text-xs text-gray-500 truncate">
                    {config.label}
                    {event.description ? ` · ${event.description}` : ''}
                    {event.payment_method ? ` · ${event.payment_method}` : ''}
                  </p>
                </div>
              </div>
              <span className="ml-2 flex-shrink-0 text-sm font-medium">
                {event.amount.toLocaleString()}원
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- Props: `date`, `events`
- 빈 상태: "이 날에는 일정이 없습니다."
- 이벤트 아이템: 색상 dot + 제목 + 설명 + 금액

**MonthSummaryCard** — `features/calendar/ui/MonthSummaryCard.tsx`

```
┌──────────────────────────────────────────┐
│  2월 요약                                │
│                                          │
│  예정 결제    580,000원    만기 1건       │
│  실제 지출    420,000원    총 12건        │
└──────────────────────────────────────────┘
```

```typescript
import type { MonthSummary } from '@/shared/types';

interface Props {
  summary: MonthSummary;
}

export function MonthSummaryCard({ summary }: Props) {
  return (
    <div className="rounded-xl border bg-white p-4">
      <p className="text-sm font-medium text-gray-700">{summary.month}월 요약</p>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-gray-500">예정 결제</p>
          <p className="text-lg font-bold">
            {summary.total_scheduled_amount.toLocaleString()}
            <span className="text-xs font-normal text-gray-500">원</span>
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">실제 지출</p>
          <p className="text-lg font-bold">
            {summary.total_expense_amount.toLocaleString()}
            <span className="text-xs font-normal text-gray-500">원</span>
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">만기 도래</p>
          <p className="text-sm font-semibold">{summary.maturity_count}건</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">총 이벤트</p>
          <p className="text-sm font-semibold">{summary.event_count}건</p>
        </div>
      </div>
    </div>
  );
}
```

**CalendarSkeleton** — `features/calendar/ui/CalendarSkeleton.tsx`

```typescript
export function CalendarSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* 월 요약 스켈레톤 */}
      <div className="rounded-xl border bg-white p-4">
        <div className="h-4 w-16 rounded bg-gray-200" />
        <div className="mt-3 grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i}>
              <div className="h-3 w-12 rounded bg-gray-200" />
              <div className="mt-1 h-6 w-24 rounded bg-gray-200" />
            </div>
          ))}
        </div>
      </div>

      {/* 캘린더 그리드 스켈레톤 */}
      <div className="rounded-xl border bg-white p-4">
        <div className="grid grid-cols-7 gap-1">
          {Array.from({ length: 35 }).map((_, i) => (
            <div key={i} className="h-14 rounded bg-gray-100 md:h-20" />
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

### 2.5 페이지 레이아웃

**파일**: `frontend/src/pages/calendar/index.tsx`

```typescript
import { useState } from 'react';
import { useCalendarEvents } from '@/features/calendar/api';
import { CalendarHeader } from '@/features/calendar/ui/CalendarHeader';
import { CalendarGrid } from '@/features/calendar/ui/CalendarGrid';
import { EventList } from '@/features/calendar/ui/EventList';
import { MonthSummaryCard } from '@/features/calendar/ui/MonthSummaryCard';
import { CalendarSkeleton } from '@/features/calendar/ui/CalendarSkeleton';

export function Component() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const { data, isLoading, isError } = useCalendarEvents(year, month);

  const handlePrev = () => {
    if (month === 1) {
      setYear(year - 1);
      setMonth(12);
    } else {
      setMonth(month - 1);
    }
    setSelectedDate(null);
  };

  const handleNext = () => {
    if (month === 12) {
      setYear(year + 1);
      setMonth(1);
    } else {
      setMonth(month + 1);
    }
    setSelectedDate(null);
  };

  const handleToday = () => {
    const today = new Date();
    setYear(today.getFullYear());
    setMonth(today.getMonth() + 1);
    setSelectedDate(null);
  };

  const selectedEvents = selectedDate
    ? (data?.events.filter((e) => e.date === selectedDate) ?? [])
    : [];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">캘린더</h1>

      {isLoading && <CalendarSkeleton />}

      {isError && (
        <div className="rounded-xl border bg-white p-12 text-center">
          <p className="text-gray-500">캘린더를 불러올 수 없습니다.</p>
        </div>
      )}

      {data && (
        <>
          <MonthSummaryCard summary={data.month_summary} />

          <CalendarHeader
            year={year}
            month={month}
            onPrev={handlePrev}
            onNext={handleNext}
            onToday={handleToday}
          />

          <CalendarGrid
            year={year}
            month={month}
            selectedDate={selectedDate}
            daySummaries={data.day_summaries}
            onSelectDate={setSelectedDate}
          />

          {selectedDate && (
            <EventList date={selectedDate} events={selectedEvents} />
          )}
        </>
      )}
    </div>
  );
}
```

**라우트 등록** (`frontend/src/app/routes/index.tsx`):

```typescript
{
  path: '/calendar',
  lazy: () => import('@/pages/calendar'),
},
```

---

## 3. 에러 처리 전략

### 3.1 Backend

| 상황 | 처리 |
|------|------|
| 잘못된 year/month 파라미터 | FastAPI Query 유효성 검증 (422) |
| Redis 연결 실패 | 캐시 없이 직접 DB 조회 (graceful degradation) |
| 데이터 없음 (신규 사용자) | 빈 events + 0 요약 반환 |

### 3.2 Frontend

| 상황 | 처리 |
|------|------|
| API 로딩 중 | CalendarSkeleton 표시 |
| API 에러 | "캘린더를 불러올 수 없습니다." 메시지 |
| 선택 날짜에 이벤트 없음 | "이 날에는 일정이 없습니다." |
| 날짜 미선택 | EventList 렌더링하지 않음 |

---

## 4. 구현 순서 (Implementation Order)

```
Step 1: Backend — 스키마
  └── backend/app/schemas/calendar.py

Step 2: Backend — 서비스
  └── backend/app/services/calendar_service.py

Step 3: Backend — 엔드포인트 & 등록
  ├── backend/app/api/v1/endpoints/calendar.py
  └── backend/app/main.py (라우터 등록 추가)

Step 4: Frontend — 타입 & API Hook
  ├── frontend/src/shared/types/index.ts (Calendar 타입 추가)
  └── frontend/src/features/calendar/api/index.ts

Step 5: Frontend — 상수 & 유틸
  ├── frontend/src/features/calendar/lib/constants.ts
  └── frontend/src/features/calendar/lib/utils.ts

Step 6: Frontend — UI 컴포넌트
  ├── features/calendar/ui/CalendarHeader.tsx
  ├── features/calendar/ui/CalendarGrid.tsx
  ├── features/calendar/ui/CalendarDayCell.tsx
  ├── features/calendar/ui/EventList.tsx
  ├── features/calendar/ui/MonthSummaryCard.tsx
  └── features/calendar/ui/CalendarSkeleton.tsx

Step 7: Frontend — 페이지 통합 & 라우트
  ├── frontend/src/pages/calendar/index.tsx
  └── frontend/src/app/routes/index.tsx (라우트 추가)
```

---

## 5. 검증 체크리스트

Design → Do 전환 시 다음 항목을 구현 검증 기준으로 사용:

- [ ] **BE-1**: `CalendarEvent`, `DaySummary`, `MonthSummary`, `CalendarEventsResponse` Pydantic 스키마 정의
- [ ] **BE-2**: `CalendarEventType` 상수 + `EVENT_COLOR_MAP` 정의
- [ ] **BE-3**: `get_calendar_events()` — 4개 소스 asyncio.gather 병렬 조회 + Redis 5분 캐싱
- [ ] **BE-4**: 고정비 → payment_day 이벤트 변환 (`min(payment_day, last_day)` 보정)
- [ ] **BE-5**: 할부 → start_date~end_date 범위 필터링 + payment_day 이벤트 변환
- [ ] **BE-6**: 만기 → maturity_date가 해당 월인 Asset 조회
- [ ] **BE-7**: 지출 → 일자별 합산 이벤트 변환
- [ ] **BE-8**: `_build_day_summaries()` + `_build_month_summary()` 요약 생성
- [ ] **BE-9**: `GET /api/v1/calendar/events` 엔드포인트 — year, month 필수 파라미터
- [ ] **BE-10**: `main.py`에 calendar 라우터 등록
- [ ] **FE-1**: `CalendarEvent`, `DaySummary`, `MonthSummary`, `CalendarEventsResponse`, `CalendarEventType` 타입 정의
- [ ] **FE-2**: `useCalendarEvents` — useQuery hook (year, month)
- [ ] **FE-3**: `EVENT_TYPE_CONFIG` 이벤트 유형 상수 (label, color, bgColor)
- [ ] **FE-4**: `getCalendarDays()` + `toDateString()` + `formatAmount()` 유틸 함수
- [ ] **FE-5**: `CalendarHeader` — 월 네비게이션 (이전/다음/오늘 버튼)
- [ ] **FE-6**: `CalendarGrid` — 7열 그리드, 요일 헤더, DaySummary 기반 dot 표시
- [ ] **FE-7**: `CalendarDayCell` — 오늘 하이라이트, 선택 상태, 이벤트 dot
- [ ] **FE-8**: `EventList` — 선택 날짜 이벤트 목록 + Empty State
- [ ] **FE-9**: `MonthSummaryCard` — 예정 결제/실제 지출/만기/총 이벤트 요약
- [ ] **FE-10**: `CalendarSkeleton` — animate-pulse 로딩 스켈레톤
- [ ] **FE-11**: 캘린더 페이지 통합 (요약+헤더+그리드+이벤트 목록)
- [ ] **FE-12**: `/calendar` 라우트 등록

---

## 6. 다음 단계

Design 승인 후 → `/pdca do calendar` 로 구현 시작
