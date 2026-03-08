from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_news_service
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
    news_service: NewsService = Depends(get_news_service),
):
    """카테고리별 뉴스 조회"""

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
    is_custom_search = bool(q)
    query = q if q else CATEGORY_QUERY_MAP.get(
        category, CATEGORY_QUERY_MAP[NewsCategory.ALL]
    )

    return await news_service.search_news(
        query=query,
        page=page,
        per_page=per_page,
        category=category,
        is_custom_search=is_custom_search,
    )


@router.get("/my-assets", response_model=MyAssetNewsResponse)
async def get_my_asset_news(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    news_service: NewsService = Depends(get_news_service),
):
    """보유 자산 기반 뉴스 조회"""

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
    """뉴스 기사 상세 조회 (본문 + LLM 분석 결과).

    raw_content가 없으면 Tavily Extract로 온디맨드 추출 후 DB에 저장.
    """
    stmt = select(NewsArticleDB).where(NewsArticleDB.external_id == external_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # raw_content 없으면 온디맨드 추출
    if not article.raw_content and article.link:
        raw_content = await _extract_article_content(article.link)
        if raw_content:
            article.raw_content = raw_content
            await db.commit()

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


async def _extract_article_content(url: str) -> str | None:
    """Tavily Extract API로 기사 본문 추출 후 정제."""
    import logging
    from app.core.config import settings

    logger = logging.getLogger(__name__)

    if not settings.TAVILY_API_KEY:
        return None

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
        response = await client.extract(urls=[url])
        results = response.get("results", [])
        if results:
            raw = results[0].get("raw_content", "")
            return _clean_article_content(raw) if raw else None
    except Exception as e:
        logger.warning(f"Article extract failed for {url}: {e}")

    return None


import re

# 제거 대상 라인 패턴
_SKIP_LINE = re.compile(
    r"^\s*\*\s*\[.*?\]\(.*?\)\s*,?\s*$"  # 리스트 링크 (메뉴, 종목, 공유)
    r"|^:?\s{2,}\*\s*\["  # 들여쓴 네비게이션
    r"|^#{1,3}\s*(?:관련종목|추천기사|인기기사|많이 본|관련기사|댓글|주가 정보)"
    r"|^!\[.*?\]\(.*?\)\s*$"  # 이미지만 있는 줄
    r"|^(?:입력|수정|발행)\s*\d{4}\."  # 날짜 메타
    r"|저작권자\s*ⓒ"
    r"|무단전재.*재배포.*금지"
    r"|^\d[\d,.]+\s*$"  # 숫자만 있는 줄 (주가 위젯)
    r"|^[-+]?\d+\.\d+%\s*$"  # 퍼센트만 있는 줄
)

_FOOTER_MARKERS = [
    "저작권자", "무단전재", "▶ 관련기사", "▶ 추천기사", "Copyrights", "ⓒ",
    "많이 본 뉴스", "많이 본 기사", "인기 기사", "추천 기사",
    "관련 기사", "함께 본 기사",
]


def _clean_article_content(raw: str) -> str:
    """추출된 마크다운에서 네비게이션/보일러플레이트를 제거하고 본문만 추출."""
    lines = raw.split("\n")

    # 1단계: 본문 시작점 찾기 - 첫 번째 긴 텍스트 문단 (50자+ 순수 텍스트)
    body_start = 0
    for i, line in enumerate(lines):
        plain = re.sub(r"\[.*?\]\(.*?\)", "", line).strip()
        plain = re.sub(r"[#*!\[\]()>|]", "", plain).strip()
        if len(plain) >= 50:
            # 제목이 바로 앞에 있으면 제목부터 시작
            if i > 0 and lines[i - 1].startswith("#"):
                body_start = i - 1
            else:
                body_start = i
            break

    # 2단계: 푸터 시작점 찾기
    body_end = len(lines)
    for i in range(len(lines) - 1, body_start, -1):
        if any(marker in lines[i] for marker in _FOOTER_MARKERS):
            body_end = i
            break

    # 3단계: 본문 영역에서 불필요한 라인 제거
    cleaned = []
    consecutive_headers = 0
    for line in lines[body_start:body_end]:
        if _SKIP_LINE.search(line):
            continue
        # 마크다운 링크만 있는 줄 제거
        stripped = re.sub(r"\[.*?\]\(.*?\)", "", line).strip()
        if not stripped and "[" in line and "](" in line:
            continue
        # 빈 줄은 헤더 카운트 유지한 채 추가
        if not line.strip():
            cleaned.append(line)
            continue
        # 연속된 ### 헤더 3개 이상이면 추천기사 목록으로 판단 → 중단
        if line.startswith("### ") or line.startswith("#### "):
            consecutive_headers += 1
            if consecutive_headers >= 3:
                while cleaned and (cleaned[-1].startswith("### ") or cleaned[-1].startswith("#### ") or not cleaned[-1].strip()):
                    cleaned.pop()
                break
        else:
            consecutive_headers = 0
        cleaned.append(line)

    result = "\n".join(cleaned).strip()

    # 너무 짧으면 정제 실패 → 원본 반환
    if len(result) < 100:
        return raw

    return result


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
