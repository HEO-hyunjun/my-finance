import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
)


def _to_response(tx: Transaction, asset: Asset) -> TransactionResponse:
    return TransactionResponse(
        id=tx.id,
        asset_id=tx.asset_id,
        asset_name=asset.name,
        asset_type=asset.asset_type.value,
        type=tx.type,
        quantity=float(tx.quantity),
        unit_price=float(tx.unit_price),
        currency=tx.currency,
        exchange_rate=float(tx.exchange_rate) if tx.exchange_rate else None,
        fee=float(tx.fee),
        memo=tx.memo,
        transacted_at=tx.transacted_at,
        created_at=tx.created_at,
    )


async def create_transaction(
    db: AsyncSession, user_id: uuid.UUID, data: TransactionCreate
) -> TransactionResponse:
    # asset 소유권 확인
    asset = await _get_user_asset(db, user_id, data.asset_id)

    # 매도 시 보유량 초과 체크
    if data.type == TransactionType.SELL:
        available = await _get_available_quantity(db, user_id, data.asset_id)
        if data.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient quantity. Available: {available}, Requested: {data.quantity}",
            )

    tx = Transaction(
        user_id=user_id,
        asset_id=data.asset_id,
        type=data.type,
        quantity=data.quantity,
        unit_price=data.unit_price,
        currency=data.currency,
        exchange_rate=data.exchange_rate,
        fee=data.fee,
        memo=data.memo,
        transacted_at=data.transacted_at,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return _to_response(tx, asset)


async def get_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    asset_id: uuid.UUID | None = None,
    asset_type: str | None = None,
    tx_type: TransactionType | None = None,
    start_date=None,
    end_date=None,
    memo: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> TransactionListResponse:
    base = select(Transaction).where(Transaction.user_id == user_id)

    if asset_id:
        base = base.where(Transaction.asset_id == asset_id)
    if tx_type:
        base = base.where(Transaction.type == tx_type)
    if start_date:
        base = base.where(Transaction.transacted_at >= start_date)
    if end_date:
        base = base.where(Transaction.transacted_at <= end_date)
    if memo:
        for word in memo.split():
            base = base.where(Transaction.memo.ilike(f"%{word}%"))

    # asset_type 필터: join 필요
    if asset_type:
        base = base.join(Asset, Transaction.asset_id == Asset.id).where(
            Asset.asset_type == asset_type
        )

    # 총 개수
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # 페이지네이션
    offset = (page - 1) * per_page
    stmt = base.order_by(Transaction.transacted_at.desc()).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    transactions = result.scalars().all()

    # 단일 IN 쿼리로 필요한 모든 asset을 한번에 조회
    asset_ids = {tx.asset_id for tx in transactions}
    asset_cache: dict[uuid.UUID, Asset] = {}
    if asset_ids:
        asset_stmt = select(Asset).where(Asset.id.in_(asset_ids))
        assets = (await db.execute(asset_stmt)).scalars().all()
        asset_cache = {a.id: a for a in assets}

    responses = []
    for tx in transactions:
        asset = asset_cache.get(tx.asset_id)
        if asset:
            responses.append(_to_response(tx, asset))

    return TransactionListResponse(
        data=responses,
        total=total,
        page=page,
        per_page=per_page,
    )


async def update_transaction(
    db: AsyncSession,
    user_id: uuid.UUID,
    tx_id: uuid.UUID,
    data: TransactionUpdate,
) -> TransactionResponse:
    tx = await _get_user_transaction(db, user_id, tx_id)
    asset = await db.get(Asset, tx.asset_id)

    update_data = data.model_dump(exclude_unset=True)

    # 매도 수량 변경 시 초과 체크
    if "quantity" in update_data and tx.type == TransactionType.SELL:
        new_qty = update_data["quantity"]
        available = await _get_available_quantity(db, user_id, tx.asset_id)
        available += tx.quantity  # 기존 매도 수량 복원
        if new_qty > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient quantity. Available: {available}, Requested: {new_qty}",
            )

    for field, value in update_data.items():
        setattr(tx, field, value)

    await db.commit()
    await db.refresh(tx)
    return _to_response(tx, asset)


async def delete_transaction(
    db: AsyncSession, user_id: uuid.UUID, tx_id: uuid.UUID
) -> None:
    tx = await _get_user_transaction(db, user_id, tx_id)
    await db.delete(tx)
    await db.commit()


async def _get_user_asset(
    db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID
) -> Asset:
    stmt = select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id)
    asset = (await db.execute(stmt)).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


async def _get_user_transaction(
    db: AsyncSession, user_id: uuid.UUID, tx_id: uuid.UUID
) -> Transaction:
    stmt = select(Transaction).where(
        Transaction.id == tx_id, Transaction.user_id == user_id
    )
    tx = (await db.execute(stmt)).scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


async def _get_available_quantity(
    db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID
) -> Decimal:
    """보유량 = buy 합계 - sell 합계"""
    buy_stmt = select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
        Transaction.user_id == user_id,
        Transaction.asset_id == asset_id,
        Transaction.type == TransactionType.BUY,
    )
    sell_stmt = select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
        Transaction.user_id == user_id,
        Transaction.asset_id == asset_id,
        Transaction.type == TransactionType.SELL,
    )

    buy_total = (await db.execute(buy_stmt)).scalar() or Decimal("0")
    sell_total = (await db.execute(sell_stmt)).scalar() or Decimal("0")
    return buy_total - sell_total
