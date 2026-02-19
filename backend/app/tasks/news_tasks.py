import asyncio
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.news_tasks.collect_news_batch")
def collect_news_batch():
    """뉴스 배치 수집: 전체 자산 + 카테고리별 뉴스 수집 → DB 저장 → Redis 캐시"""
    return asyncio.run(_collect_news_batch_async())


async def _collect_news_batch_async():
    import redis.asyncio as aioredis
    from sqlalchemy import select, distinct
    from app.core.config import settings
    from app.core.database import async_session as AsyncSessionLocal
    from app.models.asset import Asset
    from app.services.news_service import NewsService

    redis_client = aioredis.from_url(settings.REDIS_URL)
    news_service = NewsService(redis_client)

    try:
        # 전체 유저의 보유 자산명 수집 (중복 제거)
        async with AsyncSessionLocal() as db:
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


@celery_app.task(name="app.tasks.news_tasks.process_and_cluster_news")
def process_and_cluster_news():
    """뉴스 LLM 처리 + 클러스터링 파이프라인"""
    return asyncio.run(_process_and_cluster_async())


async def _process_and_cluster_async():
    from sqlalchemy import select
    from app.core.database import async_session as AsyncSessionLocal
    from app.models.news import NewsArticleDB
    from app.services.news_llm_service import (
        process_article_with_llm,
        cluster_articles,
    )

    processed_count = 0
    cluster_count = 0

    async with AsyncSessionLocal() as db:
        # 1. 미처리 기사 LLM 분석 (최대 20개씩)
        stmt = (
            select(NewsArticleDB)
            .where(NewsArticleDB.processed_at.is_(None))
            .order_by(NewsArticleDB.created_at.desc())
            .limit(20)
        )
        result = await db.execute(stmt)
        unprocessed = result.scalars().all()

        for article in unprocessed:
            try:
                res = await process_article_with_llm(db, article.external_id)
                if res:
                    processed_count += 1
            except Exception as e:
                logger.warning(f"LLM processing failed for {article.external_id}: {e}")

        # 2. 클러스터링 실행
        try:
            clusters = await cluster_articles(db)
            cluster_count = len(clusters)
            await db.commit()
        except Exception as e:
            logger.warning(f"Clustering failed: {e}")

    logger.info(f"Processed {processed_count} articles, created {cluster_count} clusters")
    return {"processed": processed_count, "clusters": cluster_count}
