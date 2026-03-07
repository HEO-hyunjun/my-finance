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


@celery_app.task(name="app.tasks.news_tasks.collect_news_batch")
def collect_news_batch():
    """뉴스 배치 수집: 전체 자산 + 카테고리별 뉴스 수집 → DB 저장 → Redis 캐시"""
    return asyncio.run(_collect_news_batch_async())


async def _collect_news_batch_async():
    import redis.asyncio as aioredis
    from sqlalchemy import select, distinct
    from app.core.config import settings
    from app.models.asset import Asset
    from app.services.news_service import NewsService

    async_session, engine = _get_async_session()
    redis_client = aioredis.from_url(settings.REDIS_URL)
    news_service = NewsService(redis_client)

    try:
        # 전체 유저의 보유 자산명 수집 (중복 제거)
        async with async_session() as db:
            stmt = select(distinct(Asset.name))
            result = await db.execute(stmt)
            asset_names = [row[0] for row in result.all()]

        # 배치 수집 → DB 저장 → Redis 캐시
        result = await news_service.collect_and_cache_all(asset_names)
        logger.info(f"Batch collection complete: {result}")
        return result

    except Exception as e:
        logger.warning(f"News batch collection failed: {e}")
        return {"error": str(e)}
    finally:
        await redis_client.aclose()
        await engine.dispose()


@celery_app.task(name="app.tasks.news_tasks.process_and_cluster_news")
def process_and_cluster_news():
    """당일 뉴스 LLM 처리 + 클러스터링 파이프라인"""
    return asyncio.run(_process_and_cluster_async())


async def _process_and_cluster_async():
    import redis.asyncio as aioredis
    from sqlalchemy import select, func
    from app.core.config import settings
    from app.models.news import NewsArticleDB
    from app.services.news_llm_service import (
        cluster_articles,
        _today_start_utc,
    )

    async_session, engine = _get_async_session()
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    processed_count = 0
    cluster_count = 0
    collected = False

    try:
        # 1. 오늘 수집된 기사가 있는지 확인
        async with async_session() as db:
            today_utc = _today_start_utc()
            count_stmt = select(func.count()).select_from(NewsArticleDB).where(
                NewsArticleDB.created_at >= today_utc
            )
            result = await db.execute(count_stmt)
            today_count = result.scalar() or 0

        # 2. 오늘 기사가 없으면 수집 먼저 실행
        if today_count == 0:
            logger.info("No articles collected today, collecting first...")
            collect_result = await _collect_news_batch_async()
            collected = True
            logger.info(f"Collection result: {collect_result}")

        # 3. 당일 미처리 기사 LLM 분석 + 클러스터링
        # cluster_articles가 내부에서 미처리 기사를 자동 처리함
        async with async_session() as db:
            try:
                clusters = await cluster_articles(
                    db, session_factory=async_session
                )
                cluster_count = len(clusters)
                processed_count = cluster_count  # 클러스터 수로 대체
                await db.commit()
            except Exception as e:
                logger.warning(f"Processing/Clustering failed: {e}")
    finally:
        # 처리 완료 후 Redis 상태 플래그 제거
        await redis_client.delete("news:clustering:status")
        await redis_client.aclose()
        await engine.dispose()

    logger.info(
        f"Processed {processed_count} articles, created {cluster_count} clusters"
        f"{' (collected first)' if collected else ''}"
    )
    return {"processed": processed_count, "clusters": cluster_count, "collected_first": collected}
