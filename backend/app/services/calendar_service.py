import uuid

from sqlalchemy import select, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.entry import Entry
from app.models.recurring_schedule import RecurringSchedule


async def get_calendar_events(
    db: AsyncSession, user_id: uuid.UUID, year: int, month: int,
) -> list[dict]:
    """월별 캘린더 이벤트 조회"""
    events = []

    # 1. 실제 발생한 Entry (해당 월)
    entries_stmt = (
        select(Entry)
        .where(
            Entry.user_id == user_id,
            extract("year", Entry.transacted_at) == year,
            extract("month", Entry.transacted_at) == month,
        )
        .order_by(Entry.transacted_at)
    )
    entries = (await db.execute(entries_stmt)).scalars().all()
    for e in entries:
        events.append({
            "type": "entry",
            "entry_type": e.type.value,
            "date": e.transacted_at.strftime("%Y-%m-%d"),
            "amount": float(e.amount),
            "currency": e.currency,
            "memo": e.memo,
            "entry_id": str(e.id),
        })

    # 2. 예정 스케줄 (아직 실행 안 된 것)
    schedules_stmt = select(RecurringSchedule).where(
        RecurringSchedule.user_id == user_id,
        RecurringSchedule.is_active.is_(True),
    )
    schedules = (await db.execute(schedules_stmt)).scalars().all()
    for s in schedules:
        # 이번 달 이미 실행됐는지 체크
        executed_stmt = select(Entry.id).where(
            Entry.recurring_schedule_id == s.id,
            extract("year", Entry.transacted_at) == year,
            extract("month", Entry.transacted_at) == month,
        )
        already_executed = (await db.execute(executed_stmt)).scalar_one_or_none()
        if already_executed:
            continue

        import calendar as cal
        _, last_day = cal.monthrange(year, month)
        sched_day = min(s.schedule_day, last_day)

        events.append({
            "type": "scheduled",
            "schedule_type": s.type.value,
            "date": f"{year}-{month:02d}-{sched_day:02d}",
            "amount": float(s.amount),
            "currency": s.currency,
            "name": s.name,
            "schedule_id": str(s.id),
        })

    # 3. 만기 예정 계좌
    maturity_stmt = select(Account).where(
        Account.user_id == user_id,
        Account.maturity_date.is_not(None),
        extract("year", Account.maturity_date) == year,
        extract("month", Account.maturity_date) == month,
    )
    maturities = (await db.execute(maturity_stmt)).scalars().all()
    for acc in maturities:
        events.append({
            "type": "maturity",
            "date": acc.maturity_date.isoformat(),
            "name": acc.name,
            "account_type": acc.account_type.value,
            "account_id": str(acc.id),
        })

    # 날짜순 정렬
    events.sort(key=lambda x: x["date"])
    return events
