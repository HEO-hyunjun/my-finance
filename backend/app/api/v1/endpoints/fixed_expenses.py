import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.budget import (
    FixedExpenseCreate,
    FixedExpenseUpdate,
    FixedExpenseResponse,
)
from app.services import budget_service

router = APIRouter(prefix="/fixed-expenses", tags=["fixed-expenses"])


@router.get("", response_model=list[FixedExpenseResponse])
async def list_fixed_expenses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.get_fixed_expenses(db, current_user.id)


@router.post(
    "",
    response_model=FixedExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_fixed_expense(
    data: FixedExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.create_fixed_expense(db, current_user.id, data)


@router.put("/{fe_id}", response_model=FixedExpenseResponse)
async def update_fixed_expense(
    fe_id: uuid.UUID,
    data: FixedExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.update_fixed_expense(
        db, current_user.id, fe_id, data
    )


@router.delete("/{fe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fixed_expense(
    fe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await budget_service.delete_fixed_expense(db, current_user.id, fe_id)


@router.patch("/{fe_id}/toggle", response_model=FixedExpenseResponse)
async def toggle_fixed_expense(
    fe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.toggle_fixed_expense(db, current_user.id, fe_id)
