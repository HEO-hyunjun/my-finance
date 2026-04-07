"""대시보드 서비스.

TODO: Phase 2 - 새 스키마(Account, Entry)에 맞게 전면 재작성 예정.
현재는 import 오류 방지를 위해 스텁 처리되어 있습니다.
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import AssetSnapshot
from app.schemas.dashboard import (
    DashboardAssetSummary,
    DashboardBudgetSummary,
    DashboardMarketInfo,
    DashboardMarketItem,
    DashboardSummaryResponse,
)
from app.services.market_service import MarketService

# TODO: Phase 2 - rewrite for new schema
# Old imports removed:
# from app.services.asset_service import get_asset_summary
# from app.services.budget_service import get_budget_summary, get_fixed_expenses, get_installments
# from app.services.transaction_service import get_transactions


async def get_dashboard_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    market: MarketService,
    redis=None,
    salary_day: int = 1,
) -> DashboardSummaryResponse:
    """대시보드 통합 데이터 반환.

    TODO: Phase 2 - 새 스키마 기반으로 재작성 필요.
    현재는 시세 정보와 빈 데이터를 반환합니다.
    """
    # 시세: 캐시 전용
    exchange_rate_raw = await market.get_cached_exchange_rate()
    if not exchange_rate_raw:
        try:
            exchange_rate_raw = await market.get_exchange_rate()
        except Exception:
            from app.schemas.market import ExchangeRateResponse

            exchange_rate_raw = ExchangeRateResponse(
                pair="USD/KRW", rate=0, cached=False
            )

    gold_price_raw = None  # TODO: Phase 2

    # TODO: Phase 2 - 전일대비 등락 계산 복원
    # yesterday = today - timedelta(days=1)
    # prev_snapshot = await _get_previous_snapshot(db, user_id, yesterday)

    result = DashboardSummaryResponse(
        asset_summary=DashboardAssetSummary(
            total_value_krw=0,
            total_invested_krw=0,
            total_profit_loss=0,
            total_profit_loss_rate=0,
            daily_change=None,
            daily_change_rate=None,
            breakdown={},
        ),
        budget_summary=DashboardBudgetSummary(
            total_budget=0,
            total_spent=0,
            total_remaining=0,
            total_usage_rate=0,
            total_fixed_expenses=0,
            total_installments=0,
            daily_available=0,
            today_spent=0,
            remaining_days=0,
            top_categories=[],
        ),
        recent_transactions=[],
        market_info=_map_market_info(exchange_rate_raw, gold_price_raw),
        upcoming_payments=[],
        maturity_alerts=[],
    )

    return result


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


def _map_market_info(exchange_rate_raw, gold_price_raw) -> DashboardMarketInfo:
    return DashboardMarketInfo(
        exchange_rate=DashboardMarketItem(
            symbol="USD/KRW",
            name="미국 달러",
            price=exchange_rate_raw.rate if exchange_rate_raw else 0,
            currency="KRW",
            change=exchange_rate_raw.change if exchange_rate_raw else None,
            change_percent=exchange_rate_raw.change_percent
            if exchange_rate_raw
            else None,
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
