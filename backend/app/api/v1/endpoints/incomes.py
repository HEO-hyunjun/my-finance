import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.income import (
    IncomeCreate, IncomeUpdate, IncomeResponse,
    IncomeListResponse, IncomeSummaryResponse,
)
from app.services import income_service

router = APIRouter(prefix="/incomes", tags=["incomes"])


@router.get("", response_model=IncomeListResponse)
async def list_incomes(
    income_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await income_service.get_incomes(
        db, user.id, income_type, start_date, end_date, page, per_page
    )


@router.post("", response_model=IncomeResponse, status_code=status.HTTP_201_CREATED)
async def create_income(
    data: IncomeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await income_service.create_income(db, user.id, data)


@router.put("/{income_id}", response_model=IncomeResponse)
async def update_income(
    income_id: uuid.UUID,
    data: IncomeUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return await income_service.update_income(db, user.id, income_id, data)
    except ValueError:
        raise HTTPException(status_code=404, detail="Income not found")


@router.delete("/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_income(
    income_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        await income_service.delete_income(db, user.id, income_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Income not found")


@router.get("/summary", response_model=IncomeSummaryResponse)
async def income_summary(
    start: date = Query(...),
    end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await income_service.get_income_summary(db, user.id, start, end)
