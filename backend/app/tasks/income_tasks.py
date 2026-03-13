import asyncio
import calendar
import logging
from datetime import date

from app.core.tz import today as tz_today

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_async_session():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine


@celery_app.task(name="app.tasks.income_tasks.generate_recurring_incomes")
def generate_recurring_incomes():
    """recurring_day == 오늘인 활성 정기 수입 템플릿에서 실제 수입 레코드를 자동 생성"""
    return asyncio.run(_generate_recurring_incomes_async())


async def _generate_recurring_incomes_async():
    from sqlalchemy import select, extract

    from app.models.income import Income, RecurringIncome

    async_session, engine = _get_async_session()
    today = tz_today()

    try:
        async with async_session() as db:
            # recurring_day가 오늘이고 활성인 정기 수입 템플릿 조회
            stmt = select(RecurringIncome).where(
                RecurringIncome.is_active.is_(True),
                RecurringIncome.recurring_day == today.day,
            )
            templates = (await db.execute(stmt)).scalars().all()

            created = 0
            for tmpl in templates:
                # 중복 방지: 이번 달 같은 템플릿의 수입이 이미 있는지
                check_stmt = select(Income.id).where(
                    Income.recurring_income_id == tmpl.id,
                    extract("year", Income.received_at) == today.year,
                    extract("month", Income.received_at) == today.month,
                )
                existing = (await db.execute(check_stmt)).scalar_one_or_none()
                if existing:
                    continue

                _, last_day = calendar.monthrange(today.year, today.month)
                recv_day = min(tmpl.recurring_day, last_day)

                new_income = Income(
                    user_id=tmpl.user_id,
                    type=tmpl.type,
                    amount=tmpl.amount,
                    description=tmpl.description,
                    recurring_income_id=tmpl.id,
                    target_asset_id=tmpl.target_asset_id,
                    received_at=date(today.year, today.month, recv_day),
                )
                db.add(new_income)
                created += 1

            await db.commit()
            logger.info(f"Recurring incomes generated: {created} created from {len(templates)} templates")
            return {"created": created, "templates": len(templates)}
    finally:
        await engine.dispose()
