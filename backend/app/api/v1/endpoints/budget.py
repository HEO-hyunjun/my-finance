"""예산 관리 API 엔드포인트.

Budget v2: top-down 방식 (수입 - 고정지출 - 자동이체 = 가용예산 → 카테고리 배분)
기존 budget_analysis_service는 유지합니다.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.tz import today as tz_today
from app.models.user import User
from app.schemas.budget import (
    AllocationCreate,
    AllocationUpdate,
    BudgetOverviewResponse,
    CategoryBudgetResponse,
    PeriodSettingUpdate,
)
from app.schemas.budget_analysis import BudgetAnalysisResponse
from app.services import budget_analysis_service, budget_v2_service

router = APIRouter(tags=["budget"])


# --- Overview ---


@router.get("/overview", response_model=BudgetOverviewResponse)
async def get_budget_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top-down 예산 개요: 수입 - 고정지출 - 자동이체 = 가용예산"""
    today = tz_today()
    return await budget_v2_service.get_budget_overview(db, current_user.id, today)


# --- Category Budgets ---


@router.get("/categories", response_model=list[CategoryBudgetResponse])
async def list_category_budgets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """카테고리별 배분 + 실제 지출 + 잔여"""
    today = tz_today()
    return await budget_v2_service.get_category_budgets(db, current_user.id, today)


# --- Allocations ---


@router.post("/allocations", status_code=status.HTTP_201_CREATED)
async def create_allocation(
    data: AllocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """예산 카테고리 배분 생성 (이미 존재하면 업데이트)"""
    today = tz_today()
    alloc = await budget_v2_service.create_or_update_allocation(
        db, current_user.id, data.category_id, data.amount, today,
    )
    return {
        "allocation_id": str(alloc.id),
        "category_id": str(alloc.category_id),
        "amount": alloc.amount,
        "period_start": alloc.period_start.isoformat(),
        "period_end": alloc.period_end.isoformat(),
    }


@router.patch("/allocations/{allocation_id}")
async def update_allocation(
    allocation_id: uuid.UUID,
    data: AllocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """예산 배분 금액 수정"""
    # 기존 allocation 조회하여 category_id를 가져옴
    from sqlalchemy import select
    from app.models.budget_v2 import BudgetAllocation

    stmt = select(BudgetAllocation).where(
        BudgetAllocation.id == allocation_id,
        BudgetAllocation.user_id == current_user.id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allocation not found",
        )

    today = tz_today()
    alloc = await budget_v2_service.create_or_update_allocation(
        db, current_user.id, existing.category_id, data.amount, today,
    )
    return {
        "allocation_id": str(alloc.id),
        "category_id": str(alloc.category_id),
        "amount": alloc.amount,
        "period_start": alloc.period_start.isoformat(),
        "period_end": alloc.period_end.isoformat(),
    }


@router.delete(
    "/allocations/{allocation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_allocation(
    allocation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """예산 배분 삭제"""
    await budget_v2_service.delete_allocation(db, current_user.id, allocation_id)


# --- Period ---


@router.get("/period")
async def get_period(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """사용자의 예산 기간 설정 조회"""
    period = await budget_v2_service.get_or_create_period(db, current_user.id)
    return {
        "period_start_day": period.period_start_day,
    }


@router.patch("/period")
async def update_period(
    data: PeriodSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """예산 기간 시작일 변경 (1-28)"""
    period = await budget_v2_service.update_period_start_day(
        db, current_user.id, data.period_start_day,
    )
    return {
        "period_start_day": period.period_start_day,
    }


# --- Analysis (기존 유지) ---


@router.get("/analysis", response_model=BudgetAnalysisResponse)
async def get_budget_analysis(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_analysis_service.get_budget_analysis(
        db,
        current_user.id,
        start,
        end,
    )
