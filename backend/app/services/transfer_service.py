import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.asset import Asset
from app.models.auto_transfer import AutoTransfer
from app.models.transaction import Transaction, TransactionType


async def execute_transfer(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_asset_id: uuid.UUID,
    target_asset_id: uuid.UUID,
    amount: Decimal,
    memo: str | None = None,
    transacted_at: datetime | None = None,
) -> dict:
    """이체 실행: 출처에서 WITHDRAW + 대상에 DEPOSIT 생성"""
    if source_asset_id == target_asset_id:
        raise HTTPException(status_code=400, detail="Same source and target asset")

    # 자산 소유권 확인
    source = await _get_user_asset(db, user_id, source_asset_id)
    target = await _get_user_asset(db, user_id, target_asset_id)

    ts = transacted_at or datetime.now(timezone.utc)
    transfer_memo = memo or f"{source.name} → {target.name} 이체"

    # 출금
    withdraw_tx = Transaction(
        user_id=user_id,
        asset_id=source_asset_id,
        type=TransactionType.WITHDRAW,
        quantity=amount,
        unit_price=Decimal("1"),
        currency="KRW",
        memo=transfer_memo,
        transacted_at=ts,
    )
    # 입금
    deposit_tx = Transaction(
        user_id=user_id,
        asset_id=target_asset_id,
        type=TransactionType.DEPOSIT,
        quantity=amount,
        unit_price=Decimal("1"),
        currency="KRW",
        memo=transfer_memo,
        transacted_at=ts,
    )
    db.add(withdraw_tx)
    db.add(deposit_tx)
    await db.commit()

    return {
        "source": source.name,
        "target": target.name,
        "amount": float(amount),
    }


# ── 자동이체 CRUD ──

async def get_auto_transfers(
    db: AsyncSession, user_id: uuid.UUID
) -> list[dict]:
    result = await db.execute(
        select(AutoTransfer)
        .where(AutoTransfer.user_id == user_id)
        .options(
            selectinload(AutoTransfer.source_asset),
            selectinload(AutoTransfer.target_asset),
        )
        .order_by(AutoTransfer.transfer_day)
    )
    items = result.scalars().all()
    return [_to_response(item) for item in items]


async def create_auto_transfer(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: dict,
) -> dict:
    # 자산 소유권 확인
    await _get_user_asset(db, user_id, data["source_asset_id"])
    await _get_user_asset(db, user_id, data["target_asset_id"])

    if data["source_asset_id"] == data["target_asset_id"]:
        raise HTTPException(status_code=400, detail="Same source and target asset")

    item = AutoTransfer(
        user_id=user_id,
        source_asset_id=data["source_asset_id"],
        target_asset_id=data["target_asset_id"],
        name=data["name"],
        amount=Decimal(str(data["amount"])),
        transfer_day=data["transfer_day"],
    )
    db.add(item)
    await db.commit()
    await db.refresh(item, attribute_names=["source_asset", "target_asset"])
    return _to_response(item)


async def toggle_auto_transfer(
    db: AsyncSession, user_id: uuid.UUID, transfer_id: uuid.UUID
) -> dict:
    item = await _get_user_auto_transfer(db, user_id, transfer_id)
    item.is_active = not item.is_active
    await db.commit()
    await db.refresh(item, attribute_names=["source_asset", "target_asset"])
    return _to_response(item)


async def delete_auto_transfer(
    db: AsyncSession, user_id: uuid.UUID, transfer_id: uuid.UUID
) -> None:
    item = await _get_user_auto_transfer(db, user_id, transfer_id)
    await db.delete(item)
    await db.commit()


def _to_response(item: AutoTransfer) -> dict:
    return {
        "id": str(item.id),
        "name": item.name,
        "source_asset_id": str(item.source_asset_id),
        "source_asset_name": item.source_asset.name if item.source_asset else None,
        "target_asset_id": str(item.target_asset_id),
        "target_asset_name": item.target_asset.name if item.target_asset else None,
        "amount": float(item.amount),
        "transfer_day": item.transfer_day,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


async def _get_user_asset(
    db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID
) -> Asset:
    stmt = select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id)
    asset = (await db.execute(stmt)).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


async def _get_user_auto_transfer(
    db: AsyncSession, user_id: uuid.UUID, transfer_id: uuid.UUID
) -> AutoTransfer:
    stmt = select(AutoTransfer).where(
        AutoTransfer.id == transfer_id, AutoTransfer.user_id == user_id
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Auto transfer not found")
    return item
