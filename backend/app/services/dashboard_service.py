"""대시보드 서비스.

Phase 2 완료: Account/Entry/Security 기반으로 전면 재작성.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, EntryType
from app.models.portfolio import AssetSnapshot
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

    # 5. 계좌 유형별 자산 분포
    type_labels = {
        "cash": "현금",
        "deposit": "예금",
        "savings": "적금",
        "parking": "파킹",
        "investment": "투자",
    }
    type_totals: dict[str, Decimal] = {}
    for acc in total_assets["accounts"]:
        at = acc["account_type"]
        type_totals[at] = type_totals.get(at, Decimal("0")) + acc["total_value_krw"]

    asset_distribution = [
        {
            "type": t,
            "label": type_labels.get(t, t),
            "amount": v,
        }
        for t, v in type_totals.items()
        if v > 0
    ]

    # 6. 전일대비 변동
    total_krw = total_assets["total_krw"]
    yesterday = today - timedelta(days=1)
    prev_snapshot = (
        await db.execute(
            select(AssetSnapshot)
            .where(
                AssetSnapshot.user_id == user_id,
                AssetSnapshot.snapshot_date <= yesterday,
            )
            .order_by(AssetSnapshot.snapshot_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    daily_change = None
    daily_change_rate = None
    if prev_snapshot and prev_snapshot.total_krw:
        prev_total = prev_snapshot.total_krw
        daily_change = float(total_krw - prev_total)
        daily_change_rate = float((total_krw - prev_total) / prev_total) if prev_total else None

    return {
        "total_assets_krw": total_krw,
        "accounts_count": len(total_assets["accounts"]),
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "daily_change": daily_change,
        "daily_change_rate": daily_change_rate,
        "budget_overview": budget,
        "asset_distribution": asset_distribution,
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
