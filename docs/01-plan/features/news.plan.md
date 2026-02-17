# Plan: News (보유 자산 뉴스)

> **Feature**: news
> **Created**: 2026-02-13
> **PRD Reference**: 섹션 2.4 (뉴스/시장 정보)
> **PDCA Phase**: Plan

---

## 1. 기능 개요

사용자의 보유 자산(종목)과 관련된 금융 뉴스를 자동으로 검색하여 피드 형태로 제공한다. SerpAPI `google_news` 엔진을 활용하여 실시간 뉴스를 가져오고, 자산 유형별 카테고리 필터링과 무한 스크롤을 지원한다.

### 1.1 핵심 목표

- 보유 자산(종목명/심볼) 기반 자동 뉴스 검색
- 금융 일반 뉴스 (경제, 증시, 환율, 금리 등)
- 자산 유형별 카테고리 필터 (국내주식, 미국주식, 금, 예금/적금 등)
- 뉴스 카드 UI (썸네일, 제목, 출처, 시간, 스니펫)
- 무한 스크롤 (커서 기반 페이지네이션)
- Redis 캐싱으로 SerpAPI 크레딧 절약

### 1.2 기존 구현 피처 연계

| 연계 피처 | 활용 데이터 | 용도 |
|-----------|-------------|------|
| asset-management | 보유 자산 목록 (symbol, name, asset_type) | 뉴스 검색 키워드 자동 생성 |
| market_service | SerpAPI 연동 패턴, Redis 캐싱 | 코드 패턴 재사용 |
| Auth (JWT) | 사용자 인증 | 사용자별 보유 자산 기반 뉴스 |

---

## 2. 구현 범위

### 2.1 In Scope (이번 Plan)

#### 뉴스 서비스 (Backend)

- [ ] **`GET /api/v1/news`** — 뉴스 목록 조회 (페이지네이션)
  - 쿼리 파라미터: `category` (all/stock_kr/stock_us/gold/economy), `q` (검색어), `page`, `per_page`
  - 보유 자산 기반 자동 뉴스 + 카테고리 필터링
- [ ] **`GET /api/v1/news/my-assets`** — 보유 자산 기반 뉴스 (자동)
  - 사용자 보유 종목명/심볼로 SerpAPI google_news 검색
  - 각 자산별 최신 뉴스 2~3건씩 통합
- [ ] **NewsService** — SerpAPI `google_news` 엔진 래퍼
  - `search_news(query, gl, hl, page)` 메서드
  - Redis 캐싱 (키: `news:{query_hash}`, TTL: 10분)
  - SerpAPI 크레딧 절약: 동일 검색어 캐시 활용
- [ ] **Pydantic 스키마** — NewsArticle, NewsListResponse

#### 뉴스 페이지 (Frontend)

- [ ] **뉴스 피드 페이지** (`/news`): 카드형 뉴스 목록
- [ ] **카테고리 탭**: 전체 / 내 보유자산 / 국내주식 / 해외주식 / 금 / 경제일반
- [ ] **뉴스 카드**: 썸네일 + 제목 + 출처 + 시간 + 스니펫
- [ ] **무한 스크롤**: TanStack Query `useInfiniteQuery` 활용
- [ ] **검색**: 뉴스 검색 입력 + 디바운스
- [ ] **외부 링크**: 뉴스 클릭 → 새 탭에서 원본 기사 열기
- [ ] **로딩/에러/빈 상태** UI

### 2.2 Out of Scope (향후 분리)

- 뉴스 북마크/저장 기능 (DB 저장 필요)
- AI 기반 뉴스 요약/감정 분석 (ai-insight feature로 분리)
- 뉴스 알림/푸시 (notification feature로 분리)
- 뉴스 댓글/공유 기능
- RSS 피드 연동

---

## 3. 기술 설계 방향

### 3.1 SerpAPI google_news 엔진 활용

```
SerpAPI Endpoint: GET https://serpapi.com/search
  engine: google_news
  q: "삼성전자" (또는 "Samsung Electronics" 등)
  gl: kr (한국)
  hl: ko (한국어)
  api_key: {SERPAPI_KEY}

Response:
{
  "news_results": [
    {
      "position": 1,
      "link": "https://...",
      "title": "삼성전자, AI 반도체 수주 확대...",
      "source": {
        "name": "한국경제",
        "icon": "https://..."
      },
      "date": "2시간 전",
      "snippet": "삼성전자가 AI 반도체 시장에서...",
      "thumbnail": "https://..."
    }
  ]
}
```

### 3.2 뉴스 API 설계

```
GET /api/v1/news?category=all&q=&page=1&per_page=20
Authorization: Bearer {token}

Response:
{
  "articles": [
    {
      "id": "hash-based-unique-id",
      "title": "삼성전자, AI 반도체 수주 확대",
      "link": "https://...",
      "source_name": "한국경제",
      "source_icon": "https://...",
      "snippet": "삼성전자가 AI 반도체 시장에서...",
      "thumbnail": "https://...",
      "published_at": "2시간 전",
      "category": "stock_kr",
      "related_asset": "삼성전자"
    }
  ],
  "page": 1,
  "per_page": 20,
  "has_next": true
}

GET /api/v1/news/my-assets
Authorization: Bearer {token}

Response:
{
  "articles": [...],  // 보유 자산별 뉴스 통합 (최신순)
  "asset_queries": ["삼성전자", "TSLA", "금 시세"]  // 검색에 사용된 키워드
}
```

### 3.3 Backend 아키텍처

```
app/
├── schemas/
│   └── news.py                # NewsArticle, NewsListResponse
├── services/
│   └── news_service.py        # SerpAPI google_news 래퍼 + 캐싱
└── api/v1/endpoints/
    └── news.py                # /api/v1/news 라우터
```

- `NewsService` 클래스: `MarketService`와 동일한 패턴 (Redis 캐싱, httpx)
- 보유 자산 뉴스: `asset_service.get_user_assets()`로 종목 목록 조회 → 각 종목별 `google_news` 검색
- `asyncio.gather()`로 병렬 검색 (최대 5개 자산 동시 검색, API 제한 고려)
- Redis 캐싱: `news:{query_hash}`, TTL 10분 (뉴스는 시세보다 긴 TTL)

### 3.4 카테고리 → SerpAPI 쿼리 매핑

| 카테고리 | SerpAPI 쿼리 | 설명 |
|---------|-------------|------|
| `all` | `금융 OR 증시 OR 경제` | 금융 일반 뉴스 |
| `my_assets` | 보유 종목명 OR 조합 | 사용자별 자동 생성 |
| `stock_kr` | `한국 증시 OR 코스피 OR 코스닥` | 국내 주식 |
| `stock_us` | `미국 증시 OR 나스닥 OR S&P500` | 해외 주식 |
| `gold` | `금 시세 OR 금값 OR 금투자` | 금 관련 |
| `economy` | `한국 경제 OR 금리 OR 환율` | 경제 일반 |

### 3.5 Frontend 아키텍처 (FSD)

```
features/news/
├── api/
│   └── index.ts              # useNewsFeed, useMyAssetNews (TanStack Query)
├── ui/
│   ├── NewsCard.tsx           # 뉴스 카드 컴포넌트
│   ├── NewsCategoryTabs.tsx   # 카테고리 탭
│   ├── NewsSearchBar.tsx      # 검색 입력
│   └── NewsCardSkeleton.tsx   # 로딩 스켈레톤
└── lib/
    └── constants.ts           # 카테고리 정의, 색상 매핑

pages/news/
└── index.tsx                  # 뉴스 피드 페이지
```

### 3.6 뉴스 카드 UI 레이아웃

```
┌─────────────────────────────────────────────────┐
│  [카테고리 탭: 전체 | 내 보유자산 | 국내 | 해외 | 금 | 경제]   │
│  [🔍 뉴스 검색...]                                        │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────┬──────────────────────────────┐    │
│  │ 🖼️       │ 삼성전자, AI 반도체 수주 확대  │    │
│  │ thumbnail│ 한국경제 · 2시간 전           │    │
│  │          │ 삼성전자가 AI 반도체 시장에서...│    │
│  └──────────┴──────────────────────────────┘    │
│                                                 │
│  ┌──────────┬──────────────────────────────┐    │
│  │ 🖼️       │ TSLA, 완전자율주행 업데이트    │    │
│  │ thumbnail│ Reuters · 3시간 전            │    │
│  │          │ Tesla announced a new FSD...  │    │
│  └──────────┴──────────────────────────────┘    │
│                                                 │
│  ... (무한 스크롤)                                │
│                                                 │
└─────────────────────────────────────────────────┘

Mobile (1열): 카드 세로 스택, 썸네일 위/텍스트 아래
Desktop: 썸네일 좌측/텍스트 우측 (수평 레이아웃)
```

---

## 4. 의존성

### 4.1 선행 조건

| 의존성 | 상태 | 비고 |
|--------|------|------|
| asset-management 기능 | 구현 완료 | 보유 자산 목록 조회 API |
| MarketService (SerpAPI 패턴) | 구현 완료 | httpx + Redis 캐싱 패턴 재사용 |
| Auth (JWT 인증) | 구현 완료 | 사용자별 보유 자산 기반 뉴스 |
| Redis | 구현 완료 | 뉴스 캐싱 |
| SerpAPI KEY | 설정 필요 | `.env` 파일의 `SERPAPI_KEY` |

### 4.2 새로 추가할 의존성

| 패키지 | 용도 | 비고 |
|--------|------|------|
| (없음) | - | 기존 httpx, redis 패키지 사용 |

### 4.3 구현 순서 (권장)

```
Phase 1: Backend — 뉴스 서비스 & API
  1. Pydantic 스키마 정의 (NewsArticle, NewsListResponse, MyAssetNewsResponse)
  2. NewsService 작성 (SerpAPI google_news 래퍼 + Redis 캐싱)
  3. 뉴스 엔드포인트 구현 (GET /news, GET /news/my-assets)
  4. main.py 라우터 등록

Phase 2: Frontend — 타입 & API Hook
  5. shared/types에 News 관련 타입 추가
  6. features/news/api — TanStack Query hooks (useInfiniteQuery)

Phase 3: Frontend — UI 컴포넌트
  7. NewsCard (뉴스 카드)
  8. NewsCategoryTabs (카테고리 탭)
  9. NewsSearchBar (검색 입력 + 디바운스)
  10. NewsCardSkeleton (로딩 스켈레톤)

Phase 4: Frontend — 페이지 조합
  11. pages/news 페이지 (카테고리 탭 + 검색 + 무한 스크롤)
  12. 반응형 레이아웃 + API 연동
```

---

## 5. 리스크 및 고려사항

| 리스크 | 영향 | 대응 방안 |
|--------|------|-----------|
| SerpAPI 크레딧 소진 | 뉴스 검색 불가 | Redis 10분 캐싱, "내 보유자산" 검색 시 최대 5개 자산 병렬 검색 제한 |
| SerpAPI google_news 응답 지연 | 뉴스 로딩 느림 | asyncio.gather 병렬 검색 + 캐시 우선 |
| 보유 자산이 없는 사용자 | "내 보유자산" 탭 비어있음 | Empty State UI + 자산 등록 유도 CTA |
| 뉴스 썸네일 없는 기사 | 레이아웃 깨짐 | 기본 placeholder 이미지 처리 |
| 뉴스 중복 | 동일 기사 다른 출처 | 제목 해시 기반 중복 제거 |
| SerpAPI KEY 미설정 | 뉴스 기능 전체 불가 | mock 뉴스 데이터 반환 + 설정 안내 |

---

## 6. 성공 기준

- [ ] 카테고리별 뉴스 목록 정상 조회 (전체, 국내주식, 해외주식, 금, 경제)
- [ ] 보유 자산 기반 자동 뉴스 검색 정상 동작
- [ ] 뉴스 검색 기능 (검색어 입력 → 결과 표시)
- [ ] 뉴스 카드 UI (썸네일, 제목, 출처, 시간, 스니펫) 정상 렌더링
- [ ] 무한 스크롤 동작 (페이지 하단 도달 → 다음 페이지 로드)
- [ ] 뉴스 클릭 → 새 탭에서 원본 기사 열기
- [ ] Redis 캐싱 정상 동작 (동일 검색어 10분 캐시)
- [ ] 반응형 레이아웃 (모바일/데스크톱) 정상 동작
- [ ] 로딩 스켈레톤 + 에러 상태 + 빈 상태 UI
- [ ] SerpAPI KEY 미설정 시 graceful degradation (mock 데이터 또는 안내)

---

## 7. 다음 단계

Plan 승인 후 → `/pdca design news` 로 상세 설계 문서 작성
