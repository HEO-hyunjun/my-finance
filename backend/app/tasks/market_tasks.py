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
    from datetime import date

    from sqlalchemy import select

    from app.models.security import AssetClass, DataSource, Security, SecurityPrice
    from app.services.market_service import MarketService

    async_session, engine = _get_async_session()
    redis_client = _get_redis_client()

    try:
        async with async_session() as db:
            # Security 모델에서 심볼 + asset_class 추출
            stmt = select(Security).where(
                Security.symbol.isnot(None), Security.symbol != ""
            )
            result = await db.execute(stmt)
            securities = result.scalars().all()
            symbol_pairs = [(s.symbol, s.asset_class) for s in securities]

            market = MarketService(redis_client)
            results = await market.warm_cache_for_symbols(symbol_pairs)

            # 캐시된 시세를 security_prices DB에도 저장
            today = date.today()
            for sec in securities:
                try:
                    price_data = await market.get_price(sec.symbol, sec.asset_class)
                    if price_data and price_data.price > 0:
                        existing = (
                            await db.execute(
                                select(SecurityPrice).where(
                                    SecurityPrice.security_id == sec.id,
                                    SecurityPrice.price_date == today,
                                )
                            )
                        ).scalar_one_or_none()
                        if existing:
                            existing.close_price = price_data.price
                            existing.currency = price_data.currency
                        else:
                            db.add(
                                SecurityPrice(
                                    security_id=sec.id,
                                    price_date=today,
                                    close_price=price_data.price,
                                    currency=price_data.currency,
                                )
                            )
                except Exception:
                    pass

            # 환율도 저장
            try:
                fx_data = await market.get_exchange_rate()
                if fx_data and fx_data.rate > 0:
                    fx_sec = (
                        await db.execute(
                            select(Security).where(Security.symbol == "USDKRW=X")
                        )
                    ).scalar_one_or_none()
                    if not fx_sec:
                        fx_sec = Security(
                            symbol="USDKRW=X",
                            name="USD/KRW",
                            currency="KRW",
                            asset_class=AssetClass.CURRENCY_PAIR,
                            data_source=DataSource.YAHOO,
                        )
                        db.add(fx_sec)
                        await db.flush()
                    fx_existing = (
                        await db.execute(
                            select(SecurityPrice).where(
                                SecurityPrice.security_id == fx_sec.id,
                                SecurityPrice.price_date == today,
                            )
                        )
                    ).scalar_one_or_none()
                    if fx_existing:
                        fx_existing.close_price = fx_data.rate
                    else:
                        db.add(
                            SecurityPrice(
                                security_id=fx_sec.id,
                                price_date=today,
                                close_price=fx_data.rate,
                                currency="KRW",
                            )
                        )
            except Exception:
                pass

            await db.commit()

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
