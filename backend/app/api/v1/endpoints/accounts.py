import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.account import (
    AccountCreate,
    AccountResponse,
    AccountSummary,
    AccountUpdate,
    AdjustBalanceRequest,
)
from app.schemas.entry import EntryResponse
from app.services import account_service, entry_service

router = APIRouter(tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await account_service.get_accounts(db, current_user.id)


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await account_service.create_account(
        db, current_user.id, data.model_dump()
    )


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await account_service.get_account(db, current_user.id, account_id)


@router.get("/{account_id}/summary", response_model=AccountSummary)
async def get_account_summary(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await account_service.get_account_summary(db, current_user.id, account_id)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await account_service.update_account(
        db, current_user.id, account_id, data.model_dump(exclude_unset=True)
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await account_service.delete_account(db, current_user.id, account_id)


@router.post("/{account_id}/adjust", response_model=EntryResponse)
async def adjust_balance(
    account_id: uuid.UUID,
    data: AdjustBalanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = await entry_service.adjust_balance(
        db,
        user_id=current_user.id,
        account_id=account_id,
        target_balance=data.target_balance,
        currency=data.currency,
        memo=data.memo,
        security_id=data.security_id,
        target_quantity=data.target_quantity,
        unit_price=data.unit_price,
    )
    await db.commit()
    await db.refresh(entry)
    return entry
