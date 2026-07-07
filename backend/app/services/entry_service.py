import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, EntryGroup, EntryType, GroupType
from app.models.security import Security, SecurityPrice


async def get_account_balance(
    db: AsyncSession, account_id: uuid.UUID, currency: str | None = None,
) -> Decimal:
    """계좌 잔액 = SUM(amount) — Entry가 유일한 진실 원천.

    currency가 지정되면 해당 통화 entry만 합산한다.
    """
    stmt = select(func.coalesce(func.sum(Entry.amount), 0)).where(
        Entry.account_id == account_id,
    )
    if currency is not None:
        stmt = stmt.where(Entry.currency == currency)
    return Decimal(str((await db.execute(stmt)).scalar()))


async def get_account_cash_balance(db: AsyncSession, account_id: uuid.UUID) -> Decimal:
    """투자 계좌 현금 잔액 = SUM(amount) (전체, 하위호환)"""
    stmt = select(func.coalesce(func.sum(Entry.amount), 0)).where(
        Entry.account_id == account_id,
    )
    return Decimal(str((await db.execute(stmt)).scalar()))


async def get_cash_balances_by_currency(
    db: AsyncSession, account_id: uuid.UUID
) -> dict[str, Decimal]:
    """투자 계좌 현금 잔액을 통화별로 분리 집계.

    security_id가 NULL인 엔트리(현금 이동)와
    security_id가 있는 엔트리(매수/매도 현금 흐름) 모두 포함.
    """
    stmt = (
        select(Entry.currency, func.coalesce(func.sum(Entry.amount), 0))
        .where(Entry.account_id == account_id)
        .group_by(Entry.currency)
    )
    result = await db.execute(stmt)
    return {
        row[0]: Decimal(str(row[1])) for row in result.all()
    }


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
        quantity = Decimal(str(row.total_quantity))

        # 평균 매수 단가 계산: -SUM(amount) / SUM(quantity) for BUY entries
        # amount는 -(qty*price+fee)이므로 수수료 포함 취득원가가 자동 반영된다
        avg_stmt = select(
            (-func.sum(Entry.amount)).label("total_cost"),
            func.sum(Entry.quantity).label("total_qty"),
        ).where(
            Entry.account_id == account_id,
            Entry.security_id == row.security_id,
            Entry.type == EntryType.BUY,
        )
        avg_result = (await db.execute(avg_stmt)).one()
        avg_price = (
            Decimal(str(avg_result.total_cost)) / Decimal(str(avg_result.total_qty))
            if avg_result.total_qty and avg_result.total_qty > 0
            else Decimal("0")
        )

        # 최신 시세 조회
        price_stmt = (
            select(SecurityPrice.close_price, SecurityPrice.currency)
            .where(SecurityPrice.security_id == row.security_id)
            .order_by(SecurityPrice.price_date.desc())
            .limit(1)
        )
        price_row = (await db.execute(price_stmt)).one_or_none()
        current_price = Decimal(str(price_row.close_price)) if price_row else None

        # 평가액 및 수익/손실
        if current_price is not None:
            value = quantity * current_price
            cost_basis = quantity * avg_price
            profit_loss = value - cost_basis
            profit_loss_rate = float(profit_loss / cost_basis * 100) if cost_basis > 0 else 0.0
        else:
            value = quantity * avg_price  # 시세 없으면 매수가 기준
            profit_loss = Decimal("0")
            profit_loss_rate = 0.0

        holdings.append(
            {
                "security_id": str(row.security_id),
                "symbol": security.symbol if security else None,
                "name": security.name if security else None,
                "quantity": quantity,
                "avg_price": avg_price,
                "current_price": current_price,
                "currency": security.currency if security else "KRW",
                "value": value,
                "profit_loss": profit_loss,
                "profit_loss_rate": round(profit_loss_rate, 2),
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
    target_currency: str | None = None,
    target_amount: Decimal | None = None,
    exchange_rate: Decimal | None = None,
    memo: str | None = None,
    transacted_at: datetime | None = None,
    recurring_schedule_id: uuid.UUID | None = None,
    source: str | None = None,
) -> EntryGroup:
    """이체 복식 기록: entry_group + entry 2건.

    통화가 다르면(target_currency != currency) target_amount로 입금 다리 금액을
    지정해야 하며, 양쪽 다리에 exchange_rate를 기록한다.
    """
    if source_account_id == target_account_id:
        raise HTTPException(status_code=400, detail="Same source and target account")

    tgt_currency = target_currency or currency
    if tgt_currency != currency and target_amount is None:
        raise HTTPException(
            status_code=400,
            detail="Cross-currency transfer requires target_amount",
        )
    in_amount = abs(target_amount) if target_amount is not None else abs(amount)

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
        exchange_rate=exchange_rate,
        memo=memo,
        recurring_schedule_id=recurring_schedule_id,
        source=source,
        transacted_at=ts,
    )
    in_entry = Entry(
        user_id=user_id,
        account_id=target_account_id,
        entry_group_id=group.id,
        type=EntryType.TRANSFER_IN,
        amount=in_amount,
        currency=tgt_currency,
        exchange_rate=exchange_rate,
        memo=memo,
        recurring_schedule_id=recurring_schedule_id,
        source=source,
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
    source: str | None = None,
) -> EntryGroup:
    """주식 매매: entry_group(trade) + entry 1건 (매수=음수amount/양수qty, 매도=양수amount/음수qty)"""
    if trade_type not in (EntryType.BUY, EntryType.SELL):
        raise HTTPException(status_code=400, detail="Trade type must be buy or sell")

    if trade_type == EntryType.SELL:
        current_qty = await get_holding_quantity(db, account_id, security_id)
        if quantity > current_qty:
            raise HTTPException(
                status_code=400,
                detail=f"매도 수량({quantity})이 보유량({current_qty})을 초과합니다",
            )

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
        entry_amount = -total_cost  # 현금 유출: -(qty * price + fee)
        entry_qty = quantity  # 주식 유입
    else:
        entry_amount = quantity * unit_price - fee  # 현금 유입: qty * price - fee
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
        source=source,
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
        current = await get_account_balance(db, account_id, currency)
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


async def get_entry_group(
    db: AsyncSession, user_id: uuid.UUID, group_id: uuid.UUID,
) -> EntryGroup:
    group = await db.get(EntryGroup, group_id)
    if not group or group.user_id != user_id:
        raise HTTPException(status_code=404, detail="Entry group not found")
    return group


async def _group_entries(db: AsyncSession, group_id: uuid.UUID) -> list[Entry]:
    stmt = select(Entry).where(Entry.entry_group_id == group_id)
    return list((await db.execute(stmt)).scalars().all())


async def update_transfer_group(
    db: AsyncSession,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    amount: Decimal | None = None,
    target_amount: Decimal | None = None,
    exchange_rate: Decimal | None = None,
    memo: str | None = None,
    transacted_at: datetime | None = None,
) -> EntryGroup:
    """이체 그룹 양다리 동시 수정 (out=-abs/in=+abs)."""
    group = await get_entry_group(db, user_id, group_id)
    if group.group_type != GroupType.TRANSFER:
        raise HTTPException(status_code=400, detail="Not a transfer group")

    entries = await _group_entries(db, group_id)
    out_entry = next((e for e in entries if e.type == EntryType.TRANSFER_OUT), None)
    in_entry = next((e for e in entries if e.type == EntryType.TRANSFER_IN), None)
    if out_entry is None or in_entry is None:
        raise HTTPException(status_code=409, detail="Transfer group is incomplete")

    if amount is not None:
        out_entry.amount = -abs(amount)
    if target_amount is not None:
        in_entry.amount = abs(target_amount)
    elif amount is not None and in_entry.currency == out_entry.currency:
        in_entry.amount = abs(amount)
    if exchange_rate is not None:
        out_entry.exchange_rate = exchange_rate
        in_entry.exchange_rate = exchange_rate
    if memo is not None:
        out_entry.memo = memo
        in_entry.memo = memo
        group.description = memo
    if transacted_at is not None:
        out_entry.transacted_at = transacted_at
        in_entry.transacted_at = transacted_at

    await db.flush()
    return group


async def update_trade_group(
    db: AsyncSession,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    quantity: Decimal | None = None,
    unit_price: Decimal | None = None,
    fee: Decimal | None = None,
    memo: str | None = None,
    transacted_at: datetime | None = None,
) -> EntryGroup:
    """매매 그룹 수정: create_trade 공식으로 amount 재계산."""
    group = await get_entry_group(db, user_id, group_id)
    if group.group_type != GroupType.TRADE:
        raise HTTPException(status_code=400, detail="Not a trade group")

    entries = await _group_entries(db, group_id)
    if len(entries) != 1:
        raise HTTPException(status_code=409, detail="Trade group is incomplete")
    entry = entries[0]
    trade_type = entry.type

    new_qty = abs(quantity) if quantity is not None else abs(entry.quantity)
    new_price = unit_price if unit_price is not None else entry.unit_price
    new_fee = fee if fee is not None else entry.fee

    if trade_type == EntryType.SELL:
        # 이 그룹 entry를 제외한 보유량을 초과해 매도할 수 없다
        current_qty = await get_holding_quantity(db, entry.account_id, entry.security_id)
        available = current_qty - entry.quantity  # entry.quantity는 매도라 음수
        if new_qty > available:
            raise HTTPException(
                status_code=400,
                detail=f"매도 수량({new_qty})이 보유량({available})을 초과합니다",
            )

    if trade_type == EntryType.BUY:
        entry.amount = -(new_qty * new_price + new_fee)
        entry.quantity = new_qty
    else:
        entry.amount = new_qty * new_price - new_fee
        entry.quantity = -new_qty
    entry.unit_price = new_price
    entry.fee = new_fee
    if memo is not None:
        entry.memo = memo
        group.description = memo
    if transacted_at is not None:
        entry.transacted_at = transacted_at

    await db.flush()
    return group


async def delete_entry_group(
    db: AsyncSession, user_id: uuid.UUID, group_id: uuid.UUID,
) -> None:
    """그룹의 모든 entry를 명시 삭제 후 그룹 삭제 (FK가 SET NULL이므로)."""
    group = await get_entry_group(db, user_id, group_id)
    entries = await _group_entries(db, group_id)
    for e in entries:
        await db.delete(e)
    await db.flush()
    await db.delete(group)
    await db.flush()


async def merge_transfer(
    db: AsyncSession,
    user_id: uuid.UUID,
    entry_a_id: uuid.UUID,
    entry_b_id: uuid.UUID,
) -> EntryGroup:
    """서로 다른 계좌의 income/expense 두 건을 이체 한 쌍으로 병합한다.

    검증: 같은 user, 서로 다른 계좌, 둘 다 그룹 미소속, 같은 통화,
    절대금액 동일, 부호 반대, 타입 income/expense.
    음수 쪽은 transfer_out, 양수 쪽은 transfer_in으로 전환하고 카테고리를 제거한다.
    """
    if entry_a_id == entry_b_id:
        raise HTTPException(status_code=400, detail="같은 거래는 병합할 수 없습니다")

    a = await db.get(Entry, entry_a_id)
    b = await db.get(Entry, entry_b_id)
    for entry in (a, b):
        if entry is None or entry.user_id != user_id:
            raise HTTPException(status_code=404, detail="Entry not found")

    if a.account_id == b.account_id:
        raise HTTPException(status_code=400, detail="서로 다른 계좌의 거래만 병합할 수 있습니다")
    if a.entry_group_id is not None or b.entry_group_id is not None:
        raise HTTPException(status_code=400, detail="이미 그룹에 속한 거래는 병합할 수 없습니다")
    if a.currency != b.currency:
        raise HTTPException(status_code=400, detail="통화가 다른 거래는 병합할 수 없습니다")
    if a.type not in (EntryType.INCOME, EntryType.EXPENSE) or b.type not in (
        EntryType.INCOME, EntryType.EXPENSE,
    ):
        raise HTTPException(status_code=400, detail="수입/지출 거래만 이체로 병합할 수 있습니다")
    if abs(a.amount) != abs(b.amount):
        raise HTTPException(status_code=400, detail="금액 절대값이 같아야 합니다")
    if (a.amount < 0) == (b.amount < 0):
        raise HTTPException(status_code=400, detail="부호가 반대여야 합니다 (한쪽 출금/한쪽 입금)")

    out_entry = a if a.amount < 0 else b
    in_entry = b if a.amount < 0 else a

    group = EntryGroup(
        user_id=user_id,
        group_type=GroupType.TRANSFER,
        description=out_entry.memo or in_entry.memo,
    )
    db.add(group)
    await db.flush()

    out_entry.type = EntryType.TRANSFER_OUT
    out_entry.entry_group_id = group.id
    out_entry.category_id = None
    in_entry.type = EntryType.TRANSFER_IN
    in_entry.entry_group_id = group.id
    in_entry.category_id = None
    await db.flush()
    return group
