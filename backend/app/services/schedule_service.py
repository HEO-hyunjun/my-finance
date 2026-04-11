import uuid
import calendar
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, EntryType
from app.models.recurring_schedule import RecurringSchedule, ScheduleType
from app.services.entry_service import create_entry, create_transfer


async def create_schedule(db: AsyncSession, user_id: uuid.UUID, data: dict) -> RecurringSchedule:
    schedule = RecurringSchedule(user_id=user_id, **data)
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def get_schedules(db: AsyncSession, user_id: uuid.UUID) -> list[RecurringSchedule]:
    stmt = (
        select(RecurringSchedule)
        .where(RecurringSchedule.user_id == user_id)
        .order_by(RecurringSchedule.schedule_day)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_schedule(db: AsyncSession, user_id: uuid.UUID, schedule_id: uuid.UUID) -> RecurringSchedule:
    stmt = select(RecurringSchedule).where(
        RecurringSchedule.id == schedule_id,
        RecurringSchedule.user_id == user_id,
    )
    schedule = (await db.execute(stmt)).scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


async def update_schedule(
    db: AsyncSession, user_id: uuid.UUID, schedule_id: uuid.UUID, data: dict,
) -> RecurringSchedule:
    schedule = await get_schedule(db, user_id, schedule_id)
    for field, value in data.items():
        setattr(schedule, field, value)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def delete_schedule(db: AsyncSession, user_id: uuid.UUID, schedule_id: uuid.UUID) -> None:
    schedule = await get_schedule(db, user_id, schedule_id)
    await db.delete(schedule)
    await db.commit()


async def toggle_schedule(db: AsyncSession, user_id: uuid.UUID, schedule_id: uuid.UUID) -> RecurringSchedule:
    schedule = await get_schedule(db, user_id, schedule_id)
    schedule.is_active = not schedule.is_active
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def execute_schedule(db: AsyncSession, schedule: RecurringSchedule, target_date: date) -> Entry | None:
    """스케줄 1건 실행: Entry 생성. 중복 체크 포함.

    Returns: 생성된 Entry 또는 None (이미 실행됨/종료 조건 도달)
    """
    # 종료 조건 체크
    if not schedule.is_active:
        return None
    if schedule.end_date and target_date > schedule.end_date:
        return None
    if schedule.total_count is not None and schedule.executed_count >= schedule.total_count:
        return None

    # 중복 체크: 이번 달 같은 스케줄에서 생성된 Entry가 있는지
    check_stmt = select(Entry.id).where(
        Entry.recurring_schedule_id == schedule.id,
        extract("year", Entry.transacted_at) == target_date.year,
        extract("month", Entry.transacted_at) == target_date.month,
    )
    if (await db.execute(check_stmt)).scalar_one_or_none():
        return None

    _, last_day = calendar.monthrange(target_date.year, target_date.month)
    if schedule.schedule_day == 0:
        exec_day = last_day
    else:
        exec_day = min(schedule.schedule_day, last_day)
    ts = datetime(target_date.year, target_date.month, exec_day, tzinfo=timezone.utc)

    if schedule.type == ScheduleType.TRANSFER:
        if not schedule.source_account_id or not schedule.target_account_id:
            return None
        group = await create_transfer(
            db,
            schedule.user_id,
            source_account_id=schedule.source_account_id,
            target_account_id=schedule.target_account_id,
            amount=schedule.amount,
            currency=schedule.currency,
            memo=f"[자동] {schedule.name}",
            transacted_at=ts,
            recurring_schedule_id=schedule.id,
        )
        # transfer creates 2 entries, return the first one
        entry = (
            await db.execute(select(Entry).where(Entry.entry_group_id == group.id).limit(1))
        ).scalar_one()
    elif schedule.type == ScheduleType.INCOME:
        if not schedule.target_account_id:
            return None
        entry = await create_entry(
            db,
            schedule.user_id,
            account_id=schedule.target_account_id,
            type=EntryType.INCOME,
            amount=abs(schedule.amount),
            currency=schedule.currency,
            category_id=schedule.category_id,
            memo=f"[자동] {schedule.name}",
            recurring_schedule_id=schedule.id,
            transacted_at=ts,
        )
    elif schedule.type == ScheduleType.EXPENSE:
        if not schedule.source_account_id:
            return None
        entry = await create_entry(
            db,
            schedule.user_id,
            account_id=schedule.source_account_id,
            type=EntryType.EXPENSE,
            amount=-abs(schedule.amount),
            currency=schedule.currency,
            category_id=schedule.category_id,
            memo=f"[자동] {schedule.name}",
            recurring_schedule_id=schedule.id,
            transacted_at=ts,
        )
    else:
        return None

    schedule.executed_count += 1
    # 횟수 도달 시 자동 비활성화
    if schedule.total_count is not None and schedule.executed_count >= schedule.total_count:
        schedule.is_active = False

    await db.flush()
    return entry


async def execute_due_schedules(db: AsyncSession, today: date) -> dict:
    """오늘 실행해야 할 모든 스케줄을 처리. Celery 태스크에서 호출."""
    _, last_day = calendar.monthrange(today.year, today.month)
    is_last_day = today.day == last_day

    from sqlalchemy import or_

    conditions = [RecurringSchedule.schedule_day == today.day]
    if is_last_day:
        conditions.append(RecurringSchedule.schedule_day == 0)

    stmt = select(RecurringSchedule).where(
        RecurringSchedule.is_active.is_(True),
        or_(*conditions),
    )
    schedules = (await db.execute(stmt)).scalars().all()

    executed = 0
    skipped = 0
    errors = []

    for schedule in schedules:
        try:
            result = await execute_schedule(db, schedule, today)
            if result:
                executed += 1
            else:
                skipped += 1
        except Exception as e:
            errors.append({"schedule_id": str(schedule.id), "name": schedule.name, "error": str(e)})

    await db.commit()
    return {"executed": executed, "skipped": skipped, "errors": errors}


async def compensate_missed_schedules(db: AsyncSession, today: date) -> dict:
    """이번 달 누락된 스케줄 보상 실행. schedule_day <= today.day인 활성 스케줄 대상."""
    stmt = select(RecurringSchedule).where(
        RecurringSchedule.is_active.is_(True),
        RecurringSchedule.schedule_day <= today.day,
    )
    schedules = (await db.execute(stmt)).scalars().all()

    executed = 0
    skipped = 0
    errors = []

    for schedule in schedules:
        try:
            result = await execute_schedule(db, schedule, today)
            if result:
                executed += 1
            else:
                skipped += 1
        except Exception as e:
            errors.append({"schedule_id": str(schedule.id), "name": schedule.name, "error": str(e)})

    await db.commit()
    return {"executed": executed, "skipped": skipped, "errors": errors}
