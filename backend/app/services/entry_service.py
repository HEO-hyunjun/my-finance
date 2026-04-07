import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, EntryGroup, EntryType, GroupType
from app.models.security import Security


async def get_account_balance(db: AsyncSession, account_id: uuid.UUID) -> Decimal:
    """계좌 잔액 = SUM(amount) — Entry가 유일한 진실 원천"""
    stmt = select(func.coalesce(func.sum(Entry.amount), 0)).where(
        Entry.account_id == account_id,
    )
    return Decimal(str((await db.execute(stmt)).scalar()))


async def get_account_cash_balance(db: AsyncSession, account_id: uuid.UUID) -> Decimal:
    """투자 계좌 현금 잔액 = SUM(amount).

    amount는 항상 현금 흐름을 나타냅니다 (BUY=-cost, SELL=+proceeds).
    주식 보유량은 quantity 필드로 별도 추적되므로 amount 합계 = 현금 잔액입니다.
    """
    stmt = select(func.coalesce(func.sum(Entry.amount), 0)).where(
        Entry.account_id == account_id,
    )
    return Decimal(str((await db.execute(stmt)).scalar()))


async def get_holding_quantity(
    db: AsyncSession,
    account_id: uuid.UUID,
    security_id: uuid.UUID,
) -> Decimal:
    """종목 보유량 = SUM(quantity)"""
    stmt = select(func.coalesce(func.sum(Entry.quantity), 0)).where(
        Entry.account_id == account_id,
        Entry.security_id == security_id,
    )
    return Decimal(str((await db.execute(stmt)).scalar()))


async def get_holdings(
    db: AsyncSession,
    account_id: uuid.UUID,
) -> list[dict]:
    """투자 계좌의 보유 종목 목록 (security_id별 수량 집계)"""
    stmt = (
        select(
            Entry.security_id,
            func.sum(Entry.quantity).label("total_quantity"),
        )
        .where(
            Entry.account_id == account_id,
            Entry.security_id.is_not(None),
        )
        .group_by(Entry.security_id)
        .having(func.sum(Entry.quantity) != 0)
    )
    result = await db.execute(stmt)
    rows = result.all()

    holdings = []
    for row in rows:
        security = await db.get(Security, row.security_id)
        holdings.append(
            {
                "security_id": str(row.security_id),
                "symbol": security.symbol if security else None,
                "name": security.name if security else None,
                "quantity": Decimal(str(row.total_quantity)),
            }
        )
    return holdings


async def create_entry(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> Entry:
    """단일 Entry 생성"""
    entry = Entry(user_id=user_id, **kwargs)
    db.add(entry)
    await db.flush()
    return entry


async def create_transfer(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_account_id: uuid.UUID,
    target_account_id: uuid.UUID,
    amount: Decimal,
    currency: str = "KRW",
    memo: str | None = None,
    transacted_at: datetime | None = None,
    recurring_schedule_id: uuid.UUID | None = None,
) -> EntryGroup:
    """이체 복식 기록: entry_group + entry 2건"""
    if source_account_id == target_account_id:
        raise HTTPException(status_code=400, detail="Same source and target account")

    ts = transacted_at or datetime.now(timezone.utc)

    group = EntryGroup(
        user_id=user_id,
        group_type=GroupType.TRANSFER,
        description=memo,
    )
    db.add(group)
    await db.flush()

    out_entry = Entry(
        user_id=user_id,
        account_id=source_account_id,
        entry_group_id=group.id,
        type=EntryType.TRANSFER_OUT,
        amount=-abs(amount),
        currency=currency,
        memo=memo,
        recurring_schedule_id=recurring_schedule_id,
        transacted_at=ts,
    )
    in_entry = Entry(
        user_id=user_id,
        account_id=target_account_id,
        entry_group_id=group.id,
        type=EntryType.TRANSFER_IN,
        amount=abs(amount),
        currency=currency,
        memo=memo,
        recurring_schedule_id=recurring_schedule_id,
        transacted_at=ts,
    )
    db.add_all([out_entry, in_entry])
    await db.flush()
    return group


async def create_trade(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    security_id: uuid.UUID,
    trade_type: EntryType,
    quantity: Decimal,
    unit_price: Decimal,
    currency: str = "KRW",
    fee: Decimal = Decimal("0"),
    exchange_rate: Decimal | None = None,
    memo: str | None = None,
    transacted_at: datetime | None = None,
) -> EntryGroup:
    """주식 매매: entry_group(trade) + entry 1건 (매수=음수amount/양수qty, 매도=양수amount/음수qty)"""
    if trade_type not in (EntryType.BUY, EntryType.SELL):
        raise HTTPException(status_code=400, detail="Trade type must be buy or sell")

    ts = transacted_at or datetime.now(timezone.utc)
    total_cost = quantity * unit_price + fee

    group = EntryGroup(
        user_id=user_id,
        group_type=GroupType.TRADE,
        description=memo,
    )
    db.add(group)
    await db.flush()

    if trade_type == EntryType.BUY:
        entry_amount = -total_cost  # 현금 유출
        entry_qty = quantity  # 주식 유입
    else:
        entry_amount = total_cost - fee  # 현금 유입 (수수료 차감)
        entry_qty = -quantity  # 주식 유출

    entry = Entry(
        user_id=user_id,
        account_id=account_id,
        entry_group_id=group.id,
        security_id=security_id,
        type=trade_type,
        amount=entry_amount,
        currency=currency,
        quantity=entry_qty,
        unit_price=unit_price,
        fee=fee,
        exchange_rate=exchange_rate,
        memo=memo,
        transacted_at=ts,
    )
    db.add(entry)
    await db.flush()
    return group


async def adjust_balance(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    target_balance: Decimal,
    currency: str = "KRW",
    memo: str | None = None,
    security_id: uuid.UUID | None = None,
    target_quantity: Decimal | None = None,
    unit_price: Decimal | None = None,
) -> Entry:
    """잔액/보유량 보정: 차액을 adjustment Entry로 생성"""
    if security_id and target_quantity is not None:
        current_qty = await get_holding_quantity(db, account_id, security_id)
        qty_diff = target_quantity - current_qty
        if not unit_price:
            raise HTTPException(status_code=400, detail="unit_price required for security adjustment")
        amount_diff = qty_diff * unit_price
    else:
        current = await get_account_balance(db, account_id)
        amount_diff = target_balance - current
        qty_diff = None

    if amount_diff == 0 and (qty_diff is None or qty_diff == 0):
        raise HTTPException(status_code=400, detail="No adjustment needed")

    entry = Entry(
        user_id=user_id,
        account_id=account_id,
        type=EntryType.ADJUSTMENT,
        amount=amount_diff,
        currency=currency,
        security_id=security_id,
        quantity=qty_diff,
        unit_price=unit_price,
        memo=memo or "잔액 보정",
        transacted_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    return entry
