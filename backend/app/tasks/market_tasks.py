import asyncio
import logging

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
    from sqlalchemy import select, distinct
    from app.models.asset import Asset
    from app.services.market_service import MarketService

    async_session, engine = _get_async_session()
    redis_client = _get_redis_client()

    try:
        async with async_session() as db:
            # 모든 자산에서 고유 (symbol, asset_type) 쌍 추출
            stmt = (
                select(distinct(Asset.symbol), Asset.asset_type)
                .where(Asset.symbol.isnot(None), Asset.symbol != "")
            )
            result = await db.execute(stmt)
            symbol_pairs = [(row[0], row[1]) for row in result.all()]

        market = MarketService(redis_client)
        results = await market.warm_cache_for_symbols(symbol_pairs)

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
