import uuid
from datetime import date
from decimal import Decimal

from app.models.budget_v2 import BudgetPeriod, BudgetAllocation
from app.models.category import Category, CategoryDirection


async def test_create_budget_period(db):
    period = BudgetPeriod(user_id=uuid.uuid4(), period_start_day=10)
    db.add(period)
    await db.flush()
    assert period.period_start_day == 10


async def test_create_budget_allocation(db):
    user_id = uuid.uuid4()
    cat = Category(user_id=user_id, direction=CategoryDirection.EXPENSE, name="식비")
    db.add(cat)
    await db.flush()

    alloc = BudgetAllocation(
        user_id=user_id,
        category_id=cat.id,
        amount=Decimal("500000"),
        period_start=date(2026, 4, 10),
        period_end=date(2026, 5, 9),
    )
    db.add(alloc)
    await db.flush()
    assert alloc.amount == Decimal("500000")
