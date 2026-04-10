import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.models.account import Account, AccountType
from app.models.security import Security, AssetClass, DataSource
from app.models.entry import EntryType
from app.services.entry_service import (
    get_account_balance,
    get_account_cash_balance,
    get_holding_quantity,
    get_holdings,
    create_entry,
    create_transfer,
    create_trade,
    adjust_balance,
)


async def _make_account(db, name="테스트", account_type=AccountType.CASH, currency="KRW"):
    user_id = uuid.uuid4()
    account = Account(user_id=user_id, account_type=account_type, name=name, currency=currency)
    db.add(account)
    await db.flush()
    return user_id, account


async def _make_security(db, symbol="005930", name="삼성전자"):
    sec = Security(
        symbol=symbol,
        name=name,
        currency="KRW",
        asset_class=AssetClass.EQUITY_KR,
        data_source=DataSource.YAHOO,
    )
    db.add(sec)
    await db.flush()
    return sec


async def test_balance_starts_at_zero(db):
    _, account = await _make_account(db)
    balance = await get_account_balance(db, account.id)
    assert balance == Decimal("0")


async def test_income_increases_balance(db):
    user_id, account = await _make_account(db)
    await create_entry(
        db,
        user_id,
        account_id=account.id,
        type=EntryType.INCOME,
        amount=Decimal("3000000"),
        currency="KRW",
        transacted_at=datetime.now(timezone.utc),
    )
    balance = await get_account_balance(db, account.id)
    assert balance == Decimal("3000000")


async def test_expense_decreases_balance(db):
    user_id, account = await _make_account(db)
    await create_entry(
        db,
        user_id,
        account_id=account.id,
        type=EntryType.INCOME,
        amount=Decimal("1000000"),
        currency="KRW",
        transacted_at=datetime.now(timezone.utc),
    )
    await create_entry(
        db,
        user_id,
        account_id=account.id,
        type=EntryType.EXPENSE,
        amount=Decimal("-50000"),
        currency="KRW",
        transacted_at=datetime.now(timezone.utc),
    )
    balance = await get_account_balance(db, account.id)
    assert balance == Decimal("950000")


async def test_transfer_preserves_total(db):
    user_id = uuid.uuid4()
    src = Account(user_id=user_id, account_type=AccountType.CASH, name="급여통장", currency="KRW")
    dst = Account(user_id=user_id, account_type=AccountType.PARKING, name="CMA", currency="KRW")
    db.add_all([src, dst])
    await db.flush()

    await create_entry(
        db,
        user_id,
        account_id=src.id,
        type=EntryType.INCOME,
        amount=Decimal("5000000"),
        currency="KRW",
        transacted_at=datetime.now(timezone.utc),
    )

    await create_transfer(db, user_id, src.id, dst.id, Decimal("1350000"))

    src_bal = await get_account_balance(db, src.id)
    dst_bal = await get_account_balance(db, dst.id)
    assert src_bal == Decimal("3650000")
    assert dst_bal == Decimal("1350000")
    assert src_bal + dst_bal == Decimal("5000000")


async def test_transfer_same_account_rejected(db):
    user_id, account = await _make_account(db)
    with pytest.raises(Exception):
        await create_transfer(db, user_id, account.id, account.id, Decimal("100000"))


async def test_stock_buy_and_holdings(db):
    user_id, account = await _make_account(db, "ISA", AccountType.INVESTMENT)
    sec = await _make_security(db)

    # ISA에 현금 입금
    await create_entry(
        db,
        user_id,
        account_id=account.id,
        type=EntryType.INCOME,
        amount=Decimal("1000000"),
        currency="KRW",
        transacted_at=datetime.now(timezone.utc),
    )

    # 삼성전자 10주 매수 @ 50000
    await create_trade(
        db, user_id, account.id, sec.id, trade_type=EntryType.BUY, quantity=Decimal("10"), unit_price=Decimal("50000")
    )

    # 현금 잔액 = 1000000 - 500000 = 500000
    cash = await get_account_cash_balance(db, account.id)
    assert cash == Decimal("500000")

    # 보유량 = 10주
    qty = await get_holding_quantity(db, account.id, sec.id)
    assert qty == Decimal("10")

    # holdings 조회
    holdings = await get_holdings(db, account.id)
    assert len(holdings) == 1
    assert holdings[0]["quantity"] == Decimal("10")
    assert holdings[0]["symbol"] == "005930"


async def test_stock_sell(db):
    user_id, account = await _make_account(db, "ISA", AccountType.INVESTMENT)
    sec = await _make_security(db, "AAPL", "Apple")

    await create_entry(
        db,
        user_id,
        account_id=account.id,
        type=EntryType.INCOME,
        amount=Decimal("2000000"),
        currency="KRW",
        transacted_at=datetime.now(timezone.utc),
    )

    # 10주 매수
    await create_trade(
        db, user_id, account.id, sec.id, trade_type=EntryType.BUY, quantity=Decimal("10"), unit_price=Decimal("100000")
    )

    # 5주 매도
    await create_trade(
        db, user_id, account.id, sec.id, trade_type=EntryType.SELL, quantity=Decimal("5"), unit_price=Decimal("120000")
    )

    qty = await get_holding_quantity(db, account.id, sec.id)
    assert qty == Decimal("5")

    # 현금: 2000000 - 1000000(매수) + 600000(매도) = 1600000
    cash = await get_account_cash_balance(db, account.id)
    assert cash == Decimal("1600000")


async def test_adjust_balance(db):
    user_id, account = await _make_account(db)
    await create_entry(
        db,
        user_id,
        account_id=account.id,
        type=EntryType.INCOME,
        amount=Decimal("480000"),
        currency="KRW",
        transacted_at=datetime.now(timezone.utc),
    )

    await adjust_balance(db, user_id, account.id, target_balance=Decimal("500000"))

    balance = await get_account_balance(db, account.id)
    assert balance == Decimal("500000")


async def test_adjust_stock_quantity(db):
    user_id, account = await _make_account(db, "ISA", AccountType.INVESTMENT)
    sec = await _make_security(db, "TEST", "테스트주식")

    # 20주 매수
    await create_trade(
        db, user_id, account.id, sec.id, trade_type=EntryType.BUY, quantity=Decimal("20"), unit_price=Decimal("10000")
    )

    # 보유량을 25주로 보정
    await adjust_balance(
        db,
        user_id,
        account.id,
        target_balance=Decimal("0"),  # not used for security adjustment
        security_id=sec.id,
        target_quantity=Decimal("25"),
        unit_price=Decimal("10000"),
    )

    qty = await get_holding_quantity(db, account.id, sec.id)
    assert qty == Decimal("25")
