import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.account import Account, AccountType
from app.models.category import Category, CategoryDirection
from app.models.entry import Entry, EntryGroup, EntryType, GroupType
from app.models.security import Security, SecurityPrice, AssetClass, DataSource
from app.models.recurring_schedule import RecurringSchedule, ScheduleType


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


async def test_create_income_entry(db):
    user_id = uuid.uuid4()
    account = Account(user_id=user_id, account_type=AccountType.CASH, name="급여통장", currency="KRW")
    db.add(account)
    await db.flush()

    entry = Entry(
        user_id=user_id,
        account_id=account.id,
        type=EntryType.INCOME,
        amount=Decimal("3000000"),
        currency="KRW",
        transacted_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    assert entry.amount == Decimal("3000000")
    assert entry.security_id is None


async def test_create_transfer_entry_group(db):
    user_id = uuid.uuid4()
    src = Account(user_id=user_id, account_type=AccountType.CASH, name="급여통장", currency="KRW")
    dst = Account(user_id=user_id, account_type=AccountType.PARKING, name="CMA", currency="KRW")
    db.add_all([src, dst])
    await db.flush()

    group = EntryGroup(user_id=user_id, group_type=GroupType.TRANSFER, description="급여통장 → CMA")
    db.add(group)
    await db.flush()

    now = datetime.now(timezone.utc)
    out_entry = Entry(
        user_id=user_id, account_id=src.id, entry_group_id=group.id,
        type=EntryType.TRANSFER_OUT, amount=Decimal("-1350000"), currency="KRW",
        transacted_at=now,
    )
    in_entry = Entry(
        user_id=user_id, account_id=dst.id, entry_group_id=group.id,
        type=EntryType.TRANSFER_IN, amount=Decimal("1350000"), currency="KRW",
        transacted_at=now,
    )
    db.add_all([out_entry, in_entry])
    await db.flush()

    assert out_entry.entry_group_id == in_entry.entry_group_id
    assert out_entry.amount + in_entry.amount == Decimal("0")


async def test_create_stock_buy_entry(db):
    user_id = uuid.uuid4()
    account = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="ISA", currency="KRW")
    db.add(account)
    await db.flush()

    sec = Security(
        symbol="005930", name="삼성전자", currency="KRW",
        asset_class=AssetClass.EQUITY_KR, data_source=DataSource.YAHOO,
    )
    db.add(sec)
    await db.flush()

    entry = Entry(
        user_id=user_id, account_id=account.id,
        security_id=sec.id,
        type=EntryType.BUY,
        amount=Decimal("-500000"),
        currency="KRW",
        quantity=Decimal("10"),
        unit_price=Decimal("50000"),
        transacted_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    assert entry.quantity == Decimal("10")
    assert entry.amount == Decimal("-500000")


async def test_create_category(db):
    cat = Category(
        user_id=uuid.uuid4(),
        direction=CategoryDirection.EXPENSE,
        name="식비",
        icon="🍽",
        color="#FF5733",
    )
    db.add(cat)
    await db.flush()
    assert cat.is_active is True
    assert cat.direction == CategoryDirection.EXPENSE


async def test_create_recurring_expense_schedule(db):
    """고정비 스케줄 생성 (종료일 없음 = 무기한)"""
    user_id = uuid.uuid4()
    src = Account(
        user_id=user_id, account_type=AccountType.CASH, name="급여통장", currency="KRW"
    )
    db.add(src)
    await db.flush()

    schedule = RecurringSchedule(
        user_id=user_id,
        type=ScheduleType.EXPENSE,
        name="월세",
        amount=Decimal("1350000"),
        currency="KRW",
        schedule_day=15,
        start_date=date(2026, 1, 1),
        source_account_id=src.id,
    )
    db.add(schedule)
    await db.flush()
    assert schedule.is_active is True
    assert schedule.end_date is None
    assert schedule.total_count is None


async def test_create_installment_schedule(db):
    """할부 스케줄 (total_count로 종료 조건)"""
    schedule = RecurringSchedule(
        user_id=uuid.uuid4(),
        type=ScheduleType.EXPENSE,
        name="노트북 할부",
        amount=Decimal("150000"),
        schedule_day=20,
        start_date=date(2026, 1, 1),
        total_count=12,
        executed_count=0,
    )
    db.add(schedule)
    await db.flush()
    assert schedule.total_count == 12


async def test_create_transfer_schedule(db):
    """자동이체 스케줄"""
    user_id = uuid.uuid4()
    src = Account(
        user_id=user_id, account_type=AccountType.CASH, name="급여통장", currency="KRW"
    )
    dst = Account(
        user_id=user_id, account_type=AccountType.PARKING, name="CMA", currency="KRW"
    )
    db.add_all([src, dst])
    await db.flush()

    schedule = RecurringSchedule(
        user_id=user_id,
        type=ScheduleType.TRANSFER,
        name="CMA 자동이체",
        amount=Decimal("500000"),
        schedule_day=11,
        start_date=date(2026, 1, 1),
        source_account_id=src.id,
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()
    assert schedule.source_account_id == src.id
    assert schedule.target_account_id == dst.id
