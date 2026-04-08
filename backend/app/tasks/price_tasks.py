import asyncio
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_async_session():
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine


@celery_app.task(name="app.tasks.price_tasks.collect_daily_prices")
def collect_daily_prices():
    """전 종목 + 환율 일별 시세 수집"""
    return asyncio.run(_collect_async())


async def _collect_async():
    from app.services.security_service import fetch_and_save_prices

    async_session, engine = _get_async_session()
    try:
        async with async_session() as db:
            result = await fetch_and_save_prices(db)
            logger.info(f"Daily prices collected: {result}")
            return result
    finally:
        await engine.dispose()
