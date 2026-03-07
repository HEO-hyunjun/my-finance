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


@celery_app.task(name="app.tasks.news_tasks.collect_news_batch")
def collect_news_batch():
    """뉴스 배치 수집: 카테고리별 뉴스 수집 → DB 저장 → Redis 캐시"""
    return asyncio.run(_collect_news_batch_async())


@celery_app.task(name="app.tasks.news_tasks.collect_and_process_news")
def collect_and_process_news():
    """뉴스 수집 → LLM 처리 → 클러스터링 통합 파이프라인.

    수집 완료 후 바로 처리/클러스터링을 실행하여 타이밍 레이스를 제거합니다.
    """
    return asyncio.run(_collect_and_process_async())


async def _collect_and_process_async():
    import redis.asyncio as aioredis
    from app.core.config import settings
    from app.services.news_llm_service import cluster_articles

    collect_result = {}
    cluster_count = 0

    # 1. 수집
    try:
        collect_result = await _collect_news_batch_async()
    except Exception as e:
        logger.warning(f"Collection phase failed: {e}")

    # 2. LLM 처리 + 클러스터링 (수집 완료 보장 후 실행)
    async_session, engine = _get_async_session()
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        async with async_session() as db:
            clusters = await cluster_articles(
                db, session_factory=async_session
            )
            cluster_count = len(clusters)
            await db.commit()
    except Exception as e:
        logger.warning(f"Processing/Clustering phase failed: {e}")
    finally:
        await redis_client.delete("news:clustering:status")
        await redis_client.aclose()
        await engine.dispose()

    logger.info(
        f"Pipeline complete: collected={collect_result.get('unique', 0)}, "
        f"clusters={cluster_count}"
    )
    return {
        "collected": collect_result.get("unique", 0),
        "saved": collect_result.get("saved", 0),
        "clusters": cluster_count,
    }


@celery_app.task(name="app.tasks.news_tasks.process_and_cluster_news")
def process_and_cluster_news():
    """당일 뉴스 LLM 처리 + 클러스터링 (수동 트리거용).

    수집은 하지 않고 기존 기사에 대해서만 처리/클러스터링을 수행합니다.
    기사가 없으면 수집을 먼저 실행합니다.
    """
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
    cluster_count = 0
    collected = False

    try:
        # 오늘 수집된 기사가 있는지 확인
        async with async_session() as db:
            today_utc = _today_start_utc()
            count_stmt = select(func.count()).select_from(NewsArticleDB).where(
                NewsArticleDB.created_at >= today_utc
            )
            result = await db.execute(count_stmt)
            today_count = result.scalar() or 0

        # 기사가 없으면 수집 먼저 실행
        if today_count == 0:
            logger.info("No articles collected today, collecting first...")
            await _collect_news_batch_async()
            collected = True

        # LLM 처리 + 클러스터링
        async with async_session() as db:
            clusters = await cluster_articles(
                db, session_factory=async_session
            )
            cluster_count = len(clusters)
            await db.commit()
    except Exception as e:
        logger.warning(f"Processing/Clustering failed: {e}")
    finally:
        await redis_client.delete("news:clustering:status")
        await redis_client.aclose()
        await engine.dispose()

    logger.info(
        f"Processed and created {cluster_count} clusters"
        f"{' (collected first)' if collected else ''}"
    )
    return {"clusters": cluster_count, "collected_first": collected}


@celery_app.task(name="app.tasks.news_tasks.cleanup_old_news")
def cleanup_old_news(retention_days: int = 7):
    """오래된 뉴스 기사/클러스터 정리"""
    return asyncio.run(_cleanup_old_news_async(retention_days))


async def _cleanup_old_news_async(retention_days: int = 7):
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import delete
    from app.models.news import NewsArticleDB, NewsCluster

    async_session, engine = _get_async_session()
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    try:
        async with async_session() as db:
            # 오래된 클러스터 삭제
            cluster_stmt = delete(NewsCluster).where(NewsCluster.created_at < cutoff)
            cluster_result = await db.execute(cluster_stmt)
            clusters_deleted = cluster_result.rowcount

            # 오래된 기사 삭제
            article_stmt = delete(NewsArticleDB).where(NewsArticleDB.created_at < cutoff)
            article_result = await db.execute(article_stmt)
            articles_deleted = article_result.rowcount

            await db.commit()

        logger.info(
            f"News cleanup: {articles_deleted} articles, "
            f"{clusters_deleted} clusters deleted (older than {retention_days} days)"
        )
        return {"articles_deleted": articles_deleted, "clusters_deleted": clusters_deleted}
    except Exception as e:
        logger.error(f"News cleanup failed: {e}")
        return {"error": str(e)}
    finally:
        await engine.dispose()
