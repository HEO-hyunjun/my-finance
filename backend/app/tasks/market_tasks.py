"""시장 데이터 캐시 워밍 태스크.

TODO: Phase 2 - Asset 모델을 Account/Security 기반으로 교체 예정.
현재는 Security 모델의 심볼을 사용합니다.
"""

import asyncio
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_async_session():
    """Create async session factory for Celery tasks"""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine


def _get_redis_client():
    """Create Redis client for Celery tasks"""
    import redis.asyncio as aioredis

    from app.core.config import settings

    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task(name="app.tasks.market_tasks.warm_market_cache")
def warm_market_cache():
    """모든 유저의 고유 심볼에 대해 시세를 일괄 fetch하여 Redis 캐시에 저장."""
    return asyncio.run(_warm_market_cache_async())


async def _warm_market_cache_async():
    from sqlalchemy import distinct, select

    from app.models.security import Security
    from app.services.market_service import MarketService

    async_session, engine = _get_async_session()
    redis_client = _get_redis_client()

    try:
        async with async_session() as db:
            # Security 모델에서 고유 심볼 추출
            stmt = select(distinct(Security.ticker)).where(
                Security.ticker.isnot(None), Security.ticker != ""
            )
            result = await db.execute(stmt)
            symbols = [(row[0], None) for row in result.all()]

        market = MarketService(redis_client)
        results = await market.warm_cache_for_symbols(symbols)

        success = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)
        logger.info(
            f"Market cache warmed: {success} success, {failed} failed "
            f"out of {len(results)} symbols"
        )
        return {"success": success, "failed": failed, "total": len(results)}
    finally:
        await redis_client.aclose()
        await engine.dispose()
