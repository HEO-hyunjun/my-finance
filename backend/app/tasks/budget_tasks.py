import asyncio
import logging
from datetime import date

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_async_session():
    """Create async session factory for Celery tasks"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine


@celery_app.task(name="app.tasks.budget_tasks.deduct_fixed_expenses")
def deduct_fixed_expenses():
    """고정비 자동 차감: 결제일에 해당하는 고정비를 지출로 자동 기록"""
    return asyncio.run(_deduct_fixed_expenses_async())


async def _deduct_fixed_expenses_async():
    from sqlalchemy import select
    from app.models.budget import FixedExpense, Expense

    async_session, engine = _get_async_session()
    today = date.today()

    async with async_session() as db:
        # Find all active fixed expenses where payment_day == today's day
        stmt = select(FixedExpense).where(
            FixedExpense.is_active == True,
            FixedExpense.payment_day == today.day,
        )
        result = await db.execute(stmt)
        fixed_expenses = result.scalars().all()

        count = 0
        for fe in fixed_expenses:
            # Check if already deducted today (avoid duplicates)
            check_stmt = select(Expense).where(
                Expense.user_id == fe.user_id,
                Expense.category_id == fe.category_id,
                Expense.spent_at == today,
                Expense.memo == f"[자동] {fe.name}",
            )
            existing = (await db.execute(check_stmt)).scalar_one_or_none()
            if existing:
                continue

            expense = Expense(
                user_id=fe.user_id,
                category_id=fe.category_id,
                amount=fe.amount,
                memo=f"[자동] {fe.name}",
                payment_method=fe.payment_method,
                spent_at=today,
            )
            db.add(expense)
            count += 1

        await db.commit()
        logger.info(f"Fixed expenses deducted: {count} items on {today}")

    await engine.dispose()
    return {"deducted": count, "date": str(today)}


@celery_app.task(name="app.tasks.budget_tasks.deduct_installments")
def deduct_installments():
    """할부금 자동 차감: 결제일에 해당하는 할부금을 지출로 자동 기록"""
    return asyncio.run(_deduct_installments_async())


async def _deduct_installments_async():
    from sqlalchemy import select
    from app.models.budget import Installment, Expense

    async_session, engine = _get_async_session()
    today = date.today()

    async with async_session() as db:
        stmt = select(Installment).where(
            Installment.is_active == True,
            Installment.payment_day == today.day,
        )
        result = await db.execute(stmt)
        installments = result.scalars().all()

        count = 0
        for inst in installments:
            if inst.paid_installments >= inst.total_installments:
                continue

            # Check duplicate
            description = f"[자동할부] {inst.name} ({inst.paid_installments + 1}/{inst.total_installments})"
            check_stmt = select(Expense).where(
                Expense.user_id == inst.user_id,
                Expense.category_id == inst.category_id,
                Expense.spent_at == today,
                Expense.memo == description,
            )
            existing = (await db.execute(check_stmt)).scalar_one_or_none()
            if existing:
                continue

            expense = Expense(
                user_id=inst.user_id,
                category_id=inst.category_id,
                amount=inst.monthly_amount,
                memo=description,
                payment_method=inst.payment_method,
                spent_at=today,
            )
            db.add(expense)

            inst.paid_installments += 1
            if inst.paid_installments >= inst.total_installments:
                inst.is_active = False

            count += 1

        await db.commit()
        logger.info(f"Installments deducted: {count} items on {today}")

    await engine.dispose()
    return {"deducted": count, "date": str(today)}
