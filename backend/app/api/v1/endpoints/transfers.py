import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.transfer_service import (
    execute_transfer,
    get_auto_transfers,
    create_auto_transfer,
    toggle_auto_transfer,
    delete_auto_transfer,
)

router = APIRouter(prefix="/transfers", tags=["Transfers"])


# ── Schemas ──

class TransferRequest(BaseModel):
    source_asset_id: uuid.UUID
    target_asset_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    exchange_rate: Decimal | None = None  # 이종통화 이체 시 환율
    memo: str | None = None
    transacted_at: datetime | None = None


class AutoTransferCreate(BaseModel):
    source_asset_id: uuid.UUID
    target_asset_id: uuid.UUID
    name: str = Field(max_length=100)
    amount: Decimal = Field(gt=0)
    transfer_day: int = Field(ge=1, le=31)


# ── Endpoints ──

@router.post("")
async def transfer(
    data: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """계좌 간 이체 실행"""
    return await execute_transfer(
        db=db,
        user_id=current_user.id,
        source_asset_id=data.source_asset_id,
        target_asset_id=data.target_asset_id,
        amount=data.amount,
        exchange_rate=data.exchange_rate,
        memo=data.memo,
        transacted_at=data.transacted_at,
    )


@router.get("/auto")
async def list_auto_transfers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """자동이체 목록 조회"""
    return await get_auto_transfers(db, current_user.id)


@router.post("/auto")
async def create_auto_transfer_endpoint(
    data: AutoTransferCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """자동이체 등록"""
    return await create_auto_transfer(db, current_user.id, data.model_dump())


@router.patch("/auto/{transfer_id}/toggle")
async def toggle_auto_transfer_endpoint(
    transfer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """자동이체 활성/비활성 토글"""
    return await toggle_auto_transfer(db, current_user.id, transfer_id)


@router.delete("/auto/{transfer_id}")
async def delete_auto_transfer_endpoint(
    transfer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """자동이체 삭제"""
    await delete_auto_transfer(db, current_user.id, transfer_id)
    return {"ok": True}
