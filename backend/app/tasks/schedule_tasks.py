import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.tz import today as tz_today

logger = logging.getLogger(__name__)


def _get_async_session():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine


@celery_app.task(name="app.tasks.schedule_tasks.execute_daily_schedules")
def execute_daily_schedules():
    """매일 실행: schedule_day == today인 활성 스케줄 처리"""
    return asyncio.run(_execute_daily_async())


async def _execute_daily_async():
    from app.services.schedule_service import execute_due_schedules

    async_session, engine = _get_async_session()
    today = tz_today()

    try:
        async with async_session() as db:
            result = await execute_due_schedules(db, today)
            logger.info(f"Daily schedules executed: {result}")
            return result
    finally:
        await engine.dispose()


@celery_app.task(name="app.tasks.schedule_tasks.compensate_missed_schedules")
def compensate_missed_schedules():
    """서버 시작 시 이번 달 누락 스케줄 보상"""
    return asyncio.run(_compensate_async())


async def _compensate_async():
    from app.services.schedule_service import compensate_missed_schedules as _compensate

    async_session, engine = _get_async_session()
    today = tz_today()

    try:
        async with async_session() as db:
            result = await _compensate(db, today)
            logger.info(f"Compensation completed: {result}")
            return result
    finally:
        await engine.dispose()
