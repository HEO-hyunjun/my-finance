from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.news import NewsArticleDB
from app.models.user import User
from app.schemas.news import (
    CATEGORY_QUERY_MAP,
    MyAssetNewsResponse,
    NewsCategory,
    NewsListResponse,
)
from app.services.asset_service import get_assets
from app.services.news_service import NewsService

router = APIRouter(prefix="/news", tags=["News"])


@router.get("", response_model=NewsListResponse)
async def get_news(
    category: str = Query(default="all", description="뉴스 카테고리"),
    q: str = Query(default="", description="검색어"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """카테고리별 뉴스 조회"""
    redis = await get_redis()
    news_service = NewsService(redis)

    # my_assets 카테고리: 보유 자산 기반 뉴스
    if category == NewsCategory.MY_ASSETS:
        assets = await get_assets(db, current_user.id)
        asset_names = [a.name for a in assets if a.symbol or a.name]
        if not asset_names:
            return NewsListResponse(
                articles=[], page=1, per_page=per_page, has_next=False
            )
        result = await news_service.get_my_asset_news(asset_names)
        start = (page - 1) * per_page
        end = start + per_page
        return NewsListResponse(
            articles=result.articles[start:end],
            page=page,
            per_page=per_page,
            has_next=end < len(result.articles),
        )

    # 검색어 우선, 없으면 카테고리 기본 쿼리
    query = q if q else CATEGORY_QUERY_MAP.get(
        category, CATEGORY_QUERY_MAP[NewsCategory.ALL]
    )

    return await news_service.search_news(
        query=query,
        page=page,
        per_page=per_page,
        category=category,
    )


@router.get("/my-assets", response_model=MyAssetNewsResponse)
async def get_my_asset_news(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """보유 자산 기반 뉴스 조회"""
    redis = await get_redis()
    news_service = NewsService(redis)

    assets = await get_assets(db, current_user.id)
    asset_names = [a.name for a in assets if a.symbol or a.name]

    if not asset_names:
        return MyAssetNewsResponse(articles=[], asset_queries=[])

    return await news_service.get_my_asset_news(asset_names)


@router.get("/processed")
async def get_processed_news(
    category: str = Query(default="all"),
    limit: int = Query(default=20, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """LLM으로 처리된 뉴스 기사 조회 (요약, 감성분석 포함)"""
    from app.services.news_llm_service import get_processed_articles

    articles = await get_processed_articles(db, category, limit)
    return {"articles": articles}


@router.get("/articles/{external_id}")
async def get_article_detail(
    external_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """뉴스 기사 상세 조회 (본문 + LLM 분석 결과)"""
    stmt = select(NewsArticleDB).where(NewsArticleDB.external_id == external_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return {
        "id": str(article.id),
        "external_id": article.external_id,
        "title": article.title,
        "link": article.link,
        "source_name": article.source_name,
        "source_icon": article.source_icon,
        "snippet": article.snippet,
        "raw_content": article.raw_content,
        "thumbnail": article.thumbnail,
        "published_at": article.published_at,
        "category": article.category,
        "related_asset": article.related_asset,
        "summary": article.summary,
        "sentiment": article.sentiment,
        "sentiment_score": article.sentiment_score,
        "keywords": article.keywords,
        "processed_at": article.processed_at.isoformat() if article.processed_at else None,
    }


@router.post("/clusters")
async def create_clusters(
    category: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    """당일 미처리 기사 LLM 분석 + 클러스터링 실행 (비동기)"""
    from app.tasks.news_tasks import process_and_cluster_news
    from app.core.redis import get_redis

    redis = await get_redis()
    # 이미 처리 중이면 중복 실행 방지
    if await redis.get("news:clustering:status") == "processing":
        return {"status": "already_processing"}

    await redis.set("news:clustering:status", "processing", ex=300)  # 5분 TTL
    process_and_cluster_news.delay()
    return {"status": "processing"}


@router.get("/clusters")
async def list_clusters(
    category: str | None = Query(default=None),
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """저장된 클러스터 조회 (처리 상태 포함)"""
    from app.services.news_llm_service import get_clusters
    from app.core.redis import get_redis

    redis = await get_redis()
    is_processing = await redis.get("news:clustering:status") == "processing"

    clusters = await get_clusters(db, category, limit)
    return {"clusters": clusters, "is_processing": is_processing}
