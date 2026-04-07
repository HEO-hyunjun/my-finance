import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
)

# 현금성 자산 (입금/출금 가능, 매수 출처로 사용 가능)
CASH_LIKE_TYPES = {AssetType.CASH_KRW, AssetType.CASH_USD, AssetType.PARKING}
# principal 추적 대상 (이자 계산에 사용)
_PRINCIPAL_TYPES = {AssetType.PARKING, AssetType.DEPOSIT, AssetType.SAVINGS}


def _to_response(
    tx: Transaction, asset: Asset, source_asset_name: str | None = None
) -> TransactionResponse:
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
        source_asset_id=tx.source_asset_id,
        source_asset_name=source_asset_name,
        transacted_at=tx.transacted_at,
        created_at=tx.created_at,
    )


async def create_transaction(
    db: AsyncSession, user_id: uuid.UUID, data: TransactionCreate
) -> TransactionResponse:
    # asset 소유권 확인
    asset = await _get_user_asset(db, user_id, data.asset_id)

    source_asset_name: str | None = None

    # 매도/출금 시 보유량 초과 체크
    if data.type in (TransactionType.SELL, TransactionType.WITHDRAW):
        available = await _get_available_quantity(db, user_id, data.asset_id)
        if data.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient quantity. Available: {available}, Requested: {data.quantity}",
            )

    # 매수/입금 시 출처 계좌에서 자동 출금
    if data.type in (TransactionType.BUY, TransactionType.DEPOSIT) and data.source_asset_id:
        source_asset = await _get_user_asset(db, user_id, data.source_asset_id)
        if source_asset.asset_type not in CASH_LIKE_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Source asset must be a cash-like account (현금, 파킹통장)",
            )
        source_asset_name = source_asset.name

        # 출금 금액 계산
        # 출처가 원화 계좌면 환율 적용, 달러 계좌면 달러 그대로
        source_is_krw = source_asset.asset_type != AssetType.CASH_USD

        if data.type == TransactionType.DEPOSIT:
            # 입금(예금/적금): 입금 금액 기준
            withdraw_amount = data.quantity
            if data.exchange_rate and source_is_krw:
                # 달러 입금인데 출처가 원화 계좌 → 원화 환산
                withdraw_amount = data.quantity * data.exchange_rate
        else:
            # 매수: 수량 × 단가 + 수수료
            withdraw_amount = data.quantity * data.unit_price + data.fee
            if data.exchange_rate and source_is_krw:
                # 해외주식 매수인데 출처가 원화 계좌 → 원화 환산
                withdraw_amount = withdraw_amount * data.exchange_rate

        # 출금 통화: 출처 계좌의 통화를 따름
        withdraw_currency = "USD" if source_asset.asset_type == AssetType.CASH_USD else "KRW"

        available = await _get_available_quantity(db, user_id, data.source_asset_id)
        if withdraw_amount > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance in source account. Available: {available}, Required: {withdraw_amount}",
            )

        memo_label = "매수" if data.type == TransactionType.BUY else "입금"
        # 출처 계좌에서 자동 출금 거래 생성
        withdraw_tx = Transaction(
            user_id=user_id,
            asset_id=data.source_asset_id,
            type=TransactionType.WITHDRAW,
            quantity=withdraw_amount,
            unit_price=Decimal("1"),
            currency=withdraw_currency,
            memo=f"{asset.name} {memo_label} 출금",
            transacted_at=data.transacted_at,
        )
        db.add(withdraw_tx)

        # source_asset principal 차감 (파킹/예금/적금)
        if source_asset.asset_type in _PRINCIPAL_TYPES and source_asset.principal is not None:
            source_asset.principal = Decimal(str(source_asset.principal)) - withdraw_amount

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
        source_asset_id=data.source_asset_id,
        transacted_at=data.transacted_at,
    )
    db.add(tx)

    # target_asset principal 반영 (입금 시 파킹/예금/적금)
    if data.type == TransactionType.DEPOSIT and asset.asset_type in _PRINCIPAL_TYPES and asset.principal is not None:
        asset.principal = Decimal(str(asset.principal)) + data.quantity

    await db.commit()
    await db.refresh(tx)
    return _to_response(tx, asset, source_asset_name)


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
    source_ids = {tx.source_asset_id for tx in transactions if tx.source_asset_id}
    all_ids = asset_ids | source_ids
    asset_cache: dict[uuid.UUID, Asset] = {}
    if all_ids:
        asset_stmt = select(Asset).where(Asset.id.in_(all_ids))
        assets = (await db.execute(asset_stmt)).scalars().all()
        asset_cache = {a.id: a for a in assets}

    responses = []
    for tx in transactions:
        asset = asset_cache.get(tx.asset_id)
        if asset:
            source_name = asset_cache[tx.source_asset_id].name if tx.source_asset_id and tx.source_asset_id in asset_cache else None
            responses.append(_to_response(tx, asset, source_name))

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

    # 매도/출금 수량 변경 시 초과 체크
    if "quantity" in update_data and tx.type in (TransactionType.SELL, TransactionType.WITHDRAW):
        new_qty = update_data["quantity"]
        available = await _get_available_quantity(db, user_id, tx.asset_id)
        available += tx.quantity  # 기존 수량 복원
        if new_qty > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient quantity. Available: {available}, Requested: {new_qty}",
            )

    for field, value in update_data.items():
        setattr(tx, field, value)

    await db.commit()
    await db.refresh(tx)
    source_name = None
    if tx.source_asset_id:
        sa = await db.get(Asset, tx.source_asset_id)
        source_name = sa.name if sa else None
    return _to_response(tx, asset, source_name)


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
    """보유량 = (buy + deposit) - (sell + withdraw)"""
    add_stmt = select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
        Transaction.user_id == user_id,
        Transaction.asset_id == asset_id,
        Transaction.type.in_([TransactionType.BUY, TransactionType.DEPOSIT]),
    )
    sub_stmt = select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
        Transaction.user_id == user_id,
        Transaction.asset_id == asset_id,
        Transaction.type.in_([TransactionType.SELL, TransactionType.WITHDRAW]),
    )

    add_total = Decimal(str((await db.execute(add_stmt)).scalar() or 0))
    sub_total = Decimal(str((await db.execute(sub_stmt)).scalar() or 0))
    return add_total - sub_total
