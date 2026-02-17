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

# 통합 배치 쿼리 (하루 2회, 1회 호출로 모든 카테고리 커버)
COMBINED_NEWS_QUERY = "한국 증시 미국 증시 금 시세 경제 금리 환율"

# 카테고리 자동 분류 키워드
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    NewsCategory.STOCK_KR: ["코스피", "코스닥", "한국 증시", "삼성전자", "SK하이닉스", "국내 증시", "한국 주식"],
    NewsCategory.STOCK_US: ["나스닥", "S&P", "다우", "미국 증시", "월가", "뉴욕증시", "애플", "엔비디아", "테슬라"],
    NewsCategory.GOLD: ["금값", "금 시세", "금투자", "골드", "금 가격", "귀금속"],
    NewsCategory.ECONOMY: ["금리", "환율", "경제", "물가", "인플레", "GDP", "한국은행", "연준", "Fed"],
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
