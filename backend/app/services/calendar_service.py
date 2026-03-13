import asyncio
import logging
import uuid
from calendar import monthrange
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.models.asset import Asset, AssetType
from app.models.budget import BudgetCategory, Expense, FixedExpense, Installment
from app.models.income import Income, IncomeType, RecurringIncome
from app.services.budget_period import get_budget_period
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
    salary_day: int = 1,
) -> CalendarEventsResponse:
    """
    월별 캘린더 이벤트를 조합하여 반환.

    4개 데이터 소스를 병렬 조회:
    1. FixedExpense → 매월 payment_day에 반복
    2. Installment → start_date~end_date 범위 내 payment_day
    3. Asset(만기) → maturity_date가 해당 월인 경우
    4. Expense → spent_at이 해당 월인 경우
    """
    cache_key = f"calendar:{user_id}:{year}:{month}:{salary_day}"

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
    fixed_expenses, installments, maturity_assets, expenses, incomes, recurring_incomes = await asyncio.gather(
        _get_fixed_expenses(db, user_id),
        _get_installments(db, user_id, month_start, month_end),
        _get_maturity_assets(db, user_id, month_start, month_end),
        _get_expenses(db, user_id, month_start, month_end),
        _get_incomes(db, user_id, month_start, month_end),
        _get_recurring_incomes(db, user_id),
    )

    # 4. 소스 자산 이름 일괄 조회
    all_source_ids: set[uuid.UUID] = set()
    for fe, _ in fixed_expenses:
        if fe.source_asset_id:
            all_source_ids.add(fe.source_asset_id)
    for inst, _ in installments:
        if inst.source_asset_id:
            all_source_ids.add(inst.source_asset_id)
    for exp, _ in expenses:
        if exp.source_asset_id:
            all_source_ids.add(exp.source_asset_id)

    asset_name_cache: dict[uuid.UUID, str] = {}
    if all_source_ids:
        asset_stmt = select(Asset.id, Asset.name).where(Asset.id.in_(all_source_ids))
        asset_rows = (await db.execute(asset_stmt)).all()
        asset_name_cache = {row.id: row.name for row in asset_rows}

    # 5. 이벤트 조합
    events: list[CalendarEvent] = []

    # 5-1. 고정비 → 매월 payment_day (0 = 말일)
    for fe, cat in fixed_expenses:
        if not fe.is_active:
            continue
        day = last_day if fe.payment_day == 0 else min(fe.payment_day, last_day)
        events.append(CalendarEvent(
            date=date(year, month, day),
            type=CalendarEventType.FIXED_EXPENSE,
            title=fe.name,
            amount=float(fe.amount),
            color=EVENT_COLOR_MAP[CalendarEventType.FIXED_EXPENSE],
            description=cat.name if cat else None,
            source_asset_name=asset_name_cache.get(fe.source_asset_id) if fe.source_asset_id else None,
        ))

    # 5-2. 할부 → 범위 내 payment_day (0 = 말일)
    for inst, cat in installments:
        if not inst.is_active:
            continue
        day = last_day if inst.payment_day == 0 else min(inst.payment_day, last_day)
        events.append(CalendarEvent(
            date=date(year, month, day),
            type=CalendarEventType.INSTALLMENT,
            title=inst.name,
            amount=float(inst.monthly_amount),
            color=EVENT_COLOR_MAP[CalendarEventType.INSTALLMENT],
            description=f"{inst.paid_installments}/{inst.total_installments}회" + (f" ({cat.name})" if cat else ""),
            source_asset_name=asset_name_cache.get(inst.source_asset_id) if inst.source_asset_id else None,
        ))

    # 5-3. 만기 도래
    for asset in maturity_assets:
        events.append(CalendarEvent(
            date=asset.maturity_date,
            type=CalendarEventType.MATURITY,
            title=f"{asset.name} 만기",
            amount=float(asset.principal) if asset.principal else 0,
            color=EVENT_COLOR_MAP[CalendarEventType.MATURITY],
            description=asset.bank_name,
        ))

    # 5-4. 지출 내역 (개별 항목)
    for exp, cat in expenses:
        events.append(CalendarEvent(
            date=exp.spent_at,
            type=CalendarEventType.EXPENSE,
            title=exp.memo or (cat.name if cat else "지출"),
            amount=float(exp.amount),
            color=cat.color if cat else EVENT_COLOR_MAP[CalendarEventType.EXPENSE],
            description=cat.name if cat else None,
            source_asset_name=asset_name_cache.get(exp.source_asset_id) if exp.source_asset_id else None,
        ))

    # 5-5. 수입 내역
    INCOME_TYPE_LABELS = {
        IncomeType.SALARY: "급여",
        IncomeType.SIDE: "부수입",
        IncomeType.INVESTMENT: "투자수익",
        IncomeType.OTHER: "기타수입",
    }
    for inc in incomes:
        events.append(CalendarEvent(
            date=inc.received_at,
            type=CalendarEventType.INCOME,
            title=inc.description or INCOME_TYPE_LABELS.get(inc.type, "수입"),
            amount=float(inc.amount),
            color=EVENT_COLOR_MAP[CalendarEventType.INCOME],
            description=INCOME_TYPE_LABELS.get(inc.type, "수입"),
        ))

    # 5-6. 정기 수입 (급여 등) → 해당 월에 실제 기록이 없으면 recurring_day에 표시
    actual_ri_ids = {inc.recurring_income_id for inc in incomes if inc.recurring_income_id}
    for ri in recurring_incomes:
        if ri.id in actual_ri_ids:
            continue
        day = min(ri.recurring_day, last_day)
        events.append(CalendarEvent(
            date=date(year, month, day),
            type=CalendarEventType.INCOME,
            title=ri.description or INCOME_TYPE_LABELS.get(ri.type, "수입"),
            amount=float(ri.amount),
            color=EVENT_COLOR_MAP[CalendarEventType.INCOME],
            description=INCOME_TYPE_LABELS.get(ri.type, "수입") + " (정기)",
        ))

    # 6. 정렬 (날짜순 → 유형순)
    type_order = {
        CalendarEventType.MATURITY: 0,
        CalendarEventType.INCOME: 1,
        CalendarEventType.FIXED_EXPENSE: 2,
        CalendarEventType.INSTALLMENT: 3,
        CalendarEventType.EXPENSE: 4,
    }
    events.sort(key=lambda e: (e.date, type_order.get(e.type, 99)))

    # 7. 일자별 요약 생성 (SQL GROUP BY 2회)
    daily_expenses, daily_incomes = await asyncio.gather(
        _get_daily_expense_totals(db, user_id, month_start, month_end),
        _get_daily_income_totals(db, user_id, month_start, month_end),
    )
    day_summaries = _build_day_summaries(daily_expenses, daily_incomes, events)

    # 8. 월 요약 생성 (급여일 기준 예산 기간)
    ref_date = date(year, month, min(15, last_day))
    budget_start, budget_end = get_budget_period(ref_date, salary_day)

    budget_expense_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.user_id == user_id,
        Expense.spent_at >= budget_start,
        Expense.spent_at <= budget_end,
        Expense.fixed_expense_id.is_(None),
    )
    budget_income_stmt = select(func.coalesce(func.sum(Income.amount), 0)).where(
        Income.user_id == user_id,
        Income.received_at >= budget_start,
        Income.received_at <= budget_end,
    )
    budget_expense_result, budget_income_result = await asyncio.gather(
        db.execute(budget_expense_stmt),
        db.execute(budget_income_stmt),
    )
    budget_expense_total = float(budget_expense_result.scalar() or 0)
    budget_income_total = float(budget_income_result.scalar() or 0)

    scheduled = sum(
        e.amount for e in events
        if e.type in {CalendarEventType.FIXED_EXPENSE, CalendarEventType.INSTALLMENT}
    )
    maturity_count = sum(
        1 for e in events if e.type == CalendarEventType.MATURITY
    )

    month_summary = MonthSummary(
        year=year,
        month=month,
        total_scheduled_amount=scheduled,
        total_expense_amount=budget_expense_total,
        total_income_amount=budget_income_total,
        event_count=len(events),
        maturity_count=maturity_count,
        budget_period_start=budget_start,
        budget_period_end=budget_end,
    )

    result = CalendarEventsResponse(
        events=events,
        day_summaries=day_summaries,
        month_summary=month_summary,
    )

    # 9. 캐시 저장
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


async def _get_incomes(
    db: AsyncSession, user_id: uuid.UUID, month_start: date, month_end: date
) -> list[Income]:
    """해당 월 수입 내역 조회"""
    stmt = (
        select(Income)
        .where(
            Income.user_id == user_id,
            Income.received_at >= month_start,
            Income.received_at <= month_end,
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_recurring_incomes(
    db: AsyncSession, user_id: uuid.UUID,
) -> list[RecurringIncome]:
    """활성 정기 수입 템플릿 조회"""
    stmt = (
        select(RecurringIncome)
        .where(
            RecurringIncome.user_id == user_id,
            RecurringIncome.is_active.is_(True),
        )
        .order_by(RecurringIncome.recurring_day)
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
            Expense.fixed_expense_id.is_(None),
        )
    )
    result = await db.execute(stmt)
    return list(result.all())


# ─── 일별 집계 쿼리 (GROUP BY) ───


async def _get_daily_expense_totals(
    db: AsyncSession, user_id: uuid.UUID, month_start: date, month_end: date
) -> dict[date, tuple[float, int]]:
    """지출 일별 합계·건수를 GROUP BY로 조회 (1 query)"""
    stmt = (
        select(
            Expense.spent_at,
            func.sum(Expense.amount).label("total"),
            func.count().label("cnt"),
        )
        .where(
            Expense.user_id == user_id,
            Expense.spent_at >= month_start,
            Expense.spent_at <= month_end,
            Expense.fixed_expense_id.is_(None),
        )
        .group_by(Expense.spent_at)
    )
    rows = (await db.execute(stmt)).all()
    return {row.spent_at: (float(row.total), row.cnt) for row in rows}


async def _get_daily_income_totals(
    db: AsyncSession, user_id: uuid.UUID, month_start: date, month_end: date
) -> dict[date, tuple[float, int]]:
    """수입 일별 합계·건수를 GROUP BY로 조회 (1 query)"""
    stmt = (
        select(
            Income.received_at,
            func.sum(Income.amount).label("total"),
            func.count().label("cnt"),
        )
        .where(
            Income.user_id == user_id,
            Income.received_at >= month_start,
            Income.received_at <= month_end,
        )
        .group_by(Income.received_at)
    )
    rows = (await db.execute(stmt)).all()
    return {row.received_at: (float(row.total), row.cnt) for row in rows}


# ─── 요약 생성 ───


def _build_day_summaries(
    daily_expenses: dict[date, tuple[float, int]],
    daily_incomes: dict[date, tuple[float, int]],
    events: list[CalendarEvent],
) -> list[DaySummary]:
    """GROUP BY 결과 + 고정비/할부 이벤트로 일자별 요약 생성"""
    all_dates: set[date] = set(daily_expenses.keys()) | set(daily_incomes.keys())

    # 고정비·할부·만기는 DB에 날짜 레코드가 없으므로 이벤트에서 추출
    scheduled_by_day: dict[date, float] = {}
    for e in events:
        if e.type in {CalendarEventType.FIXED_EXPENSE, CalendarEventType.INSTALLMENT, CalendarEventType.MATURITY}:
            scheduled_by_day[e.date] = scheduled_by_day.get(e.date, 0.0) + e.amount
            all_dates.add(e.date)

    # 이벤트 타입 수집 (dot 표시용)
    types_by_day: dict[date, set[str]] = {}
    for e in events:
        types_by_day.setdefault(e.date, set()).add(e.type)

    summaries: list[DaySummary] = []
    for d in sorted(all_dates):
        exp_amount, exp_cnt = daily_expenses.get(d, (0.0, 0))
        inc_amount, inc_cnt = daily_incomes.get(d, (0.0, 0))
        sched_amount = scheduled_by_day.get(d, 0.0)

        total_expense = exp_amount + sched_amount
        total = total_expense + inc_amount
        count = exp_cnt + inc_cnt + (1 if sched_amount > 0 else 0)

        summaries.append(DaySummary(
            date=d,
            total_amount=total,
            total_expense=total_expense,
            total_income=inc_amount,
            event_count=count,
            event_types=sorted(types_by_day.get(d, set())),
        ))

    return summaries


