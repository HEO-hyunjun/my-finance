import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.income import (
    RecurringIncomeCreate,
    RecurringIncomeUpdate,
    RecurringIncomeResponse,
)
from app.services import income_service

router = APIRouter(prefix="/recurring-incomes", tags=["recurring-incomes"])


@router.get("", response_model=list[RecurringIncomeResponse])
async def list_recurring_incomes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await income_service.get_recurring_incomes(db, current_user.id)


@router.post(
    "",
    response_model=RecurringIncomeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recurring_income(
    data: RecurringIncomeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await income_service.create_recurring_income(db, current_user.id, data)


@router.put("/{ri_id}", response_model=RecurringIncomeResponse)
async def update_recurring_income(
    ri_id: uuid.UUID,
    data: RecurringIncomeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await income_service.update_recurring_income(
        db, current_user.id, ri_id, data
    )


@router.delete("/{ri_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring_income(
    ri_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await income_service.delete_recurring_income(db, current_user.id, ri_id)


@router.patch("/{ri_id}/toggle", response_model=RecurringIncomeResponse)
async def toggle_recurring_income(
    ri_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await income_service.toggle_recurring_income(db, current_user.id, ri_id)
