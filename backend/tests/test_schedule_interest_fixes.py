"""짧은 달 스케줄 선택/보상 및 이자 캡·백필 수정 테스트"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.tz import APP_TZ, kst_noon_utc
from app.models.account import Account, AccountType
from app.models.entry import Entry, EntryType
from app.models.recurring_schedule import RecurringSchedule, ScheduleType
from app.services.entry_service import create_entry
from app.services.interest_service import calculate_ledger_accrued_interest
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
    await create_entry(db, user_id, account_id=src.id, type=EntryType.INCOME,
                       amount=Decimal("10000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))
    return user_id, src, dst


@pytest.fixture
async def iso_db():
    """격리된 in-memory 엔진 세션.

    execute_due/compensate는 내부에서 commit하고 유저 필터 없이 전역 조회하므로,
    세션 공유 엔진(db 픽스처)에서는 배치 결과가 다른 테스트로 누수된다. 배치·보상
    테스트는 이 픽스처로 각자 독립 DB를 사용한다.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as session:
        yield session
    await engine.dispose()


# ─── Fix 1: 짧은 달 말일에 schedule_day > 말일 스케줄 선택·실행 ───


async def test_due_day_31_selected_on_30day_month_last_day(iso_db):
    """schedule_day=31 스케줄이 30일짜리 달(4월) 말일 배치에서 선택·실행된다"""
    db = iso_db
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="월말 수입",
        amount=Decimal("100000"), schedule_day=31,
        start_date=date(2026, 1, 1), target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    result = await execute_due_schedules(db, date(2026, 4, 30))
    assert result["executed"] == 1


async def test_due_day_29_30_31_all_execute_on_feb_last_day(iso_db):
    """2월 말일(28일)에 schedule_day 29/30/31 모두 배치 실행된다"""
    db = iso_db
    user_id, _, dst = await _setup(db)
    for day in (29, 30, 31):
        db.add(RecurringSchedule(
            user_id=user_id, type=ScheduleType.INCOME, name=f"수입{day}",
            amount=Decimal("100000"), schedule_day=day,
            start_date=date(2026, 1, 1), target_account_id=dst.id,
        ))
    await db.flush()

    # 2026-02-28은 비윤년 2월 말일
    result = await execute_due_schedules(db, date(2026, 2, 28))
    assert result["executed"] == 3


# ─── Fix 2 + 3: 보상 로직 (짧은 달 선택 + end_date 경계 판정) ───


async def test_compensate_day_31_on_short_month_last_day(iso_db):
    """보상에서도 schedule_day=31이 30일짜리 달 말일에 잡힌다"""
    db = iso_db
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="월말 보상",
        amount=Decimal("100000"), schedule_day=31,
        start_date=date(2026, 1, 1), target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    result = await compensate_missed_schedules(db, date(2026, 4, 30))
    assert result["executed"] == 1


async def test_compensate_respects_scheduled_date_within_end_date(iso_db):
    """예정일(4/5)이 end_date(4/10) 이내면, 보상 시점(4/15)이 지났어도 보상된다"""
    db = iso_db
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="놓친 수입",
        amount=Decimal("100000"), schedule_day=5,
        start_date=date(2026, 1, 1), end_date=date(2026, 4, 10),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    result = await compensate_missed_schedules(db, date(2026, 4, 15))
    assert result["executed"] == 1
    # 보상 Entry는 실제 예정일(4/5)로 기록되어야 한다
    entry = (await db.execute(
        select(Entry).where(Entry.recurring_schedule_id == schedule.id)
    )).scalar_one()
    assert entry.transacted_at.astimezone(APP_TZ).date() == date(2026, 4, 5)


async def test_compensate_skips_when_scheduled_date_past_end_date(iso_db):
    """예정일(4/20)이 end_date(4/10)를 넘으면 보상하지 않는다"""
    db = iso_db
    user_id, _, dst = await _setup(db)
    schedule = RecurringSchedule(
        user_id=user_id, type=ScheduleType.INCOME, name="만료 수입",
        amount=Decimal("100000"), schedule_day=20,
        start_date=date(2026, 1, 1), end_date=date(2026, 4, 10),
        target_account_id=dst.id,
    )
    db.add(schedule)
    await db.flush()

    result = await compensate_missed_schedules(db, date(2026, 4, 25))
    assert result["executed"] == 0


# ─── Fix 4: 예금 발생이자 만기 캡 ───


class _FakeEntry:
    def __init__(self, amount, transacted_at):
        self.amount = amount
        self.transacted_at = transacted_at


def test_ledger_accrued_capped_at_maturity():
    """as_of가 만기 이후여도 경과일은 만기일까지만 인정된다"""
    maturity = date(2026, 6, 1)
    deposit = _FakeEntry(
        amount=Decimal("1000000"),
        transacted_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
    )

    uncapped = calculate_ledger_accrued_interest(
        [deposit], annual_rate=Decimal("3.650"), tax_rate=Decimal("0"),
        as_of=date(2026, 7, 1),  # 만기 30일 후
    )
    capped = calculate_ledger_accrued_interest(
        [deposit], annual_rate=Decimal("3.650"), tax_rate=Decimal("0"),
        as_of=date(2026, 7, 1), maturity_date=maturity,
    )
    at_maturity = calculate_ledger_accrued_interest(
        [deposit], annual_rate=Decimal("3.650"), tax_rate=Decimal("0"),
        as_of=maturity,
    )

    assert capped < uncapped
    assert capped == at_maturity


# ─── Fix 5: 파킹통장 일일이자 다운타임 백필 ───


async def _static_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


class _NoDisposeEngine:
    """task가 호출하는 engine.dispose()를 무력화 (테스트가 세션 재사용)"""

    async def dispose(self):
        pass


@pytest.mark.asyncio
async def test_parking_backfill_fills_missed_days_and_no_duplicate_on_rerun(monkeypatch):
    from app.core.tz import today as tz_today
    from app.tasks import interest_tasks

    engine = await _static_engine()
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    today = tz_today()

    def _fake_get_async_session():
        return session_factory, _NoDisposeEngine()

    monkeypatch.setattr(interest_tasks, "_get_async_session", _fake_get_async_session)

    user_id = uuid.uuid4()
    # 계좌 생성일을 5일 전으로 설정 → 백필 대상: today-5 .. today (6일)
    created = kst_noon_utc(today - timedelta(days=5))
    async with session_factory() as db:
        acc = Account(
            user_id=user_id, account_type=AccountType.PARKING, name="파킹",
            currency="KRW", interest_rate=Decimal("3.000"), is_active=True,
            created_at=created,
        )
        db.add(acc)
        await db.flush()
        db.add(Entry(
            user_id=user_id, account_id=acc.id, type=EntryType.INCOME,
            amount=Decimal("10000000"), currency="KRW", source="manual",
            transacted_at=created,
        ))
        await db.commit()

    result = await interest_tasks._record_parking_interest_async()
    # 이자 기록이 없으므로 생성일(today-5)부터 today까지 6일 백필
    assert result["recorded"] == 6

    async with session_factory() as db:
        total = (await db.execute(
            select(func.count()).select_from(Entry).where(
                Entry.account_id == acc.id, Entry.source == "interest",
            )
        )).scalar()
        assert total == 6  # 하루당 정확히 1건

    # 재실행 → 중복 없음
    result2 = await interest_tasks._record_parking_interest_async()
    assert result2["recorded"] == 0

    await engine.dispose()
