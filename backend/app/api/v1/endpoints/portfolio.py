"""포트폴리오 관리 API 엔드포인트.

Phase 2 완료: portfolio_v2_service 기반으로 자산 요약 제공.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.portfolio import (
    AssetTimelineResponse,
    GoalAssetCreate,
    GoalAssetResponse,
    PortfolioTargetBulkCreate,
    PortfolioTargetResponse,
    RebalancingAlertResponse,
    RebalancingAnalysisResponse,
)
from app.services import portfolio_service
from app.services.portfolio_v2_service import get_total_assets

router = APIRouter(tags=["portfolio"])


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
    total_data = await get_total_assets(db, user.id)
    breakdown = {}
    for acc in total_data["accounts"]:
        atype = acc["account_type"]
        breakdown[atype] = float(
            breakdown.get(atype, 0) + float(acc["total_value_krw"])
        )
    return await portfolio_service.create_snapshot(
        db, user.id, total_data["total_krw"], breakdown
    )


# --- Goal ---


@router.get("/goal", response_model=GoalAssetResponse | None)
async def get_goal(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total_data = await get_total_assets(db, user.id)
    current_amount = float(total_data["total_krw"])
    return await portfolio_service.get_goal(db, user.id, current_amount)


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
    total_data = await get_total_assets(db, user.id)
    breakdown = {}
    for acc in total_data["accounts"]:
        atype = acc["account_type"]
        breakdown[atype] = float(
            breakdown.get(atype, 0) + float(acc["total_value_krw"])
        )
    return await portfolio_service.get_portfolio_targets(db, user.id, breakdown)


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
    total_data = await get_total_assets(db, user.id)
    breakdown = {}
    for acc in total_data["accounts"]:
        atype = acc["account_type"]
        breakdown[atype] = float(
            breakdown.get(atype, 0) + float(acc["total_value_krw"])
        )
    return await portfolio_service.get_rebalancing_analysis(
        db, user.id, breakdown, threshold
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
