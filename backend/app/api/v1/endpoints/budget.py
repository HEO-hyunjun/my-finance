"""예산 관리 API 엔드포인트.

TODO: Phase 2 - budget_service를 새 스키마(Entry, Category) 기반으로 교체 예정.
현재 budget_service가 삭제되어 카테고리/요약 관련 엔드포인트는 501을 반환합니다.
budget_analysis_service는 유지됩니다.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.budget import (
    BudgetCategoryCreate,
    BudgetCategoryResponse,
    BudgetCategoryUpdate,
    BudgetSummaryResponse,
)
from app.schemas.budget_analysis import BudgetAnalysisResponse
from app.services import budget_analysis_service

router = APIRouter(prefix="/budget", tags=["budget"])


# --- Categories ---
# TODO: Phase 2 - budget_service 재구현 후 복원


@router.get("/categories", response_model=list[BudgetCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Budget categories API is being migrated to new schema. Coming in Phase 2.",
    )


@router.post(
    "/categories",
    response_model=BudgetCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    data: BudgetCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Budget categories API is being migrated to new schema. Coming in Phase 2.",
    )


@router.put("/categories/{category_id}", response_model=BudgetCategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    data: BudgetCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Budget categories API is being migrated to new schema. Coming in Phase 2.",
    )


# --- Summary ---
# TODO: Phase 2 - budget_service.get_budget_summary 재구현 후 복원


@router.get("/summary", response_model=BudgetSummaryResponse)
async def get_budget_summary(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Budget summary API is being migrated to new schema. Coming in Phase 2.",
    )


# --- Analysis ---


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
        salary_day=current_user.salary_day,
    )
