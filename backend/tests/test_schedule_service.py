import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.account import Account, AccountType
from app.models.recurring_schedule import RecurringSchedule, ScheduleType
from app.services.entry_service import get_account_balance
from app.services.schedule_service import (
    execute_schedule,
)


async def _setup_accounts(db):
    user_id = uuid.uuid4()
    src = Account(user_id=user_id, account_type=AccountType.CASH, name="급여통장", currency="KRW")
    dst = Account(user_id=user_id, account_type=AccountType.PARKING, name="CMA", currency="KRW")
    db.add_all([src, dst])
    await db.flush()
    return user_id, src, dst


async def test_execute_income_schedule(db):
    user_id, _, dst = await _setup_accounts(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="월급",
        amount=Decimal("3000000"), schedule_day=25,
        start_date=date(2026, 1, 1),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 25))
    assert entry is not None
    balance = await get_account_balance(db, dst.id)
    assert balance == Decimal("3000000")
    assert schedule.executed_count == 1


async def test_execute_expense_schedule(db):
    user_id, src, _ = await _setup_accounts(db)
    # 먼저 잔액 입금
    from app.services.entry_service import create_entry
    from app.models.entry import EntryType
    await create_entry(db, user_id, account_id=src.id, type=EntryType.INCOME,
                       amount=Decimal("5000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.EXPENSE, name="월세",
        amount=Decimal("1350000"), schedule_day=15,
        start_date=date(2026, 1, 1),
        source_account_id=src.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 15))
    assert entry is not None
    balance = await get_account_balance(db, src.id)
    assert balance == Decimal("3650000")


async def test_execute_transfer_schedule(db):
    user_id, src, dst = await _setup_accounts(db)
    from app.services.entry_service import create_entry
    from app.models.entry import EntryType
    await create_entry(db, user_id, account_id=src.id, type=EntryType.INCOME,
                       amount=Decimal("5000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.TRANSFER, name="CMA 자동이체",
        amount=Decimal("500000"), schedule_day=11,
        start_date=date(2026, 1, 1),
        source_account_id=src.id, target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 11))
    assert entry is not None

    src_bal = await get_account_balance(db, src.id)
    dst_bal = await get_account_balance(db, dst.id)
    assert src_bal == Decimal("4500000")
    assert dst_bal == Decimal("500000")


async def test_duplicate_execution_skipped(db):
    user_id, _, dst = await _setup_accounts(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="월급",
        amount=Decimal("3000000"), schedule_day=25,
        start_date=date(2026, 1, 1),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    # 첫 실행
    entry1 = await execute_schedule(db, schedule, date(2026, 4, 25))
    assert entry1 is not None
    # 같은 달 재실행 → 스킵
    entry2 = await execute_schedule(db, schedule, date(2026, 4, 25))
    assert entry2 is None
    # 잔액은 1회분만
    balance = await get_account_balance(db, dst.id)
    assert balance == Decimal("3000000")


async def test_installment_auto_deactivation(db):
    user_id, src, _ = await _setup_accounts(db)
    from app.services.entry_service import create_entry
    from app.models.entry import EntryType
    await create_entry(db, user_id, account_id=src.id, type=EntryType.INCOME,
                       amount=Decimal("10000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.EXPENSE, name="노트북 할부",
        amount=Decimal("150000"), schedule_day=20,
        start_date=date(2026, 1, 1),
        total_count=3, executed_count=2,
        source_account_id=src.id,
    )
    db.add(schedule)
    await db.flush()

    # 3번째 실행 → total_count 도달 → 자동 비활성화
    entry = await execute_schedule(db, schedule, date(2026, 3, 20))
    assert entry is not None
    assert schedule.executed_count == 3
    assert schedule.is_active is False

    # 4번째 시도 → 이미 비활성화
    entry2 = await execute_schedule(db, schedule, date(2026, 4, 20))
    assert entry2 is None


async def test_user_can_edit_generated_entry(db):
    """스케줄에서 생성된 Entry를 사용자가 수정해도 스케줄 템플릿은 변하지 않음"""
    user_id, src, _ = await _setup_accounts(db)
    from app.services.entry_service import create_entry
    from app.models.entry import EntryType
    await create_entry(db, user_id, account_id=src.id, type=EntryType.INCOME,
                       amount=Decimal("5000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.EXPENSE, name="공과금",
        amount=Decimal("150000"), schedule_day=15,
        start_date=date(2026, 1, 1),
        source_account_id=src.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 15))
    assert entry is not None

    # 사용자가 이번 달 공과금을 20만원으로 수정
    entry.amount = Decimal("-200000")
    await db.flush()

    # 스케줄 템플릿은 15만원 그대로
    assert schedule.amount == Decimal("150000")
    # 잔액은 수정된 값 반영
    balance = await get_account_balance(db, src.id)
    assert balance == Decimal("4800000")
