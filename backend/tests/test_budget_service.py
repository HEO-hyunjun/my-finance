import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.account import Account, AccountType
from app.models.category import Category, CategoryDirection
from app.models.entry import EntryType
from app.models.recurring_schedule import RecurringSchedule, ScheduleType
from app.services.budget_v2_service import (
    get_period_dates,
    get_budget_overview,
    get_category_budgets,
    create_or_update_allocation,
)
from app.services.entry_service import create_entry


def test_period_dates_standard_month():
    start, end = get_period_dates(1, date(2026, 4, 15))
    assert start == date(2026, 4, 1)
    assert end == date(2026, 4, 30)


def test_period_dates_custom_day_after():
    """today(4/15)가 시작일(10) 이후 → 4/10 ~ 5/9"""
    start, end = get_period_dates(10, date(2026, 4, 15))
    assert start == date(2026, 4, 10)
    assert end == date(2026, 5, 9)


def test_period_dates_custom_day_before():
    """today(4/5)가 시작일(10) 이전 → 3/10 ~ 4/9"""
    start, end = get_period_dates(10, date(2026, 4, 5))
    assert start == date(2026, 3, 10)
    assert end == date(2026, 4, 9)


def test_period_dates_december_wrap():
    """12월 → 연도 넘김 처리"""
    start, end = get_period_dates(15, date(2026, 12, 20))
    assert start == date(2026, 12, 15)
    assert end == date(2027, 1, 14)


def test_period_dates_january_wrap():
    """1월 초 → 전년도 12월 시작"""
    start, end = get_period_dates(15, date(2027, 1, 5))
    assert start == date(2026, 12, 15)
    assert end == date(2027, 1, 14)


async def test_budget_overview_top_down(db):
    user_id = uuid.uuid4()

    # 수입 스케줄
    db.add(
        RecurringSchedule(
            user_id=user_id,
            type=ScheduleType.INCOME,
            name="월급",
            amount=Decimal("3000000"),
            schedule_day=25,
            start_date=date(2026, 1, 1),
            target_account_id=uuid.uuid4(),
        )
    )
    # 고정 지출
    db.add(
        RecurringSchedule(
            user_id=user_id,
            type=ScheduleType.EXPENSE,
            name="월세",
            amount=Decimal("1350000"),
            schedule_day=15,
            start_date=date(2026, 1, 1),
            source_account_id=uuid.uuid4(),
        )
    )
    # 자동이체
    db.add(
        RecurringSchedule(
            user_id=user_id,
            type=ScheduleType.TRANSFER,
            name="적금",
            amount=Decimal("500000"),
            schedule_day=11,
            start_date=date(2026, 1, 1),
            source_account_id=uuid.uuid4(),
            target_account_id=uuid.uuid4(),
        )
    )
    await db.flush()

    overview = await get_budget_overview(db, user_id, date(2026, 4, 15))

    assert overview["total_income"] == Decimal("3000000")
    assert overview["total_fixed_expense"] == Decimal("1350000")
    assert overview["total_transfer"] == Decimal("500000")
    # 가용 = 3000000 - 1350000 - 500000 = 1150000
    assert overview["available_budget"] == Decimal("1150000")
    # 배분 없음 → 미배분 = 가용
    assert overview["unallocated"] == Decimal("1150000")


async def test_budget_overview_with_allocation(db):
    """배분이 있으면 미배분 잔액이 줄어야 합니다."""
    user_id = uuid.uuid4()
    cat = Category(
        user_id=user_id, direction=CategoryDirection.EXPENSE, name="식비"
    )
    db.add(cat)

    db.add(
        RecurringSchedule(
            user_id=user_id,
            type=ScheduleType.INCOME,
            name="월급",
            amount=Decimal("2000000"),
            schedule_day=25,
            start_date=date(2026, 1, 1),
            target_account_id=uuid.uuid4(),
        )
    )
    await db.flush()

    await create_or_update_allocation(
        db, user_id, cat.id, Decimal("300000"), date(2026, 4, 15)
    )

    overview = await get_budget_overview(db, user_id, date(2026, 4, 15))
    assert overview["total_allocated"] == Decimal("300000")
    assert overview["unallocated"] == Decimal("1700000")


async def test_category_budget_status(db):
    user_id = uuid.uuid4()
    account = Account(
        user_id=user_id,
        account_type=AccountType.CASH,
        name="통장",
        currency="KRW",
    )
    cat = Category(
        user_id=user_id, direction=CategoryDirection.EXPENSE, name="식비"
    )
    db.add_all([account, cat])
    await db.flush()

    # 배분 설정: 50만원
    await create_or_update_allocation(
        db, user_id, cat.id, Decimal("500000"), date(2026, 4, 15)
    )

    # 지출 입력: 20만원
    await create_entry(
        db,
        user_id,
        account_id=account.id,
        type=EntryType.EXPENSE,
        amount=Decimal("-200000"),
        currency="KRW",
        category_id=cat.id,
        transacted_at=datetime(2026, 4, 12, tzinfo=timezone.utc),
    )

    budgets = await get_category_budgets(db, user_id, date(2026, 4, 15))
    assert len(budgets) == 1
    assert budgets[0]["allocated"] == Decimal("500000")
    assert budgets[0]["spent"] == Decimal("200000")
    assert budgets[0]["remaining"] == Decimal("300000")


async def test_update_existing_allocation(db):
    """같은 카테고리/기간에 대해 배분 금액을 수정할 수 있어야 합니다."""
    user_id = uuid.uuid4()
    cat = Category(
        user_id=user_id, direction=CategoryDirection.EXPENSE, name="교통비"
    )
    db.add(cat)
    await db.flush()

    alloc1 = await create_or_update_allocation(
        db, user_id, cat.id, Decimal("100000"), date(2026, 4, 15)
    )
    alloc2 = await create_or_update_allocation(
        db, user_id, cat.id, Decimal("150000"), date(2026, 4, 15)
    )

    # 같은 allocation이 업데이트되어야 합니다
    assert str(alloc1.id) == str(alloc2.id)
    assert alloc2.amount == Decimal("150000")


async def test_no_spending_shows_zero(db):
    """지출이 없으면 spent=0, remaining=allocated 여야 합니다."""
    user_id = uuid.uuid4()
    cat = Category(
        user_id=user_id, direction=CategoryDirection.EXPENSE, name="여가"
    )
    db.add(cat)
    await db.flush()

    await create_or_update_allocation(
        db, user_id, cat.id, Decimal("200000"), date(2026, 4, 15)
    )

    budgets = await get_category_budgets(db, user_id, date(2026, 4, 15))
    assert len(budgets) == 1
    assert budgets[0]["spent"] == Decimal("0")
    assert budgets[0]["remaining"] == Decimal("200000")
