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


# 카테고리 → 검색 쿼리 매핑 (topic="general"에 최적화된 한국어 쿼리)
CATEGORY_QUERY_MAP: dict[str, str] = {
    NewsCategory.ALL: "코스피 나스닥 금값 환율 최신 뉴스",
    NewsCategory.STOCK_KR: "코스피 코스닥 한국 증시 오늘 뉴스",
    NewsCategory.STOCK_US: "나스닥 미국증시 뉴스 최신",
    NewsCategory.GOLD: "금값 금시세 투자 뉴스",
    NewsCategory.ECONOMY: "금리 환율 경제 뉴스 최신",
}

# 통합 배치 기본 쿼리 (topic="general"에 최적화)
BASE_NEWS_QUERY = "코스피 나스닥 금값 환율 최신 뉴스"

# 하위 호환용 (기존 참조 유지)
COMBINED_NEWS_QUERY = BASE_NEWS_QUERY

# 뉴스 검색에 부적합한 일반 자산명
_SKIP_KEYWORDS = {"원화", "현금", "KRW", "USD", "원화 자금", "달러 자금", "비상금", "파킹통장", "비상예비자금"}


def filter_asset_names(asset_names: list[str], max_assets: int = 10) -> list[str]:
    """뉴스 검색에 적합한 자산명만 필터링"""
    return [
        name for name in asset_names
        if name not in _SKIP_KEYWORDS and len(name) >= 2
    ][:max_assets]


def build_batch_query(asset_names: list[str] | None = None, max_assets: int = 10) -> str:
    """보유 자산 키워드를 포함한 배치 쿼리 생성.

    Args:
        asset_names: 전체 유저의 보유 자산명 (중복 제거된 리스트)
        max_assets: 쿼리에 포함할 최대 자산 수 (쿼리 길이 제한)
    """
    filtered = filter_asset_names(asset_names, max_assets) if asset_names else []

    if not filtered:
        return BASE_NEWS_QUERY

    asset_query = " OR ".join(filtered)
    return f"{asset_query} 주가 뉴스"


def build_category_queries(asset_names: list[str] | None = None) -> list[str]:
    """카테고리별 + 자산별 개별 쿼리 목록 생성 (배치 수집용)"""
    queries = list(CATEGORY_QUERY_MAP.values())
    if asset_names:
        filtered = filter_asset_names(asset_names)
        for name in filtered[:5]:
            queries.append(f"{name} 주가 뉴스")
    return queries

# 카테고리 자동 분류 키워드 (시장/지수 키워드만, 개별 종목은 제외)
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    NewsCategory.STOCK_KR: ["코스피", "코스닥", "한국 증시", "국내 증시", "한국 주식", "유가증권"],
    NewsCategory.STOCK_US: ["나스닥", "S&P", "다우", "미국 증시", "월가", "뉴욕증시", "러셀"],
    NewsCategory.GOLD: ["금값", "금 시세", "금투자", "골드", "금 가격", "귀금속", "은값"],
    NewsCategory.ECONOMY: ["금리", "환율", "경제", "물가", "인플레", "GDP", "한국은행", "연준", "Fed", "기준금리"],
}


def classify_article_category(title: str, snippet: str | None = None) -> str:
    """기사 제목/snippet으로 카테고리 자동 분류"""
    text = f"{title} {snippet or ''}".lower()
    scores: dict[str, int] = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw.lower() in text)
    if not scores or max(scores.values()) == 0:
        return NewsCategory.ECONOMY  # 기본값
    return max(scores, key=lambda k: scores[k])


class NewsSource(BaseModel):
    """뉴스 출처"""

    name: str
    icon: str | None = None


class NewsArticle(BaseModel):
    """뉴스 기사"""

    id: str
    title: str
    link: str
    source: NewsSource
    snippet: str | None = None
    raw_content: str | None = None
    thumbnail: str | None = None
    published_at: str
    category: str
    related_asset: str | None = None

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
    asset_queries: list[str]
