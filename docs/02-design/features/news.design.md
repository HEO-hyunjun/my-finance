# Design: News (보유 자산 뉴스)

> **Feature**: news
> **Created**: 2026-02-13
> **Plan Reference**: `docs/01-plan/features/news.plan.md`
> **PDCA Phase**: Design

---

## 1. Backend 상세 설계

### 1.1 Pydantic 스키마

**파일**: `backend/app/schemas/news.py`

```python
from __future__ import annotations

import hashlib

from pydantic import BaseModel


class NewsCategory:
    """뉴스 카테고리 상수"""
    ALL = "all"
    MY_ASSETS = "my_assets"
    STOCK_KR = "stock_kr"
    STOCK_US = "stock_us"
    GOLD = "gold"
    ECONOMY = "economy"

    VALID = {ALL, MY_ASSETS, STOCK_KR, STOCK_US, GOLD, ECONOMY}


# 카테고리 → SerpAPI 쿼리 매핑
CATEGORY_QUERY_MAP: dict[str, str] = {
    NewsCategory.ALL: "금융 OR 증시 OR 경제",
    NewsCategory.STOCK_KR: "한국 증시 OR 코스피 OR 코스닥",
    NewsCategory.STOCK_US: "미국 증시 OR 나스닥 OR S&P500",
    NewsCategory.GOLD: "금 시세 OR 금값 OR 금투자",
    NewsCategory.ECONOMY: "한국 경제 OR 금리 OR 환율",
}


class NewsSource(BaseModel):
    """뉴스 출처"""
    name: str
    icon: str | None = None


class NewsArticle(BaseModel):
    """뉴스 기사"""
    id: str  # title 해시 기반 고유 ID
    title: str
    link: str
    source: NewsSource
    snippet: str | None = None
    thumbnail: str | None = None
    published_at: str  # "2시간 전" 등 상대 시간
    category: str  # NewsCategory 값
    related_asset: str | None = None  # 관련 자산명 (my_assets용)

    @staticmethod
    def generate_id(title: str, link: str) -> str:
        return hashlib.md5(f"{title}:{link}".encode()).hexdigest()[:12]


class NewsListResponse(BaseModel):
    """뉴스 목록 응답"""
    articles: list[NewsArticle]
    page: int
    per_page: int
    has_next: bool


class MyAssetNewsResponse(BaseModel):
    """보유 자산 기반 뉴스 응답"""
    articles: list[NewsArticle]
    asset_queries: list[str]  # 검색에 사용된 키워드
```

---

### 1.2 서비스 레이어

**파일**: `backend/app/services/news_service.py`

```python
import asyncio
import hashlib
import json
import logging

import httpx
import redis.asyncio as redis

from app.core.config import settings
from app.schemas.news import (
    CATEGORY_QUERY_MAP,
    NewsArticle,
    NewsCategory,
    NewsListResponse,
    NewsSource,
    MyAssetNewsResponse,
)

logger = logging.getLogger(__name__)

NEWS_CACHE_TTL = 600  # 10분


class NewsService:
    """SerpAPI google_news 엔진 래퍼 + Redis 캐싱"""

    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client

    async def search_news(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        category: str = NewsCategory.ALL,
        related_asset: str | None = None,
    ) -> NewsListResponse:
        """
        SerpAPI google_news로 뉴스 검색.

        캐싱 전략:
        - Redis 키: news:{query_hash}:{page}
        - TTL: 10분
        """
        cache_key = self._cache_key(query, page)

        # 1. 캐시 확인
        cached = await self._get_cached(cache_key)
        if cached:
            return NewsListResponse(**cached)

        # 2. SerpAPI 호출
        raw_articles = await self._fetch_serpapi_news(query)

        # 3. 매핑 + 중복 제거
        articles = self._map_articles(raw_articles, category, related_asset)

        # 4. 페이지네이션 (SerpAPI는 서버 사이드 페이징 미지원이므로 클라이언트 사이드)
        start = (page - 1) * per_page
        end = start + per_page
        page_articles = articles[start:end]
        has_next = end < len(articles)

        result = NewsListResponse(
            articles=page_articles,
            page=page,
            per_page=per_page,
            has_next=has_next,
        )

        # 5. 캐시 저장
        await self._set_cached(cache_key, result.model_dump(), NEWS_CACHE_TTL)

        return result

    async def get_my_asset_news(
        self,
        asset_names: list[str],
        max_per_asset: int = 3,
    ) -> MyAssetNewsResponse:
        """
        보유 자산별 뉴스 병렬 검색.

        최대 5개 자산 동시 검색 (SerpAPI 크레딧 절약).
        """
        queries = asset_names[:5]  # 최대 5개 제한

        # 병렬 검색
        results = await asyncio.gather(
            *[self._fetch_serpapi_news(q) for q in queries],
            return_exceptions=True,
        )

        all_articles: list[NewsArticle] = []
        seen_ids: set[str] = set()

        for query, result in zip(queries, results):
            if isinstance(result, Exception):
                logger.warning(f"News search failed for '{query}': {result}")
                continue
            mapped = self._map_articles(result, NewsCategory.MY_ASSETS, query)
            for article in mapped[:max_per_asset]:
                if article.id not in seen_ids:
                    seen_ids.add(article.id)
                    all_articles.append(article)

        return MyAssetNewsResponse(
            articles=all_articles,
            asset_queries=queries,
        )

    async def _fetch_serpapi_news(self, query: str) -> list[dict]:
        """SerpAPI google_news 엔진 호출"""
        if not settings.SERPAPI_KEY:
            logger.warning("SERPAPI_KEY not set, returning mock news")
            return self._mock_news(query)

        params = {
            "engine": "google_news",
            "q": query,
            "gl": "kr",
            "hl": "ko",
            "api_key": settings.SERPAPI_KEY,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://serpapi.com/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        return data.get("news_results", [])

    def _map_articles(
        self,
        raw: list[dict],
        category: str,
        related_asset: str | None = None,
    ) -> list[NewsArticle]:
        """SerpAPI 응답 → NewsArticle 목록 매핑"""
        articles: list[NewsArticle] = []
        for item in raw:
            title = item.get("title", "")
            link = item.get("link", "")
            if not title or not link:
                continue

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
                    related_asset=related_asset,
                )
            )
        return articles

    def _mock_news(self, query: str) -> list[dict]:
        """SerpAPI 키 미설정 시 더미 뉴스 반환"""
        return [
            {
                "title": f"[Mock] {query} 관련 뉴스 {i}",
                "link": f"https://example.com/news/{i}",
                "source": {"name": "Mock News", "icon": None},
                "snippet": f"{query}에 대한 최신 뉴스입니다. (Mock 데이터)",
                "thumbnail": None,
                "date": f"{i}시간 전",
            }
            for i in range(1, 6)
        ]

    def _cache_key(self, query: str, page: int) -> str:
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"news:{query_hash}:{page}"

    async def _get_cached(self, key: str) -> dict | None:
        try:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            logger.warning(f"Redis cache read failed for {key}")
        return None

    async def _set_cached(self, key: str, data: dict, ttl: int) -> None:
        try:
            await self._redis.set(key, json.dumps(data, default=str), ex=ttl)
        except Exception:
            logger.warning(f"Redis cache write failed for {key}")
```

**핵심 설계 원칙:**
- **MarketService 패턴 재사용**: 동일한 Redis 캐싱 + httpx 클라이언트 구조
- **클래스 기반**: `MarketService`와 동일하게 `__init__(self, redis_client)` 패턴
- **병렬 검색**: `asyncio.gather()` + `return_exceptions=True`로 개별 실패 격리
- **중복 제거**: `article.id` (title+link 해시) 기반
- **클라이언트 사이드 페이징**: SerpAPI google_news는 서버 사이드 페이징 미지원

---

### 1.3 API 엔드포인트

**파일**: `backend/app/api/v1/endpoints/news.py`

```python
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.news import (
    CATEGORY_QUERY_MAP,
    NewsCategory,
    NewsListResponse,
    MyAssetNewsResponse,
)
from app.services.asset_service import get_assets
from app.services.news_service import NewsService

router = APIRouter(prefix="/news", tags=["News"])


@router.get("", response_model=NewsListResponse)
async def get_news(
    category: str = Query(default="all", description="뉴스 카테고리"),
    q: str = Query(default="", description="검색어 (빈 문자열이면 카테고리 기본 쿼리)"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """카테고리별 뉴스 조회"""
    redis = await get_redis()
    news_service = NewsService(redis)

    # my_assets 카테고리는 /news/my-assets 엔드포인트로 리다이렉트 안내
    if category == NewsCategory.MY_ASSETS:
        # my-assets 엔드포인트 로직 내부 호출
        assets = await get_assets(db, current_user.id)
        asset_names = [a.name for a in assets if a.symbol or a.name]
        if not asset_names:
            return NewsListResponse(articles=[], page=1, per_page=per_page, has_next=False)
        result = await news_service.get_my_asset_news(asset_names)
        # 페이지네이션 적용
        start = (page - 1) * per_page
        end = start + per_page
        return NewsListResponse(
            articles=result.articles[start:end],
            page=page,
            per_page=per_page,
            has_next=end < len(result.articles),
        )

    # 검색어 우선, 없으면 카테고리 기본 쿼리
    query = q if q else CATEGORY_QUERY_MAP.get(category, CATEGORY_QUERY_MAP[NewsCategory.ALL])

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

    # 사용자 보유 자산 조회
    assets = await get_assets(db, current_user.id)
    asset_names = [a.name for a in assets if a.symbol or a.name]

    if not asset_names:
        return MyAssetNewsResponse(articles=[], asset_queries=[])

    return await news_service.get_my_asset_news(asset_names)
```

**API 명세:**

```
GET /api/v1/news?category=all&q=&page=1&per_page=20
  - Auth: Required (JWT Bearer)
  - Params:
    - category: all | my_assets | stock_kr | stock_us | gold | economy
    - q: 검색어 (빈 문자열이면 카테고리 기본 쿼리)
    - page: 페이지 번호 (기본 1)
    - per_page: 페이지당 기사 수 (기본 20, 최대 50)
  - Response: NewsListResponse
  - 200: 뉴스 목록
  - 401: 인증 실패

GET /api/v1/news/my-assets
  - Auth: Required (JWT Bearer)
  - Response: MyAssetNewsResponse
  - 200: 보유 자산 기반 뉴스 + 검색 키워드
  - 401: 인증 실패
```

**라우터 등록 (`backend/app/main.py`):**

```python
from app.api.v1.endpoints import news

app.include_router(news.router, prefix="/api/v1")
```

---

## 2. Frontend 상세 설계

### 2.1 TypeScript 타입 정의

**파일**: `frontend/src/shared/types/index.ts` (기존 파일에 추가)

```typescript
// ========== News Types ==========

export interface NewsSource {
  name: string;
  icon?: string;
}

export interface NewsArticle {
  id: string;
  title: string;
  link: string;
  source: NewsSource;
  snippet?: string;
  thumbnail?: string;
  published_at: string;
  category: string;
  related_asset?: string;
}

export interface NewsListResponse {
  articles: NewsArticle[];
  page: number;
  per_page: number;
  has_next: boolean;
}

export interface MyAssetNewsResponse {
  articles: NewsArticle[];
  asset_queries: string[];
}

export type NewsCategory = 'all' | 'my_assets' | 'stock_kr' | 'stock_us' | 'gold' | 'economy';
```

---

### 2.2 TanStack Query Hooks

**파일**: `frontend/src/features/news/api/index.ts`

```typescript
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type { NewsListResponse, MyAssetNewsResponse, NewsCategory } from '@/shared/types';

export const newsKeys = {
  all: ['news'] as const,
  list: (category: NewsCategory, q: string) => [...newsKeys.all, 'list', category, q] as const,
  myAssets: () => [...newsKeys.all, 'my-assets'] as const,
};

export function useNewsFeed(category: NewsCategory, q: string = '') {
  return useInfiniteQuery({
    queryKey: newsKeys.list(category, q),
    queryFn: async ({ pageParam = 1 }): Promise<NewsListResponse> => {
      const params = new URLSearchParams({
        category,
        page: String(pageParam),
        per_page: '20',
      });
      if (q) params.set('q', q);
      const { data } = await apiClient.get(`/v1/news?${params.toString()}`);
      return data;
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.has_next ? lastPage.page + 1 : undefined,
    staleTime: 5 * 60 * 1000,
  });
}

export function useMyAssetNews() {
  return useQuery({
    queryKey: newsKeys.myAssets(),
    queryFn: async (): Promise<MyAssetNewsResponse> => {
      const { data } = await apiClient.get('/v1/news/my-assets');
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
```

---

### 2.3 UI 컴포넌트 설계

#### 2.3.1 컴포넌트 트리

```
pages/news/index.tsx
├── NewsCategoryTabs          # 카테고리 탭 (6개)
├── NewsSearchBar             # 검색 입력 (디바운스 300ms)
├── NewsCard (반복)            # 뉴스 카드
├── NewsCardSkeleton (반복)    # 로딩 스켈레톤
└── <div ref={sentinelRef} /> # 무한 스크롤 Intersection Observer
```

#### 2.3.2 컴포넌트 상세

**NewsCategoryTabs** — `features/news/ui/NewsCategoryTabs.tsx`

```
┌────────────────────────────────────────────────────────┐
│  전체 | 내 보유자산 | 국내주식 | 해외주식 | 금 | 경제   │
└────────────────────────────────────────────────────────┘
```

- Props: `activeCategory: NewsCategory`, `onChange: (cat: NewsCategory) => void`
- 카테고리 정의:

```typescript
const NEWS_CATEGORIES: { value: NewsCategory; label: string }[] = [
  { value: 'all', label: '전체' },
  { value: 'my_assets', label: '내 보유자산' },
  { value: 'stock_kr', label: '국내주식' },
  { value: 'stock_us', label: '해외주식' },
  { value: 'gold', label: '금' },
  { value: 'economy', label: '경제' },
];
```

- 활성 탭: `bg-blue-600 text-white`, 비활성: `bg-gray-100 text-gray-600`
- 수평 스크롤 (모바일 대응): `overflow-x-auto whitespace-nowrap`

**NewsSearchBar** — `features/news/ui/NewsSearchBar.tsx`

```
┌─────────────────────────────────────────┐
│  🔍 뉴스 검색...                        │
└─────────────────────────────────────────┘
```

- Props: `value: string`, `onChange: (q: string) => void`
- 디바운스: 300ms (입력 후 300ms 대기 후 검색 실행)
- `useEffect` + `setTimeout`으로 디바운스 구현 (추가 라이브러리 불필요)
- 검색어 입력 시 카테고리를 `all`로 전환 (또는 현재 카테고리 유지)
- 스타일: `rounded-lg border bg-white px-4 py-2.5 text-sm`

**NewsCard** — `features/news/ui/NewsCard.tsx`

```
Desktop:
┌──────────┬──────────────────────────────────┐
│          │ 삼성전자, AI 반도체 수주 확대      │
│ thumbnail│ 한국경제 · 2시간 전               │
│ (96x96)  │ 삼성전자가 AI 반도체 시장에서...   │
│          │ 🏷️ 삼성전자                       │
└──────────┴──────────────────────────────────┘

Mobile:
┌──────────────────────────────────────────┐
│ 삼성전자, AI 반도체 수주 확대              │
│ 한국경제 · 2시간 전                       │
│ 삼성전자가 AI 반도체 시장에서...           │
│ 🏷️ 삼성전자                              │
└──────────────────────────────────────────┘
```

- Props: `article: NewsArticle`
- 클릭: `<a href={article.link} target="_blank" rel="noopener noreferrer">`
- 썸네일: 있으면 `<img>` (96x96 rounded), 없으면 숨김
- 출처 아이콘: `source.icon`이 있으면 16x16 이미지, 없으면 숨김
- `related_asset` 태그: 있으면 하단에 작은 배지로 표시
- 호버: `hover:bg-gray-50` 배경 변경
- 카드 사이 구분: `divide-y` 또는 `border-b`

**NewsCardSkeleton** — `features/news/ui/NewsCardSkeleton.tsx`

```
┌──────────┬──────────────────────────────────┐
│ ░░░░░░░░ │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░    │
│ ░░░░░░░░ │ ░░░░░░░░ · ░░░░                  │
│ ░░░░░░░░ │ ░░░░░░░░░░░░░░░░░░░░░░           │
└──────────┴──────────────────────────────────┘
```

- Props 없음 (고정 레이아웃)
- `animate-pulse` + `bg-gray-200 rounded`
- 보통 3~5개 반복 표시

---

### 2.4 카테고리 상수 & 유틸

**파일**: `frontend/src/features/news/lib/constants.ts`

```typescript
import type { NewsCategory } from '@/shared/types';

export const NEWS_CATEGORIES: { value: NewsCategory; label: string }[] = [
  { value: 'all', label: '전체' },
  { value: 'my_assets', label: '내 보유자산' },
  { value: 'stock_kr', label: '국내주식' },
  { value: 'stock_us', label: '해외주식' },
  { value: 'gold', label: '금' },
  { value: 'economy', label: '경제' },
];
```

---

### 2.5 페이지 레이아웃

**파일**: `frontend/src/pages/news/index.tsx`

```typescript
import { useState, useRef, useCallback, useEffect } from 'react';
import { useNewsFeed } from '@/features/news/api';
import { NewsCategoryTabs } from '@/features/news/ui/NewsCategoryTabs';
import { NewsSearchBar } from '@/features/news/ui/NewsSearchBar';
import { NewsCard } from '@/features/news/ui/NewsCard';
import { NewsCardSkeleton } from '@/features/news/ui/NewsCardSkeleton';
import type { NewsCategory } from '@/shared/types';

export function Component() {
  const [category, setCategory] = useState<NewsCategory>('all');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // 디바운스
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useNewsFeed(category, debouncedSearch);

  // Intersection Observer로 무한 스크롤
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const articles = data?.pages.flatMap((p) => p.articles) ?? [];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">뉴스</h1>

      <NewsCategoryTabs activeCategory={category} onChange={setCategory} />
      <NewsSearchBar value={search} onChange={setSearch} />

      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <NewsCardSkeleton key={i} />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl border bg-white p-12 text-center">
          <p className="text-gray-500">뉴스를 불러올 수 없습니다.</p>
        </div>
      )}

      {!isLoading && !isError && articles.length === 0 && (
        <div className="rounded-xl border bg-white p-12 text-center">
          <p className="text-gray-500">뉴스가 없습니다.</p>
          {category === 'my_assets' && (
            <p className="mt-2 text-sm text-gray-400">
              자산을 등록하면 관련 뉴스를 볼 수 있어요.
            </p>
          )}
        </div>
      )}

      {articles.length > 0 && (
        <div className="divide-y rounded-xl border bg-white">
          {articles.map((article) => (
            <NewsCard key={article.id} article={article} />
          ))}
        </div>
      )}

      {/* 무한 스크롤 센티넬 */}
      <div ref={sentinelRef} className="h-4" />

      {isFetchingNextPage && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <NewsCardSkeleton key={`loading-${i}`} />
          ))}
        </div>
      )}
    </div>
  );
}
```

**반응형 레이아웃 정리:**

| 뷰포트 | NewsCard 레이아웃 | 설명 |
|---------|-------------------|------|
| Mobile (< 768px) | 세로 스택 (텍스트만, 썸네일 숨김) | 공간 효율 |
| Desktop (≥ 768px) | 수평 (좌: 썸네일 96x96, 우: 텍스트) | 정보 밀도 향상 |

---

## 3. 에러 처리 전략

### 3.1 Backend

| 상황 | 처리 |
|------|------|
| SerpAPI KEY 미설정 | mock 뉴스 데이터 반환, 로그 경고 |
| SerpAPI 호출 실패 (타임아웃 등) | 빈 결과 반환, 로그 경고 |
| 보유 자산 없음 | 빈 articles + 빈 asset_queries 반환 |
| Redis 연결 실패 | 캐시 없이 직접 SerpAPI 호출 (graceful degradation) |
| 개별 자산 뉴스 검색 실패 | 해당 자산만 건너뛰고 나머지 반환 (`return_exceptions=True`) |

### 3.2 Frontend

| 상황 | 처리 |
|------|------|
| API 로딩 중 | NewsCardSkeleton 5개 표시 |
| API 에러 | "뉴스를 불러올 수 없습니다." 메시지 |
| 데이터 비어있음 | Empty State (카테고리별 안내 메시지) |
| 추가 로딩 중 (무한 스크롤) | 하단에 NewsCardSkeleton 3개 추가 |
| 썸네일 로딩 실패 | `onError`에서 이미지 숨김 |

---

## 4. 구현 순서 (Implementation Order)

```
Step 1: Backend — 스키마
  └── backend/app/schemas/news.py (Pydantic 스키마 + 카테고리 상수)

Step 2: Backend — 서비스
  └── backend/app/services/news_service.py (SerpAPI 래퍼 + Redis 캐싱)

Step 3: Backend — 엔드포인트 & 등록
  ├── backend/app/api/v1/endpoints/news.py (API 라우터)
  └── backend/app/main.py (라우터 등록 추가)

Step 4: Frontend — 타입 & API Hook
  ├── frontend/src/shared/types/index.ts (News 타입 추가)
  └── frontend/src/features/news/api/index.ts (TanStack Query hooks)

Step 5: Frontend — 상수 & 유틸
  └── frontend/src/features/news/lib/constants.ts (카테고리 정의)

Step 6: Frontend — UI 컴포넌트
  ├── features/news/ui/NewsCategoryTabs.tsx
  ├── features/news/ui/NewsSearchBar.tsx
  ├── features/news/ui/NewsCard.tsx
  └── features/news/ui/NewsCardSkeleton.tsx

Step 7: Frontend — 페이지 조합
  └── frontend/src/pages/news/index.tsx (무한 스크롤 + 카테고리 + 검색)
```

---

## 5. 검증 체크리스트

Design → Do 전환 시 다음 항목을 구현 검증 기준으로 사용:

- [ ] **BE-1**: `NewsArticle`, `NewsListResponse`, `MyAssetNewsResponse` Pydantic 스키마 정의
- [ ] **BE-2**: `NewsCategory` 상수 + `CATEGORY_QUERY_MAP` 정의
- [ ] **BE-3**: `NewsService.search_news()` — SerpAPI google_news 호출 + Redis 10분 캐싱
- [ ] **BE-4**: `NewsService.get_my_asset_news()` — asyncio.gather 병렬 검색 (최대 5개)
- [ ] **BE-5**: `NewsService._mock_news()` — SerpAPI KEY 미설정 시 mock 데이터
- [ ] **BE-6**: `GET /api/v1/news` 엔드포인트 — category, q, page, per_page 파라미터
- [ ] **BE-7**: `GET /api/v1/news/my-assets` 엔드포인트 — 보유 자산 기반 뉴스
- [ ] **BE-8**: `main.py`에 news 라우터 등록
- [ ] **FE-1**: `NewsArticle`, `NewsListResponse`, `MyAssetNewsResponse`, `NewsCategory` 타입 정의
- [ ] **FE-2**: `useNewsFeed` — useInfiniteQuery hook (카테고리 + 검색어 + 페이지네이션)
- [ ] **FE-3**: `useMyAssetNews` — useQuery hook
- [ ] **FE-4**: `NewsCategoryTabs` — 6개 카테고리 탭 (활성/비활성 스타일)
- [ ] **FE-5**: `NewsSearchBar` — 디바운스 300ms 검색 입력
- [ ] **FE-6**: `NewsCard` — 썸네일 + 제목 + 출처 + 시간 + 스니펫 + 외부 링크
- [ ] **FE-7**: `NewsCardSkeleton` — animate-pulse 스켈레톤
- [ ] **FE-8**: 무한 스크롤 — IntersectionObserver + fetchNextPage
- [ ] **FE-9**: Empty State — 카테고리별 안내 (my_assets: 자산 등록 유도)
- [ ] **FE-10**: 뉴스 카테고리 상수 정의 (`constants.ts`)
- [ ] **FE-11**: 반응형 레이아웃 (모바일: 텍스트만 / 데스크톱: 썸네일+텍스트)
- [ ] **FE-12**: 뉴스 페이지 — 카테고리 탭 + 검색바 + 뉴스 목록 + 무한 스크롤 통합

---

## 6. 다음 단계

Design 승인 후 → `/pdca do news` 로 구현 시작
