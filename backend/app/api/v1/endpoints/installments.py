import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.budget import (
    InstallmentCreate,
    InstallmentUpdate,
    InstallmentResponse,
)
from app.services import budget_service

router = APIRouter(prefix="/installments", tags=["installments"])


@router.get("", response_model=list[InstallmentResponse])
async def list_installments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.get_installments(db, current_user.id)


@router.post(
    "",
    response_model=InstallmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_installment(
    data: InstallmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.create_installment(db, current_user.id, data)


@router.put("/{inst_id}", response_model=InstallmentResponse)
async def update_installment(
    inst_id: uuid.UUID,
    data: InstallmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.update_installment(
        db, current_user.id, inst_id, data
    )


@router.delete("/{inst_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_installment(
    inst_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await budget_service.delete_installment(db, current_user.id, inst_id)


@router.get("/{inst_id}/progress", response_model=InstallmentResponse)
async def get_installment_progress(
    inst_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await budget_service.get_installment_progress(
        db, current_user.id, inst_id
    )
