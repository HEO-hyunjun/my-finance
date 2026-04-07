import uuid
from decimal import Decimal
from datetime import datetime, timezone

from app.models.account import AccountType
from app.models.entry import EntryType
from app.services.account_service import (
    create_account, get_accounts, get_account_summary,
)
from app.services.entry_service import create_entry


async def test_create_and_get_account(db):
    user_id = uuid.uuid4()
    account = await create_account(db, user_id, {
        "account_type": AccountType.CASH,
        "name": "급여통장",
        "currency": "KRW",
    })
    assert account.name == "급여통장"

    accounts = await get_accounts(db, user_id)
    assert len(accounts) == 1


async def test_account_summary_with_balance(db):
    user_id = uuid.uuid4()
    account = await create_account(db, user_id, {
        "account_type": AccountType.CASH,
        "name": "테스트",
        "currency": "KRW",
    })
    await create_entry(db, user_id, account_id=account.id, type=EntryType.INCOME,
                       amount=Decimal("1000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))
    await db.commit()

    summary = await get_account_summary(db, user_id, account.id)
    assert summary["balance"] == Decimal("1000000")
