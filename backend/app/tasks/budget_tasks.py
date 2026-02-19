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


@celery_app.task(name="app.tasks.budget_tasks.initialize_period_fixed_expenses")
def initialize_period_fixed_expenses():
    """월급일에 해당하는 유저의 활성 고정비를 새 기간 Expense로 일괄 INSERT"""
    return asyncio.run(_initialize_period_fixed_expenses_async())


async def _initialize_period_fixed_expenses_async():
    from sqlalchemy import select
    from app.models.budget import FixedExpense, Expense
    from app.models.user import User
    from app.services.budget_period import get_budget_period

    async_session, engine = _get_async_session()
    today = date.today()

    async with async_session() as db:
        # salary_day == today.day 인 유저만 처리
        user_stmt = select(User).where(User.salary_day == today.day)
        users = (await db.execute(user_stmt)).scalars().all()

        total_count = 0
        for user in users:
            period_start, _ = get_budget_period(today, user.salary_day)

            # 해당 유저의 활성 고정비 전체 조회
            fe_stmt = select(FixedExpense).where(
                FixedExpense.user_id == user.id,
                FixedExpense.is_active.is_(True),
            )
            fixed_expenses = (await db.execute(fe_stmt)).scalars().all()

            for fe in fixed_expenses:
                # 중복 방지: fixed_expense_id + spent_at 조합
                check_stmt = select(Expense).where(
                    Expense.fixed_expense_id == fe.id,
                    Expense.spent_at == period_start,
                )
                existing = (await db.execute(check_stmt)).scalar_one_or_none()
                if existing:
                    continue

                expense = Expense(
                    user_id=fe.user_id,
                    category_id=fe.category_id,
                    amount=fe.amount,
                    memo=f"[고정] {fe.name}",
                    source_asset_id=fe.source_asset_id,
                    fixed_expense_id=fe.id,
                    spent_at=period_start,
                )
                db.add(expense)
                total_count += 1

        await db.commit()
        logger.info(
            f"Period fixed expenses initialized: {total_count} items for {len(users)} users on {today}"
        )

    await engine.dispose()
    return {"initialized": total_count, "users": len(users), "date": str(today)}


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
            Installment.is_active.is_(True),
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
                source_asset_id=inst.source_asset_id,
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
