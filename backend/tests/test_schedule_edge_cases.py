"""스케줄 서비스 엣지케이스 테스트"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.account import Account, AccountType
from app.models.entry import EntryType
from app.models.recurring_schedule import RecurringSchedule, ScheduleType
from app.services.entry_service import create_entry
from app.services.schedule_service import (
    execute_schedule,
    execute_due_schedules,
    compensate_missed_schedules,
)


async def _setup(db):
    user_id = uuid.uuid4()
    src = Account(user_id=user_id, account_type=AccountType.CASH, name="급여통장", currency="KRW")
    dst = Account(user_id=user_id, account_type=AccountType.PARKING, name="CMA", currency="KRW")
    db.add_all([src, dst])
    await db.flush()
    # 충분한 잔액
    await create_entry(db, user_id, account_id=src.id, type=EntryType.INCOME,
                       amount=Decimal("10000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))
    return user_id, src, dst


# ─── schedule_day=0 (말일) ───


async def test_day_zero_means_last_day_of_month(db):
    """schedule_day=0은 해당 월의 말일에 실행되어야 한다 (4월 → 30일)"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="말일 수입",
        amount=Decimal("100000"), schedule_day=0,
        start_date=date(2026, 1, 1),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 30))
    assert entry is not None
    assert entry.transacted_at.day == 30  # 4월 말일


async def test_day_zero_february_non_leap(db):
    """schedule_day=0 + 2월 비윤년 → 28일에 실행"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="말일 수입",
        amount=Decimal("100000"), schedule_day=0,
        start_date=date(2026, 1, 1),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 2, 28))
    assert entry is not None
    assert entry.transacted_at.day == 28


async def test_day_zero_february_leap_year(db):
    """schedule_day=0 + 2월 윤년 → 29일에 실행"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="말일 수입",
        amount=Decimal("100000"), schedule_day=0,
        start_date=date(2024, 1, 1),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2024, 2, 29))
    assert entry is not None
    assert entry.transacted_at.day == 29


# ─── 짧은 달 처리 (schedule_day=31) ───


async def test_day_31_in_short_month(db):
    """schedule_day=31인데 4월(30일)이면 → 30일에 실행"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="월말 수입",
        amount=Decimal("100000"), schedule_day=31,
        start_date=date(2026, 1, 1),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 30))
    assert entry is not None
    assert entry.transacted_at.day == 30


async def test_day_31_in_february(db):
    """schedule_day=31 + 2월 → 28일에 실행"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="월말 수입",
        amount=Decimal("100000"), schedule_day=31,
        start_date=date(2026, 1, 1),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 2, 28))
    assert entry is not None
    assert entry.transacted_at.day == 28


# ─── 비활성 스케줄 ───


async def test_inactive_schedule_skipped(db):
    """is_active=False인 스케줄은 실행되지 않는다"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="비활성",
        amount=Decimal("100000"), schedule_day=15,
        start_date=date(2026, 1, 1),
        target_account_id=dst.id,
        is_active=False,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 15))
    assert entry is None


# ─── 종료일 이후 ───


async def test_past_end_date_skipped(db):
    """target_date > end_date이면 실행되지 않는다"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="만료됨",
        amount=Decimal("100000"), schedule_day=15,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 15))
    assert entry is None


async def test_on_end_date_still_executes(db):
    """target_date == end_date이면 실행된다 (초과만 스킵)"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="마지막 달",
        amount=Decimal("100000"), schedule_day=15,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 4, 15),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 15))
    assert entry is not None


# ─── total_count 경계 ───


async def test_total_count_exact_boundary(db):
    """executed_count == total_count이면 더 이상 실행 안 됨"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="3회한정",
        amount=Decimal("100000"), schedule_day=10,
        start_date=date(2026, 1, 1),
        total_count=3, executed_count=3,
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 10))
    assert entry is None


# ─── 계좌 누락 ───


async def test_expense_without_source_account(db):
    """EXPENSE인데 source_account_id가 없으면 None 반환"""
    user_id, _, _ = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.EXPENSE, name="계좌없음",
        amount=Decimal("50000"), schedule_day=15,
        start_date=date(2026, 1, 1),
        source_account_id=None,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 15))
    assert entry is None


async def test_income_without_target_account(db):
    """INCOME인데 target_account_id가 없으면 None 반환"""
    user_id, _, _ = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="계좌없음",
        amount=Decimal("50000"), schedule_day=15,
        start_date=date(2026, 1, 1),
        target_account_id=None,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 15))
    assert entry is None


async def test_transfer_missing_one_account(db):
    """TRANSFER인데 source만 있고 target이 없으면 None 반환"""
    user_id, src, _ = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.TRANSFER, name="불완전 이체",
        amount=Decimal("50000"), schedule_day=15,
        start_date=date(2026, 1, 1),
        source_account_id=src.id,
        target_account_id=None,
    )
    db.add(schedule)
    await db.flush()

    entry = await execute_schedule(db, schedule, date(2026, 4, 15))
    assert entry is None


# ─── TRANSFER 중복 체크 (2개 Entry 생성) ───


async def test_transfer_duplicate_check_with_two_entries(db):
    """TRANSFER는 entry 2개(out+in) 생성 — 중복 체크에서 에러 없이 스킵되어야 함"""
    user_id, src, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.TRANSFER, name="이체 중복테스트",
        amount=Decimal("100000"), schedule_day=10,
        start_date=date(2026, 1, 1),
        source_account_id=src.id, target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry1 = await execute_schedule(db, schedule, date(2026, 4, 10))
    assert entry1 is not None
    # 같은 달 재실행 → 에러 없이 None 반환
    entry2 = await execute_schedule(db, schedule, date(2026, 4, 10))
    assert entry2 is None
    assert schedule.executed_count == 1


# ─── 다른 달 중복 체크는 통과 ───


async def test_different_month_not_duplicate(db):
    """같은 스케줄이라도 다른 달이면 중복이 아님"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="월급",
        amount=Decimal("3000000"), schedule_day=25,
        start_date=date(2026, 1, 1),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    entry1 = await execute_schedule(db, schedule, date(2026, 3, 25))
    assert entry1 is not None
    entry2 = await execute_schedule(db, schedule, date(2026, 4, 25))
    assert entry2 is not None
    assert schedule.executed_count == 2


# ─── execute_due_schedules 배치 ───


async def test_execute_due_schedules_batch(db):
    """오늘 실행해야 할 스케줄만 배치 실행"""
    user_id, _, dst = await _setup(db)
    # 15일 스케줄 2개, 20일 스케줄 1개
    s1 = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="수입A",
        amount=Decimal("100000"), schedule_day=15,
        start_date=date(2026, 1, 1), target_account_id=dst.id,
    )
    s2 = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="수입B",
        amount=Decimal("200000"), schedule_day=15,
        start_date=date(2026, 1, 1), target_account_id=dst.id,
    )
    s3 = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="수입C",
        amount=Decimal("300000"), schedule_day=20,
        start_date=date(2026, 1, 1), target_account_id=dst.id,
    )
    db.add_all([s1, s2, s3])
    await db.flush()

    result = await execute_due_schedules(db, date(2026, 4, 15))
    assert result["executed"] == 2
    assert result["skipped"] == 0


# ─── execute_due_schedules에서 schedule_day=0 ───


async def test_due_schedules_day_zero_on_last_day(db):
    """말일(day=0) 스케줄은 해당 월의 마지막 날에 배치에서 실행되어야 한다"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="말일 수입",
        amount=Decimal("100000"), schedule_day=0,
        start_date=date(2026, 1, 1), target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    # 4월 30일 (4월 마지막 날)에 실행
    result = await execute_due_schedules(db, date(2026, 4, 30))
    assert result["executed"] == 1, (
        "schedule_day=0인 스케줄이 월말에 배치 실행되지 않음 - "
        "execute_due_schedules가 day=0을 처리하지 못하는 버그"
    )


# ─── compensate_missed_schedules ───


async def test_compensate_picks_up_missed(db):
    """보상 실행: 이번 달 실행일이 지났지만 아직 실행되지 않은 스케줄을 보상"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="놓친 수입",
        amount=Decimal("100000"), schedule_day=5,
        start_date=date(2026, 1, 1), target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    # 4월 15일 시점에 보상 실행 → 5일 스케줄이 아직 실행 안 됐으므로 보상
    result = await compensate_missed_schedules(db, date(2026, 4, 15))
    assert result["executed"] == 1


async def test_compensate_skips_already_executed(db):
    """이미 실행된 스케줄은 보상 시 중복 실행되지 않음"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="이미 실행됨",
        amount=Decimal("100000"), schedule_day=5,
        start_date=date(2026, 1, 1), target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    # 먼저 정상 실행
    await execute_schedule(db, schedule, date(2026, 4, 5))
    # 보상 실행 → 이미 있으므로 스킵
    result = await compensate_missed_schedules(db, date(2026, 4, 15))
    assert result["skipped"] >= 1
    assert result["executed"] == 0  # 이 스케줄이 다시 실행되면 안 됨


async def test_compensate_day_zero(db):
    """보상 실행에서 schedule_day=0 스케줄도 처리되어야 한다"""
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="말일 보상",
        amount=Decimal("100000"), schedule_day=0,
        start_date=date(2026, 1, 1), target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    # 3월 31일 시점에서 보상 — schedule_day=0 <= 31이므로 쿼리에 포함됨
    result = await compensate_missed_schedules(db, date(2026, 3, 31))
    # day=0 처리가 정상이면 에러 없이 실행됨
    assert len(result["errors"]) == 0, f"day=0 보상 실행 중 에러 발생: {result['errors']}"
    assert result["executed"] >= 1  # 이 스케줄 포함
