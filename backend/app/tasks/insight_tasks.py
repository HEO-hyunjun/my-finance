import asyncio
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.insight_tasks.generate_all_user_insights")
def generate_all_user_insights():
    """모든 사용자의 AI 인사이트를 일일 생성"""
    return asyncio.run(_generate_all_user_insights_async())


async def _generate_all_user_insights_async():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    import redis.asyncio as aioredis

    from app.core.config import settings
    from app.models.user import User
    from app.services.insight_service import generate_daily_insights
    from app.services.market_service import MarketService

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    redis_client = aioredis.from_url(settings.REDIS_URL)
    market = MarketService(redis_client)

    async with async_session() as db:
        users = (await db.execute(select(User))).scalars().all()
        count = 0

        for user in users:
            try:
                insights = await generate_daily_insights(db, user.id, market)
                if insights:
                    count += 1
            except Exception as e:
                logger.warning(f"Insight generation failed for user {user.id}: {e}")

        logger.info(f"Daily insights generated for {count}/{len(users)} users")

    await redis_client.aclose()
    await engine.dispose()
    return {"users_processed": count, "total_users": len(users)}
