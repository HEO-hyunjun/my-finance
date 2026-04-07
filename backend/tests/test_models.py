import uuid
from datetime import date
from decimal import Decimal

from app.models.account import Account, AccountType
from app.models.security import Security, SecurityPrice, AssetClass, DataSource


async def test_create_cash_account(db):
    account = Account(
        user_id=uuid.uuid4(),
        account_type=AccountType.CASH,
        name="급여통장",
        currency="KRW",
    )
    db.add(account)
    await db.flush()
    assert account.id is not None
    assert account.is_active is True


async def test_create_parking_account(db):
    account = Account(
        user_id=uuid.uuid4(),
        account_type=AccountType.PARKING,
        name="한투 CMA",
        currency="KRW",
        interest_rate=Decimal("2.250"),
    )
    db.add(account)
    await db.flush()
    assert account.interest_rate == Decimal("2.250")


async def test_create_security_with_price(db):
    sec = Security(
        symbol="005930",
        name="삼성전자",
        currency="KRW",
        asset_class=AssetClass.EQUITY_KR,
        data_source=DataSource.YAHOO,
        exchange="KRX",
    )
    db.add(sec)
    await db.flush()

    price = SecurityPrice(
        security_id=sec.id,
        price_date=date(2026, 4, 7),
        close_price=Decimal("67800"),
        currency="KRW",
    )
    db.add(price)
    await db.flush()
    assert price.security_id == sec.id
