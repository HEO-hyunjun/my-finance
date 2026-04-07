import json
import logging
from datetime import datetime, timezone, timedelta

from litellm import acompletion
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.tz import now as tz_now, to_utc
from app.models.news import NewsArticleDB, NewsCluster
from app.schemas.news import NewsArticle

logger = logging.getLogger(__name__)


def _today_start_utc() -> datetime:
    """뉴스 수집 기준 '오늘' 시작 시각을 UTC로 변환.

    배치 수집 시각(NEWS_BATCH_HOUR:NEWS_BATCH_MINUTE) 직전을 하루의 경계로 사용한다.
    경계 이전이면 전날 경계, 이후이면 오늘 경계가 기준.
    """
    batch_hour = settings.NEWS_BATCH_HOUR
    batch_minute = settings.NEWS_BATCH_MINUTE

    now_local = tz_now()
    if now_local.hour < batch_hour or (
        now_local.hour == batch_hour and now_local.minute < batch_minute
    ):
        base = now_local - timedelta(days=1)
    else:
        base = now_local
    today_start = base.replace(hour=batch_hour, minute=batch_minute, second=0, microsecond=0)
    return to_utc(today_start)


async def save_articles_to_db(
    db: AsyncSession,
    articles: list[NewsArticle],
) -> int:
    """뉴스 기사를 DB에 저장 (중복 스킵)"""
    saved = 0

    # 단일 IN 쿼리로 이미 존재하는 external_id를 한번에 조회
    all_ids = [a.id for a in articles]
    existing_stmt = select(NewsArticleDB.external_id).where(
        NewsArticleDB.external_id.in_(all_ids)
    )
    existing_ids = set((await db.execute(existing_stmt)).scalars().all())

    for article in articles:
        if article.id in existing_ids:
            continue

        db_article = NewsArticleDB(
            external_id=article.id,
            title=article.title,
            link=article.link,
            source_name=article.source.name,
            source_icon=article.source.icon,
            snippet=article.snippet,
            raw_content=article.raw_content,
            thumbnail=article.thumbnail,
            published_at=article.published_at,
            category=article.category,
            related_asset=article.related_asset,
        )
        db.add(db_article)
        saved += 1

    await db.commit()
    return saved


async def process_article_with_llm(
    db: AsyncSession,
    article_id: str,
) -> dict | None:
    """개별 기사에 대해 LLM 요약 + 감성분석 수행"""
    stmt = select(NewsArticleDB).where(NewsArticleDB.external_id == article_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article or article.processed_at:
        return None

    content_text = article.raw_content or article.snippet or "(내용 없음)"
    # LLM 토큰 절약을 위해 본문은 2000자까지만
    if len(content_text) > 2000:
        content_text = content_text[:2000] + "..."

    prompt = f"""다음 뉴스 기사를 분석해주세요.

제목: {article.title}
내용: {content_text}
출처: {article.source_name}

아래 JSON 형식으로만 응답하세요:
{{
  "summary": "2-3문장 한국어 요약",
  "sentiment": "positive 또는 negative 또는 neutral",
  "sentiment_score": -1.0에서 1.0 사이의 숫자 (부정=-1, 긍정=1),
  "keywords": "쉼표로 구분된 키워드 5-7개 (넓은 주제 키워드 2-3개 + 구체적 키워드 3-4개. 예: 반도체,미국증시,엔비디아,AI,실적)"
}}"""

    try:
        response = await acompletion(
            model=settings.news_llm_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.NEWS_LLM_MAX_TOKENS,
            temperature=settings.NEWS_LLM_TEMPERATURE,
            drop_params=True,
        )

        content = response.choices[0].message.content.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)

        article.summary = data.get("summary")
        article.sentiment = data.get("sentiment", "neutral")
        article.sentiment_score = float(data.get("sentiment_score", 0))
        article.keywords = data.get("keywords")
        article.processed_at = datetime.now(timezone.utc)

        await db.commit()

        return {
            "id": article_id,
            "summary": article.summary,
            "sentiment": article.sentiment,
            "sentiment_score": article.sentiment_score,
            "keywords": article.keywords,
        }
    except Exception as e:
        logger.error(f"LLM processing failed for article {article_id}: {e}")
        return None


async def process_unprocessed_articles(
    db: AsyncSession,
    max_articles: int = 100,
    concurrency: int = 20,
    max_retries: int = 2,
    session_factory=None,
) -> int:
    """당일 미처리 기사를 병렬 LLM 분석 (실패 시 재시도)"""
    import asyncio

    if session_factory is None:
        from app.core.database import async_session as session_factory

    today_utc = _today_start_utc()

    stmt = (
        select(NewsArticleDB.external_id)
        .where(
            NewsArticleDB.processed_at.is_(None),
            NewsArticleDB.created_at >= today_utc,
        )
        .order_by(NewsArticleDB.created_at.desc())
        .limit(max_articles)
    )
    result = await db.execute(stmt)
    article_ids = [row[0] for row in result.all()]

    if not article_ids:
        return 0

    semaphore = asyncio.Semaphore(concurrency)

    async def _process_one(article_id: str) -> bool:
        async with semaphore:
            for attempt in range(1, max_retries + 1):
                async with session_factory() as local_db:
                    try:
                        res = await process_article_with_llm(local_db, article_id)
                        return res is not None
                    except Exception as e:
                        if attempt < max_retries:
                            logger.info(f"Retry {attempt}/{max_retries} for {article_id}")
                            await asyncio.sleep(1 * attempt)
                        else:
                            logger.warning(f"LLM failed after {max_retries} retries for {article_id}: {e}")
            return False

    results = await asyncio.gather(*[_process_one(aid) for aid in article_ids])
    return sum(1 for r in results if r)


async def get_processed_articles(
    db: AsyncSession,
    category: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """DB에서 당일 처리된 뉴스 기사 조회"""
    today_utc = _today_start_utc()

    stmt = (
        select(NewsArticleDB)
        .where(
            NewsArticleDB.processed_at.isnot(None),
            NewsArticleDB.created_at >= today_utc,
        )
        .order_by(NewsArticleDB.created_at.desc())
        .limit(limit)
    )

    if category and category != "all":
        stmt = stmt.where(NewsArticleDB.category == category)

    result = await db.execute(stmt)
    articles = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "external_id": a.external_id,
            "title": a.title,
            "link": a.link,
            "source_name": a.source_name,
            "snippet": a.snippet,
            "thumbnail": a.thumbnail,
            "published_at": a.published_at,
            "category": a.category,
            "summary": a.summary,
            "sentiment": a.sentiment,
            "sentiment_score": a.sentiment_score,
            "keywords": a.keywords,
        }
        for a in articles
    ]


# ---------------------------------------------------------------------------
# News Clustering (이슈 그룹핑)
# ---------------------------------------------------------------------------


async def cluster_articles(
    db: AsyncSession,
    category: str | None = None,
    max_articles: int = 100,
    session_factory=None,
) -> list[dict]:
    """당일 기사를 LLM 처리 후 키워드 유사도 기반으로 클러스터링.

    미처리 기사가 있으면 먼저 LLM 처리를 수행한 후 클러스터링합니다.
    """
    today_utc = _today_start_utc()

    # 0. 미처리 기사가 있으면 LLM 처리 먼저 수행
    unprocessed_stmt = (
        select(NewsArticleDB.external_id)
        .where(
            NewsArticleDB.processed_at.is_(None),
            NewsArticleDB.created_at >= today_utc,
        )
        .limit(max_articles)
    )
    unprocessed_result = await db.execute(unprocessed_stmt)
    unprocessed_ids = unprocessed_result.scalars().all()

    if unprocessed_ids:
        if session_factory is None:
            from app.core.database import async_session as session_factory
        processed = await process_unprocessed_articles(
            db, max_articles=max_articles, session_factory=session_factory
        )
        logger.info(f"Auto-processed {processed} articles before clustering")

    # 1. 당일 처리된 기사 조회
    stmt = (
        select(NewsArticleDB)
        .where(
            NewsArticleDB.processed_at.isnot(None),
            NewsArticleDB.keywords.isnot(None),
            NewsArticleDB.created_at >= today_utc,
        )
        .order_by(NewsArticleDB.created_at.desc())
        .limit(max_articles)
    )
    if category and category != "all":
        stmt = stmt.where(NewsArticleDB.category == category)

    result = await db.execute(stmt)
    articles = result.scalars().all()

    if len(articles) < 2:
        return []

    # 2. 기존 당일 클러스터 삭제 후 새로 생성
    delete_stmt = delete(NewsCluster).where(
        NewsCluster.created_at >= today_utc,
    )
    if category and category != "all":
        delete_stmt = delete_stmt.where(NewsCluster.category == category)
    await db.execute(delete_stmt)

    # 3. 키워드 기반 유사도로 그룹핑 (Jaccard similarity)
    groups = _group_by_keyword_similarity(articles, threshold=0.15)

    # 4. 각 그룹에 대해 LLM 요약
    clusters: list[dict] = []
    for group in groups:
        if len(group) < 2:
            continue
        cluster = await _summarize_cluster(db, group)
        if cluster:
            clusters.append(cluster)

    # 중요도순 정렬
    clusters.sort(key=lambda c: c["importance_score"], reverse=True)
    return clusters


def _group_by_keyword_similarity(
    articles: list[NewsArticleDB],
    threshold: float = 0.2,
) -> list[list[NewsArticleDB]]:
    """키워드 Jaccard 유사도 기반 그룹핑 (Union-Find)"""
    from collections import defaultdict

    n = len(articles)
    keyword_sets: list[set[str]] = []
    for a in articles:
        kws = set(
            k.strip().lower() for k in (a.keywords or "").split(",") if k.strip()
        )
        keyword_sets.append(kws)

    # Union-Find
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        for j in range(i + 1, n):
            if not keyword_sets[i] or not keyword_sets[j]:
                continue
            # Jaccard similarity
            intersection = len(keyword_sets[i] & keyword_sets[j])
            union_size = len(keyword_sets[i] | keyword_sets[j])
            if union_size > 0 and intersection / union_size >= threshold:
                union(i, j)

    # Group by root
    groups_map: dict[int, list[NewsArticleDB]] = defaultdict(list)
    for i in range(n):
        groups_map[find(i)].append(articles[i])

    return list(groups_map.values())


async def _summarize_cluster(
    db: AsyncSession,
    articles: list[NewsArticleDB],
) -> dict | None:
    """클러스터의 기사들을 LLM으로 요약"""
    titles = "\n".join(f"- {a.title}" for a in articles[:10])
    snippets = "\n".join(
        f"- {a.snippet[:100]}" for a in articles[:5] if a.snippet
    )

    prompt = f"""다음 관련 뉴스 기사들을 하나의 이슈로 요약하세요.

기사 제목들:
{titles}

주요 내용:
{snippets}

아래 JSON 형식으로만 응답하세요:
{{
  "title": "이슈 제목 (20자 이내)",
  "summary": "3-4문장 요약",
  "importance": 0.0에서 1.0 사이 (시장 영향도)
}}"""

    try:
        response = await acompletion(
            model=settings.news_llm_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.NEWS_LLM_MAX_TOKENS,
            temperature=settings.NEWS_LLM_TEMPERATURE,
            drop_params=True,
        )

        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)

        # 평균 감성 점수
        scores = [
            a.sentiment_score for a in articles if a.sentiment_score is not None
        ]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # 키워드 합산
        all_keywords: dict[str, int] = {}
        for a in articles:
            for kw in (a.keywords or "").split(","):
                kw = kw.strip().lower()
                if kw:
                    all_keywords[kw] = all_keywords.get(kw, 0) + 1
        top_keywords = sorted(
            all_keywords, key=lambda k: all_keywords[k], reverse=True
        )[:10]

        # DB에 클러스터 저장
        cluster = NewsCluster(
            title=data.get("title", "이슈"),
            summary=data.get("summary", ""),
            category=articles[0].category,
            sentiment=(
                "positive"
                if avg_score > 0.2
                else ("negative" if avg_score < -0.2 else "neutral")
            ),
            avg_sentiment_score=round(avg_score, 3),
            article_count=len(articles),
            article_ids=",".join(a.external_id for a in articles),
            keywords=",".join(top_keywords),
            importance_score=float(data.get("importance", 0.5)),
        )
        db.add(cluster)
        await db.flush()

        return {
            "id": str(cluster.id),
            "title": cluster.title,
            "summary": cluster.summary,
            "category": cluster.category,
            "sentiment": cluster.sentiment,
            "avg_sentiment_score": cluster.avg_sentiment_score,
            "article_count": cluster.article_count,
            "keywords": top_keywords,
            "importance_score": cluster.importance_score,
        }
    except Exception as e:
        logger.error(f"Cluster summarization failed: {e}")
        return None


async def search_articles_by_keywords(
    db: AsyncSession,
    keywords: list[str],
    hours: int = 24,
    limit: int = 20,
) -> list[dict]:
    """키워드 목록으로 DB에서 관련 기사 검색 (LIKE 매칭)"""
    from sqlalchemy import or_

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # 각 키워드에 대해 제목 또는 snippet에 포함된 기사 검색
    keyword_filters = []
    for kw in keywords:
        keyword_filters.append(NewsArticleDB.title.ilike(f"%{kw}%"))
        keyword_filters.append(NewsArticleDB.snippet.ilike(f"%{kw}%"))

    stmt = (
        select(NewsArticleDB)
        .where(
            NewsArticleDB.created_at >= cutoff,
            or_(*keyword_filters),
        )
        .order_by(NewsArticleDB.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    articles = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "external_id": a.external_id,
            "title": a.title,
            "link": a.link,
            "source_name": a.source_name,
            "snippet": a.snippet,
            "thumbnail": a.thumbnail,
            "published_at": a.published_at,
            "category": a.category,
            "summary": a.summary,
            "sentiment": a.sentiment,
            "keywords": a.keywords,
        }
        for a in articles
    ]


async def get_clusters(
    db: AsyncSession,
    category: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """당일 클러스터 조회"""
    today_utc = _today_start_utc()

    stmt = (
        select(NewsCluster)
        .where(NewsCluster.created_at >= today_utc)
        .order_by(NewsCluster.importance_score.desc())
        .limit(limit)
    )
    if category and category != "all":
        stmt = stmt.where(NewsCluster.category == category)

    result = await db.execute(stmt)
    clusters = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "title": c.title,
            "summary": c.summary,
            "category": c.category,
            "sentiment": c.sentiment,
            "avg_sentiment_score": c.avg_sentiment_score,
            "article_count": c.article_count,
            "keywords": [k.strip() for k in c.keywords.split(",") if k.strip()],
            "importance_score": c.importance_score,
            "created_at": c.created_at.isoformat(),
        }
        for c in clusters
    ]
