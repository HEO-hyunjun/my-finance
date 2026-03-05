import uuid
from datetime import date, timedelta

from app.core.tz import today as tz_today

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.portfolio import AssetSnapshot
from app.schemas.dashboard import (
    DashboardAssetSummary,
    DashboardBudgetCategory,
    DashboardBudgetSummary,
    DashboardMarketInfo,
    DashboardMarketItem,
    DashboardMaturityAlert,
    DashboardPayment,
    DashboardSummaryResponse,
    DashboardTransaction,
)
from app.services.asset_service import get_asset_summary
from app.services.budget_service import (
    get_budget_summary,
    get_fixed_expenses,
    get_installments,
)
from app.services.budget_analysis_service import get_budget_analysis
from app.services.market_service import MarketService
from app.services.transaction_service import get_transactions

MATURITY_TYPES = {AssetType.DEPOSIT, AssetType.SAVINGS}


async def get_dashboard_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    market: MarketService,
    redis=None,
    salary_day: int = 1,
) -> DashboardSummaryResponse:
    """대시보드 통합 데이터를 매번 계산하여 반환. 시세는 개별 Redis 캐시 사용."""

    today = tz_today()

    # 시세: 캐시 전용 (yfinance 호출 없음)
    exchange_rate_raw = await market.get_cached_exchange_rate()
    if not exchange_rate_raw:
        # 캐시 없으면 fallback으로 한번만 fetch
        try:
            exchange_rate_raw = await market.get_exchange_rate()
        except Exception:
            from app.schemas.market import ExchangeRateResponse
            exchange_rate_raw = ExchangeRateResponse(
                pair="USD/KRW", rate=0, cached=False
            )

    gold_price_raw = await market.get_cached_price("KRX:GOLD", AssetType.GOLD)

    # DB 쿼리 (순차 - 단일 연결에서 동시 쿼리 불가)
    asset_summary_raw = await get_asset_summary(db, user_id, market)
    budget_summary_raw = await get_budget_summary(db, user_id, salary_day=salary_day)
    transactions_raw = await get_transactions(db, user_id, page=1, per_page=5)
    fixed_expenses_raw = await get_fixed_expenses(db, user_id)
    installments_raw = await get_installments(db, user_id)
    budget_analysis_raw = await _safe_get_budget_analysis(db, user_id, salary_day=salary_day)

    # 만기 임박 예금/적금 조회
    maturity_alerts = await _get_maturity_alerts(db, user_id, today)

    # 전일대비 등락 계산
    yesterday = today - timedelta(days=1)
    prev_snapshot = await _get_previous_snapshot(db, user_id, yesterday)

    # 응답 조합
    result = DashboardSummaryResponse(
        asset_summary=_map_asset_summary(asset_summary_raw, prev_snapshot),
        budget_summary=_map_budget_summary(budget_summary_raw, budget_analysis_raw),
        recent_transactions=_map_transactions(transactions_raw),
        market_info=_map_market_info(exchange_rate_raw, gold_price_raw),
        upcoming_payments=_map_payments(fixed_expenses_raw, installments_raw, today),
        maturity_alerts=maturity_alerts,
    )

    return result


async def _safe_get_budget_analysis(
    db: AsyncSession, user_id: uuid.UUID, salary_day: int = 1
):
    try:
        return await get_budget_analysis(db, user_id, salary_day=salary_day)
    except Exception:
        return None


async def _safe_get_gold_price(market: MarketService):
    """KRX 금시장 시세 조회 (KRW/g). 실패 시 None 반환."""
    try:
        return await market.get_krx_gold_price()
    except Exception:
        return None


async def _get_maturity_alerts(
    db: AsyncSession,
    user_id: uuid.UUID,
    today: date,
    days_threshold: int = 30,
) -> list[DashboardMaturityAlert]:
    deadline = today + timedelta(days=days_threshold)
    stmt = (
        select(Asset)
        .where(
            Asset.user_id == user_id,
            Asset.asset_type.in_([t.value for t in MATURITY_TYPES]),
            Asset.maturity_date.isnot(None),
            Asset.maturity_date <= deadline,
            Asset.maturity_date >= today,
        )
        .order_by(Asset.maturity_date.asc())
    )
    result = await db.execute(stmt)
    assets = result.scalars().all()

    alerts = []
    for a in assets:
        days_remaining = (a.maturity_date - today).days
        alerts.append(
            DashboardMaturityAlert(
                name=a.name,
                asset_type=a.asset_type.value,
                maturity_date=a.maturity_date,
                principal=float(a.principal) if a.principal else 0,
                maturity_amount=None,
                days_remaining=days_remaining,
                bank_name=a.bank_name,
            )
        )
    return alerts


async def _get_previous_snapshot(
    db: AsyncSession, user_id: uuid.UUID, target_date: date
) -> AssetSnapshot | None:
    """최근 스냅샷 조회 (target_date 이하에서 가장 최신)"""
    stmt = (
        select(AssetSnapshot)
        .where(
            AssetSnapshot.user_id == user_id,
            AssetSnapshot.snapshot_date <= target_date,
        )
        .order_by(AssetSnapshot.snapshot_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _map_asset_summary(raw, prev_snapshot: AssetSnapshot | None = None) -> DashboardAssetSummary:
    daily_change = None
    daily_change_rate = None
    if prev_snapshot and prev_snapshot.total_krw:
        prev_total = float(prev_snapshot.total_krw)
        if prev_total > 0:
            daily_change = round(raw.total_value_krw - prev_total)
            daily_change_rate = round((daily_change / prev_total) * 100, 2)

    return DashboardAssetSummary(
        total_value_krw=raw.total_value_krw,
        total_invested_krw=raw.total_invested_krw,
        total_profit_loss=raw.total_profit_loss,
        total_profit_loss_rate=raw.total_profit_loss_rate,
        daily_change=daily_change,
        daily_change_rate=daily_change_rate,
        breakdown=raw.breakdown,
    )


def _map_budget_summary(raw, analysis=None) -> DashboardBudgetSummary:
    top_cats = sorted(raw.categories, key=lambda c: c.usage_rate, reverse=True)[:5]

    daily_available = 0.0
    today_spent = 0.0
    remaining_days = 0
    if analysis:
        daily_available = analysis.daily_budget.daily_available
        today_spent = analysis.daily_budget.today_spent
        remaining_days = analysis.daily_budget.remaining_days

    return DashboardBudgetSummary(
        total_budget=raw.total_budget,
        total_spent=raw.total_spent,
        total_remaining=raw.total_remaining,
        total_usage_rate=raw.total_usage_rate,
        total_fixed_expenses=raw.total_fixed_expenses,
        total_installments=raw.total_installments,
        daily_available=daily_available,
        today_spent=today_spent,
        remaining_days=remaining_days,
        top_categories=[
            DashboardBudgetCategory(
                name=c.category_name,
                icon=c.category_icon,
                color=c.category_color,
                budget=c.monthly_budget,
                spent=c.spent,
                usage_rate=c.usage_rate,
            )
            for c in top_cats
        ],
    )


def _map_transactions(raw) -> list[DashboardTransaction]:
    return [
        DashboardTransaction(
            id=str(tx.id),
            asset_name=tx.asset_name,
            asset_type=tx.asset_type,
            type=tx.type.value if hasattr(tx.type, "value") else tx.type,
            quantity=tx.quantity,
            unit_price=tx.unit_price,
            currency=tx.currency.value if hasattr(tx.currency, "value") else tx.currency,
            transacted_at=tx.transacted_at,
        )
        for tx in raw.data
    ]


def _map_market_info(exchange_rate_raw, gold_price_raw) -> DashboardMarketInfo:
    return DashboardMarketInfo(
        exchange_rate=DashboardMarketItem(
            symbol="USD/KRW",
            name="미국 달러",
            price=exchange_rate_raw.rate if exchange_rate_raw else 0,
            currency="KRW",
            change=exchange_rate_raw.change if exchange_rate_raw else None,
            change_percent=exchange_rate_raw.change_percent if exchange_rate_raw else None,
        ),
        gold_price=(
            DashboardMarketItem(
                symbol=gold_price_raw.symbol,
                name="금",
                price=gold_price_raw.price,
                currency=gold_price_raw.currency,
                change=gold_price_raw.change,
                change_percent=gold_price_raw.change_percent,
            )
            if gold_price_raw
            else None
        ),
    )


def _map_payments(fixed_expenses, installments, today: date) -> list[DashboardPayment]:
    payments: list[DashboardPayment] = []
    current_day = today.day

    for fe in fixed_expenses:
        if fe.is_active and fe.payment_day >= current_day:
            payments.append(
                DashboardPayment(
                    name=fe.name,
                    amount=fe.amount,
                    payment_day=fe.payment_day,
                    type="fixed",
                    category_name=fe.category_name,
                    category_color=fe.category_color,
                )
            )

    for inst in installments:
        if inst.is_active and inst.payment_day >= current_day and inst.remaining_installments > 0:
            payments.append(
                DashboardPayment(
                    name=inst.name,
                    amount=inst.monthly_amount,
                    payment_day=inst.payment_day,
                    type="installment",
                    remaining=f"{inst.paid_installments}/{inst.total_installments}",
                    category_name=inst.category_name,
                    category_color=inst.category_color,
                )
            )

    payments.sort(key=lambda p: p.payment_day)
    return payments
