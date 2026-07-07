"""캘린더 이벤트의 entry_id 노출 테스트.

실제 Entry 기반 이벤트는 entry_id를 가지고,
예정 스케줄 항목은 entry_id가 None이다 (표시 전용).
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.account import Account, AccountType
from app.models.entry import EntryType
from app.models.recurring_schedule import RecurringSchedule, ScheduleType
from app.services.calendar_service import get_calendar_events
from app.services.entry_service import create_entry


async def test_calendar_event_entry_id_exposure(db):
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.CASH, name="통장", currency="KRW")
    db.add(acc)
    await db.flush()

    # 실제 지출 Entry (2026-07)
    await create_entry(
        db, user_id, account_id=acc.id, type=EntryType.EXPENSE,
        amount=Decimal("-50000"), currency="KRW", memo="점심",
        transacted_at=datetime(2026, 7, 10, 12, tzinfo=timezone.utc),
    )
    # 아직 실행 안 된 예정 스케줄
    db.add(RecurringSchedule(
        user_id=user_id, type=ScheduleType.EXPENSE, name="월세",
        amount=Decimal("500000"), currency="KRW", schedule_day=25,
        start_date=date(2026, 1, 1), source_account_id=acc.id,
    ))
    await db.flush()

    resp = await get_calendar_events(db, user_id, 2026, 7)

    entry_events = [e for e in resp.events if e.title == "점심"]
    schedule_events = [e for e in resp.events if e.title == "월세"]

    assert len(entry_events) == 1
    assert entry_events[0].entry_id is not None
    assert len(schedule_events) == 1
    assert schedule_events[0].entry_id is None
