import asyncio
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.news_tasks.collect_news_batch")
def collect_news_batch():
    """뉴스 배치 수집: 통합 쿼리 1회로 모든 카테고리 뉴스 수집 + DB 저장"""
    return asyncio.run(_collect_news_batch_async())


async def _collect_news_batch_async():
    import redis.asyncio as aioredis
    from sqlalchemy import select, distinct
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.asset import Asset
    from app.services.news_service import NewsService
    from app.services.news_llm_service import save_articles_to_db
    from app.schemas.news import build_batch_query, classify_article_category

    redis_client = aioredis.from_url(settings.REDIS_URL)
    news_service = NewsService(redis_client)

    total_collected = 0
    total_saved = 0

    try:
        # 전체 유저의 보유 자산명 수집 (중복 제거)
        async with AsyncSessionLocal() as db:
            stmt = select(distinct(Asset.name))
            result = await db.execute(stmt)
            asset_names = [row[0] for row in result.all()]

        # 보유 자산 키워드 포함된 통합 쿼리 생성 (SerpAPI 1회 호출)
        query = build_batch_query(asset_names)
        logger.info(f"Batch query: {query}")

        raw_articles = await news_service._fetch_news(query)
        logger.info(f"Fetched {len(raw_articles)} articles with combined query")

        # 카테고리 자동 분류 후 매핑
        from app.schemas.news import NewsArticle, NewsSource
        articles = []
        for item in raw_articles:
            title = item.get("title", "")
            link = item.get("link", "")
            if not title or not link:
                continue

            category = classify_article_category(title, item.get("snippet"))
            source_data = item.get("source", {})
            articles.append(
                NewsArticle(
                    id=NewsArticle.generate_id(title, link),
                    title=title,
                    link=link,
                    source=NewsSource(
                        name=source_data.get("name", ""),
                        icon=source_data.get("icon"),
                    ),
                    snippet=item.get("snippet"),
                    thumbnail=item.get("thumbnail"),
                    published_at=item.get("date", ""),
                    category=category,
                    related_asset=None,
                )
            )

        total_collected = len(articles)

        # DB에 저장 (중복 스킵)
        if articles:
            async with AsyncSessionLocal() as db:
                total_saved = await save_articles_to_db(db, articles)
                logger.info(f"Saved {total_saved} new articles to DB")

        # 쿼터 증가 (SerpAPI 1회 호출했으므로)
        await news_service._increment_quota()

    except Exception as e:
        logger.warning(f"News batch collection failed: {e}")

    await redis_client.aclose()
    logger.info(f"Total collected: {total_collected}, saved to DB: {total_saved}")
    return {"total_collected": total_collected, "total_saved": total_saved}


@celery_app.task(name="app.tasks.news_tasks.process_and_cluster_news")
def process_and_cluster_news():
    """뉴스 LLM 처리 + 클러스터링 파이프라인"""
    return asyncio.run(_process_and_cluster_async())


async def _process_and_cluster_async():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
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
