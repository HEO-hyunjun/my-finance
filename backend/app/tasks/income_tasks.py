import asyncio
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
    """recurring_day == 오늘인 정기 수입을 자동 생성"""
    return asyncio.run(_generate_recurring_incomes_async())


async def _generate_recurring_incomes_async():
    from sqlalchemy import select, and_

    from app.models.income import Income

    async_session, engine = _get_async_session()
    today = tz_today()

    try:
        async with async_session() as db:
            # recurring_day가 오늘인 정기 수입 조회
            stmt = select(Income).where(
                Income.is_recurring.is_(True),
                Income.recurring_day == today.day,
            )
            recurring = (await db.execute(stmt)).scalars().all()

            # 유저+유형별 최신 1건만 (같은 정기 수입이 여러 레코드일 수 있음)
            seen: set[tuple] = set()
            templates: list[Income] = []
            for inc in sorted(recurring, key=lambda x: x.received_at, reverse=True):
                key = (inc.user_id, inc.type, inc.recurring_day)
                if key not in seen:
                    seen.add(key)
                    templates.append(inc)

            created = 0
            for tmpl in templates:
                # 중복 방지: 이번 달 같은 유형+일자 수입이 이미 있는지
                month_start = today.replace(day=1)
                check_stmt = select(Income.id).where(
                    Income.user_id == tmpl.user_id,
                    Income.type == tmpl.type,
                    Income.is_recurring.is_(True),
                    Income.received_at >= month_start,
                    Income.received_at <= today,
                )
                existing = (await db.execute(check_stmt)).scalar_one_or_none()
                if existing:
                    continue

                new_income = Income(
                    user_id=tmpl.user_id,
                    type=tmpl.type,
                    amount=tmpl.amount,
                    description=tmpl.description,
                    is_recurring=True,
                    recurring_day=tmpl.recurring_day,
                    target_asset_id=tmpl.target_asset_id,
                    received_at=today,
                )
                db.add(new_income)
                created += 1

            await db.commit()
            logger.info(f"Recurring incomes generated: {created} created")
            return {"created": created, "templates": len(templates)}
    finally:
        await engine.dispose()
