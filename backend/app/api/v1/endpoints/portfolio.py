import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.api.deps import get_current_user
from app.models.user import User
from app.services import portfolio_service, asset_service
from app.services.market_service import MarketService
from app.schemas.portfolio import (
    AssetTimelineResponse, GoalAssetCreate, GoalAssetResponse,
    PortfolioTargetBulkCreate, PortfolioTargetResponse,
    RebalancingAnalysisResponse, RebalancingAlertResponse,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# --- Asset Timeline ---

@router.get("/timeline", response_model=AssetTimelineResponse)
async def get_timeline(
    period: str = Query(default="1M", pattern=r"^(1W|1M|3M|6M|1Y|ALL)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.get_asset_timeline(db, user.id, period)


@router.post("/snapshot")
async def create_snapshot(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    redis = get_redis()
    market = MarketService(redis)
    summary = await asset_service.get_asset_summary(db, user.id, market)
    from decimal import Decimal
    snapshot = await portfolio_service.create_snapshot(
        db, user.id,
        total_krw=Decimal(str(summary.total_value_krw)),
        breakdown=summary.breakdown,
    )
    return snapshot


# --- Goal ---

@router.get("/goal", response_model=GoalAssetResponse | None)
async def get_goal(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    redis = get_redis()
    market = MarketService(redis)
    summary = await asset_service.get_asset_summary(db, user.id, market)
    return await portfolio_service.get_goal(db, user.id, summary.total_value_krw)


@router.put("/goal", response_model=GoalAssetResponse)
async def set_goal(
    data: GoalAssetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.upsert_goal(db, user.id, data)


# --- Portfolio Targets ---

@router.get("/targets", response_model=list[PortfolioTargetResponse])
async def get_targets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    redis = get_redis()
    market = MarketService(redis)
    summary = await asset_service.get_asset_summary(db, user.id, market)
    return await portfolio_service.get_portfolio_targets(db, user.id, summary.breakdown)


@router.put("/targets", response_model=list[PortfolioTargetResponse])
async def set_targets(
    data: PortfolioTargetBulkCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return await portfolio_service.set_portfolio_targets(db, user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Rebalancing ---

@router.get("/rebalancing", response_model=RebalancingAnalysisResponse)
async def get_rebalancing(
    threshold: float = Query(default=0.05, ge=0.01, le=0.20),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    redis = get_redis()
    market = MarketService(redis)
    summary = await asset_service.get_asset_summary(db, user.id, market)
    return await portfolio_service.get_rebalancing_analysis(
        db, user.id, summary.breakdown, threshold
    )


@router.get("/alerts", response_model=list[RebalancingAlertResponse])
async def get_alerts(
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.get_rebalancing_alerts(db, user.id, unread_only)


@router.patch("/alerts/{alert_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await portfolio_service.mark_alert_read(db, user.id, alert_id)
