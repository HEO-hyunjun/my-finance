import asyncio
import logging
from datetime import date

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.snapshot_tasks.take_daily_snapshot")
def take_daily_snapshot():
    """모든 사용자의 자산 스냅샷을 일일 기록"""
    return asyncio.run(_take_daily_snapshot_async())


async def _take_daily_snapshot_async():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    import redis.asyncio as aioredis

    from app.core.config import settings
    from app.models.user import User
    from app.models.portfolio import AssetSnapshot
    from app.services.asset_service import get_asset_summary
    from app.services.market_service import MarketService

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    redis_client = aioredis.from_url(settings.REDIS_URL)
    market = MarketService(redis_client)
    today = date.today()

    async with async_session() as db:
        users = (await db.execute(select(User))).scalars().all()
        count = 0

        for user in users:
            try:
                # Check if snapshot already exists for today
                existing = (await db.execute(
                    select(AssetSnapshot).where(
                        AssetSnapshot.user_id == user.id,
                        AssetSnapshot.snapshot_date == today,
                    )
                )).scalar_one_or_none()

                if existing:
                    continue

                summary = await get_asset_summary(db, user.id, market)

                snapshot = AssetSnapshot(
                    user_id=user.id,
                    snapshot_date=today,
                    total_krw=summary.total_value_krw,
                    breakdown=summary.breakdown,
                )
                db.add(snapshot)
                count += 1
            except Exception as e:
                logger.warning(f"Snapshot failed for user {user.id}: {e}")

        await db.commit()
        logger.info(f"Daily snapshots taken: {count} users on {today}")

    await redis_client.aclose()
    await engine.dispose()
    return {"snapshots": count, "date": str(today)}
