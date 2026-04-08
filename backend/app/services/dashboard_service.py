"""대시보드 서비스.

Phase 2 완료: Account/Entry/Security 기반으로 전면 재작성.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, EntryType
from app.services.portfolio_v2_service import get_total_assets
from app.services.budget_v2_service import get_budget_overview
from app.core.tz import today as tz_today


async def get_dashboard_summary(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> dict:
    """대시보드 통합 데이터 반환.

    kwargs는 기존 API 시그니처 호환을 위해 수용 (market, redis, salary_day 등).
    """
    today = tz_today()

    # 1. 전체 자산 현황
    total_assets = await get_total_assets(db, user_id)

    # 2. 이번 달 수입/지출 요약
    month_start = today.replace(day=1)
    month_start_dt = datetime(
        month_start.year, month_start.month, month_start.day, tzinfo=timezone.utc
    )

    income_stmt = select(func.coalesce(func.sum(Entry.amount), 0)).where(
        Entry.user_id == user_id,
        Entry.type == EntryType.INCOME,
        Entry.transacted_at >= month_start_dt,
    )
    monthly_income = Decimal(str((await db.execute(income_stmt)).scalar()))

    expense_stmt = select(func.coalesce(func.sum(Entry.amount), 0)).where(
        Entry.user_id == user_id,
        Entry.type == EntryType.EXPENSE,
        Entry.transacted_at >= month_start_dt,
    )
    monthly_expense = abs(Decimal(str((await db.execute(expense_stmt)).scalar())))

    # 3. 예산 개요
    budget = await get_budget_overview(db, user_id, today)

    # 4. 최근 거래 5건
    recent_stmt = (
        select(Entry)
        .where(Entry.user_id == user_id)
        .order_by(Entry.transacted_at.desc())
        .limit(5)
    )
    recent_entries = (await db.execute(recent_stmt)).scalars().all()

    return {
        "total_assets_krw": total_assets["total_krw"],
        "accounts_count": len(total_assets["accounts"]),
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "budget_overview": budget,
        "recent_entries": [
            {
                "id": str(e.id),
                "type": e.type.value,
                "amount": e.amount,
                "currency": e.currency,
                "memo": e.memo,
                "transacted_at": e.transacted_at.isoformat(),
            }
            for e in recent_entries
        ],
    }
