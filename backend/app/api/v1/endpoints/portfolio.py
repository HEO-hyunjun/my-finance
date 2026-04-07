"""포트폴리오 관리 API 엔드포인트.

TODO: Phase 2 - asset_service를 새 스키마(Account, Entry) 기반으로 교체 예정.
현재 asset_service가 삭제되어 자산 요약이 필요한 엔드포인트는 501을 반환합니다.
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
    # TODO: Phase 2 - asset_service.get_asset_summary를 새 서비스로 교체
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Snapshot creation is being migrated to new schema. Coming in Phase 2.",
    )


# --- Goal ---


@router.get("/goal", response_model=GoalAssetResponse | None)
async def get_goal(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # TODO: Phase 2 - asset_service.get_asset_summary를 새 서비스로 교체
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Goal API requires asset summary which is being migrated. Coming in Phase 2.",
    )


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
    # TODO: Phase 2 - asset_service.get_asset_summary를 새 서비스로 교체
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Targets API requires asset summary which is being migrated. Coming in Phase 2.",
    )


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
    # TODO: Phase 2 - asset_service.get_asset_summary를 새 서비스로 교체
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Rebalancing API requires asset summary which is being migrated. Coming in Phase 2.",
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
