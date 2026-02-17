import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.budget import (
    BudgetCategoryCreate,
    BudgetCategoryUpdate,
    BudgetCategoryResponse,
    BudgetSummaryResponse,
)
from app.schemas.budget_analysis import BudgetAnalysisResponse
from app.services import budget_service, budget_analysis_service

router = APIRouter(prefix="/budget", tags=["budget"])


# --- Categories ---


@router.get("/categories", response_model=list[BudgetCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.get_categories(db, current_user.id)


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
    return await budget_service.create_category(db, current_user.id, data)


@router.put("/categories/{category_id}", response_model=BudgetCategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    data: BudgetCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.update_category(
        db, current_user.id, category_id, data
    )


# --- Summary ---


@router.get("/summary", response_model=BudgetSummaryResponse)
async def get_budget_summary(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.get_budget_summary(
        db, current_user.id, start, end,
        salary_day=current_user.salary_day,
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
        db, current_user.id, start, end,
        salary_day=current_user.salary_day,
    )
