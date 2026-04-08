"""캘린더 서비스 — v2 스키마 기반.

Entry, RecurringSchedule, Account(만기)를 조합해
CalendarEventsResponse(events, day_summaries, month_summary)를 반환한다.
"""

import calendar as cal
import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import select, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.entry import Entry, EntryType
from app.models.recurring_schedule import RecurringSchedule, ScheduleType
from app.schemas.calendar import (
    CalendarEvent,
    CalendarEventType,
    CalendarEventsResponse,
    DaySummary,
    EVENT_COLOR_MAP,
    MonthSummary,
)
from app.services.budget_v2_service import get_or_create_period, get_period_dates

# Entry.type → CalendarEventType 매핑
_INCOME_ENTRY_TYPES = {
    EntryType.INCOME,
    EntryType.DIVIDEND,
    EntryType.INTEREST,
    EntryType.SELL,
}

def _entry_to_calendar_type(entry_type: EntryType) -> str:
    if entry_type in _INCOME_ENTRY_TYPES:
        return CalendarEventType.INCOME
    return CalendarEventType.EXPENSE


def _schedule_to_calendar_type(schedule_type: ScheduleType) -> str:
    if schedule_type == ScheduleType.INCOME:
        return CalendarEventType.INCOME
    # EXPENSE / TRANSFER → 고정비 취급
    return CalendarEventType.FIXED_EXPENSE


async def get_calendar_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
) -> CalendarEventsResponse:
    """월별 캘린더 이벤트 조회 — CalendarEventsResponse 반환."""
    # ──────────────────────────────────────────────
    # 1. 예산 기간 (budget_period_start / end)
    # ──────────────────────────────────────────────
    budget_period = await get_or_create_period(db, user_id)
    # 해당 연월의 1일을 기준으로 예산 기간을 계산
    from calendar import monthrange as _mr
    _, _max_day = _mr(year, month)
    reference_day = date(year, month, min(budget_period.period_start_day, _max_day))
    # 해당 달에 기간 시작일이 있으면 그 기간, 없으면 이전달 시작일 기간
    period_start, period_end = get_period_dates(budget_period.period_start_day, reference_day)
    # 보정: reference_day가 기간 시작일과 같으면 OK, 아니면 한달 후로 이동
    if period_start.month != month and period_start.year != year:
        # 기간이 조회 월을 벗어날 경우 재계산하지 않고 None으로
        period_start = None
        period_end = None

    # ──────────────────────────────────────────────
    # 2. 실제 발생한 Entry 조회
    # ──────────────────────────────────────────────
    entries_stmt = (
        select(Entry)
        .where(
            Entry.user_id == user_id,
            extract("year", Entry.transacted_at) == year,
            extract("month", Entry.transacted_at) == month,
        )
        .order_by(Entry.transacted_at)
    )
    entries = (await db.execute(entries_stmt)).scalars().all()

    # ──────────────────────────────────────────────
    # 3. 예정 스케줄 조회 (아직 이번달 실행 안 된 것)
    # ──────────────────────────────────────────────
    schedules_stmt = select(RecurringSchedule).where(
        RecurringSchedule.user_id == user_id,
        RecurringSchedule.is_active.is_(True),
    )
    all_schedules = (await db.execute(schedules_stmt)).scalars().all()

    _, last_day_of_month = cal.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day_of_month)

    # 이번 달에 실행된 스케줄 ID 집합 수집
    executed_ids_stmt = (
        select(Entry.recurring_schedule_id)
        .where(
            Entry.user_id == user_id,
            Entry.recurring_schedule_id.is_not(None),
            extract("year", Entry.transacted_at) == year,
            extract("month", Entry.transacted_at) == month,
        )
    )
    executed_ids = {
        row[0] for row in (await db.execute(executed_ids_stmt)).all()
    }

    pending_schedules: list[RecurringSchedule] = []
    for s in all_schedules:
        # 기간 내에 있는 스케줄인지 확인
        if s.end_date and s.end_date < month_start:
            continue
        if s.start_date > month_end:
            continue
        # 이미 실행된 것은 건너뜀
        if s.id in executed_ids:
            continue
        pending_schedules.append(s)

    # ──────────────────────────────────────────────
    # 4. 만기 계좌 조회
    # ──────────────────────────────────────────────
    maturity_stmt = select(Account).where(
        Account.user_id == user_id,
        Account.maturity_date.is_not(None),
        extract("year", Account.maturity_date) == year,
        extract("month", Account.maturity_date) == month,
    )
    maturities = (await db.execute(maturity_stmt)).scalars().all()

    # ──────────────────────────────────────────────
    # 5. CalendarEvent 목록 조성
    # ──────────────────────────────────────────────
    events: list[CalendarEvent] = []

    for e in entries:
        cal_type = _entry_to_calendar_type(e.type)
        color = EVENT_COLOR_MAP.get(cal_type, "#6B7280")
        title = e.memo or e.type.value
        events.append(
            CalendarEvent(
                date=e.transacted_at.date(),
                type=cal_type,
                title=title,
                amount=float(e.amount),
                color=color,
                description=None,
                source_asset_name=None,
            )
        )

    for s in pending_schedules:
        sched_day = last_day_of_month if s.schedule_day <= 0 else min(s.schedule_day, last_day_of_month)
        cal_type = _schedule_to_calendar_type(s.type)
        color = EVENT_COLOR_MAP.get(cal_type, "#6B7280")
        events.append(
            CalendarEvent(
                date=date(year, month, sched_day),
                type=cal_type,
                title=s.name,
                amount=float(s.amount),
                color=color,
                description=s.memo,
                source_asset_name=None,
            )
        )

    for acc in maturities:
        events.append(
            CalendarEvent(
                date=acc.maturity_date,
                type=CalendarEventType.MATURITY,
                title=f"{acc.name} 만기",
                amount=0.0,
                color=EVENT_COLOR_MAP[CalendarEventType.MATURITY],
                description=None,
                source_asset_name=acc.name,
            )
        )

    # 날짜순 정렬
    events.sort(key=lambda ev: ev.date)

    # ──────────────────────────────────────────────
    # 6. DaySummary 계산
    # ──────────────────────────────────────────────
    _EXPENSE_CAL_TYPES = {CalendarEventType.EXPENSE, CalendarEventType.FIXED_EXPENSE, CalendarEventType.INSTALLMENT}
    _INCOME_CAL_TYPES = {CalendarEventType.INCOME, CalendarEventType.MATURITY}

    day_data: dict[date, dict] = defaultdict(lambda: {
        "total_expense": 0.0,
        "total_income": 0.0,
        "event_types": set(),
    })

    for ev in events:
        d = ev.date
        if ev.type in _EXPENSE_CAL_TYPES:
            day_data[d]["total_expense"] += ev.amount
        elif ev.type in _INCOME_CAL_TYPES:
            day_data[d]["total_income"] += ev.amount
        day_data[d]["event_types"].add(ev.type)

    day_summaries: list[DaySummary] = []
    for d, info in sorted(day_data.items()):
        total_exp = info["total_expense"]
        total_inc = info["total_income"]
        day_summaries.append(
            DaySummary(
                date=d,
                total_amount=total_inc - total_exp,
                total_expense=total_exp,
                total_income=total_inc,
                event_count=len([ev for ev in events if ev.date == d]),
                event_types=list(info["event_types"]),
            )
        )

    # ──────────────────────────────────────────────
    # 7. MonthSummary 계산
    # ──────────────────────────────────────────────
    total_expense_amount = sum(
        ev.amount for ev in events if ev.type in _EXPENSE_CAL_TYPES
    )
    total_income_amount = sum(
        ev.amount for ev in events if ev.type in _INCOME_CAL_TYPES
    )
    total_scheduled_amount = sum(float(s.amount) for s in pending_schedules)
    maturity_count = len(maturities)

    month_summary = MonthSummary(
        year=year,
        month=month,
        total_scheduled_amount=total_scheduled_amount,
        total_expense_amount=total_expense_amount,
        total_income_amount=total_income_amount,
        event_count=len(events),
        maturity_count=maturity_count,
        budget_period_start=period_start,
        budget_period_end=period_end,
    )

    return CalendarEventsResponse(
        events=events,
        day_summaries=day_summaries,
        month_summary=month_summary,
    )
