# Plan: Asset Management (자산 관리)

> **Feature**: asset-management
> **Created**: 2026-02-04
> **PRD Reference**: 섹션 2.1 (자산 관리), 5.1 (데이터 모델 - assets, transactions), 6.1 (API)
> **PDCA Phase**: Plan

---

## 1. 기능 개요

사용자가 보유한 다양한 자산(국내주식, 미국주식, 금, 원화, 달러)의 매수/매도/환전 거래를 기록하고, SerpAPI를 통해 실시간 시세를 반영한 자산 가치를 추적하는 핵심 기능.

### 1.1 핵심 목표

- 5가지 자산 유형(stock_kr, stock_us, gold, cash_krw, cash_usd) 등록 및 관리
- 거래(buy/sell/exchange) 기록 CRUD
- SerpAPI google_finance 엔진을 통한 실시간 시세 조회
- 자산 요약 뷰 (총 자산, 유형별 소계, 수익률)
- Redis 캐싱으로 API 크레딧 최적화

### 1.2 PRD 근거

| PRD 섹션 | 내용 |
|----------|------|
| 2.1.1 | 지원 자산 유형 5종 |
| 2.1.2 | 거래 기록 필드 정의 (유형, 수량, 단가, 수수료, 환율, 메모) |
| 2.1.3 | SerpAPI google_finance 기반 시세 조회 + Redis 5분 캐싱 |
| 2.1.4 | 자산 요약 뷰 (총자산, 유형별 합계, 수익률) |
| 5.1 | assets, transactions 테이블 스키마 |
| 6.1 | Assets/Transactions/Market API 엔드포인트 |

---

## 2. 구현 범위

### 2.1 In Scope (이번 Plan)

#### Backend
- [ ] **DB 모델**: `assets`, `transactions` SQLAlchemy 모델
- [ ] **Alembic 마이그레이션**: 초기 테이블 생성
- [ ] **Pydantic 스키마**: 요청/응답 스키마 정의
- [ ] **API 엔드포인트**:
  - `GET /api/v1/assets` — 보유 자산 목록
  - `POST /api/v1/assets` — 자산 추가
  - `GET /api/v1/assets/{id}` — 자산 상세 (보유량, 평균단가, 현재가, 수익률)
  - `DELETE /api/v1/assets/{id}` — 자산 삭제
  - `GET /api/v1/transactions` — 거래 내역 (필터: 기간, 자산유형)
  - `POST /api/v1/transactions` — 거래 기록
  - `PUT /api/v1/transactions/{id}` — 거래 수정
  - `DELETE /api/v1/transactions/{id}` — 거래 삭제
- [ ] **시세 서비스**: SerpAPI google_finance 연동 + Redis 캐싱
  - `GET /api/v1/market/price?symbol=` — 실시간 시세 조회
  - `GET /api/v1/market/exchange-rate` — USD/KRW 환율 조회
- [ ] **자산 계산 서비스**: 보유량, 평균단가, 수익률 계산 로직

#### Frontend
- [ ] **자산 목록 페이지** (`/assets`): 보유 자산 카드 뷰
- [ ] **자산 추가 모달**: 자산 유형 선택 + 종목 검색 (주식) / 수동 입력 (현금, 금)
- [ ] **거래 기록 폼**: 매수/매도/환전 입력 폼
- [ ] **거래 내역 리스트**: 필터링 (기간, 자산유형) + 페이지네이션
- [ ] **자산 요약 카드**: 총 자산, 유형별 소계, 총 수익률
- [ ] **TanStack Query 연동**: API 캐싱 및 리페칭

### 2.2 Out of Scope (다음 Plan으로 분리)

- 자산 대시보드 차트 (2.3절 — dashboard feature로 분리)
- 포트폴리오 리밸런싱 (2.3.5절 — portfolio feature로 분리)
- 일일 자산 스냅샷 Celery 태스크 (dashboard feature 연계)
- AI 자산 인사이트 (2.3.6절 — ai-insight feature로 분리)
- 뉴스 연동 (2.4절 — news feature로 분리)

---

## 3. 기술 설계 방향

### 3.1 Backend 아키텍처

```
app/
├── models/
│   ├── user.py          # (auth feature에서 생성 예정, 여기서는 참조만)
│   ├── asset.py         # Asset 모델
│   └── transaction.py   # Transaction 모델
├── schemas/
│   ├── asset.py         # Asset 요청/응답 스키마
│   └── transaction.py   # Transaction 요청/응답 스키마
├── services/
│   ├── asset_service.py      # 자산 CRUD + 계산 로직
│   ├── transaction_service.py # 거래 CRUD
│   └── market_service.py     # SerpAPI 시세 조회 + Redis 캐싱
└── api/v1/endpoints/
    ├── assets.py         # /api/v1/assets 라우터
    ├── transactions.py   # /api/v1/transactions 라우터
    └── market.py         # /api/v1/market 라우터
```

### 3.2 데이터 모델 (PRD 5.1 기반)

**assets 테이블:**
- `id` (PK, UUID)
- `user_id` (FK → users)
- `asset_type` (ENUM: stock_kr, stock_us, gold, cash_krw, cash_usd)
- `symbol` (nullable — 주식 종목코드/티커)
- `name` (자산명)
- `created_at`

**transactions 테이블:**
- `id` (PK, UUID)
- `user_id` (FK → users)
- `asset_id` (FK → assets)
- `type` (ENUM: buy, sell, exchange)
- `quantity` (DECIMAL)
- `unit_price` (DECIMAL)
- `currency` (ENUM: KRW, USD)
- `exchange_rate` (DECIMAL, nullable)
- `fee` (DECIMAL, default: 0)
- `memo` (TEXT, nullable)
- `transacted_at` (TIMESTAMP)
- `created_at`

**인덱스:**
- `transactions`: `(user_id, transacted_at)` 복합 인덱스

### 3.3 시세 서비스 설계

```
SerpAPI 호출 흐름:
┌──────────┐    ┌───────────┐    ┌──────────┐
│ Frontend │───>│ Market API │───>│  Redis   │
│          │    │ Endpoint   │    │ (5분 캐시)│
└──────────┘    └─────┬─────┘    └────┬─────┘
                      │ cache miss      │ cache hit
                      ▼                 │
                ┌───────────┐           │
                │  SerpAPI  │           │
                │ google_   │           │
                │ finance   │───────────┘
                └───────────┘
```

- **캐시 키**: `market:price:{symbol}`, `market:exchange_rate:USD-KRW`
- **캐시 TTL**: 5분 (Redis)
- **장외 시간**: 마지막 종가 반환, `is_market_open: false` 플래그

### 3.4 Frontend 아키텍처 (FSD)

```
features/assets/
├── api/          # TanStack Query hooks (useAssets, useTransactions)
├── model/        # Zustand store (선택적)
├── ui/           # AssetCard, TransactionForm, AssetSummary
└── lib/          # 수익률 계산 유틸 등

pages/assets/
└── index.tsx     # 자산 관리 페이지 (features/assets 조합)
```

### 3.5 자산 계산 로직

```
보유량 = SUM(buy.quantity) - SUM(sell.quantity)
평균 매입가 = SUM(buy.quantity * buy.unit_price) / SUM(buy.quantity)
현재 평가액 = 보유량 * 현재가 * (해외자산 ? 환율 : 1)
수익/손실 = 현재 평가액 - (보유량 * 평균 매입가 * (해외자산 ? 매입시 환율 : 1))
수익률 = 수익/손실 / 총 투자금 * 100
```

---

## 4. 의존성

### 4.1 선행 조건

| 의존성 | 상태 | 비고 |
|--------|------|------|
| users 테이블 & Auth API | 미완 | 자산/거래에 user_id FK 필요. 최소 User 모델 + JWT 인증 미들웨어 필요 |
| PostgreSQL + Alembic 초기 설정 | 미완 | DB 연결 + 마이그레이션 기반 구축 필요 |
| Redis 연결 | 미완 | 시세 캐싱용 |
| SerpAPI 키 | 미완 | .env에 SERPAPI_KEY 설정 필요 |

### 4.2 구현 순서 (권장)

```
Phase 1: 기반 설정 (사전 필요)
  1. User 모델 + Alembic 초기 마이그레이션
  2. JWT 인증 미들웨어 (의존성 주입)
  3. Redis 클라이언트 설정

Phase 2: Backend 핵심
  4. Asset, Transaction 모델 + 마이그레이션
  5. Pydantic 스키마 정의
  6. Asset CRUD 서비스 + API 엔드포인트
  7. Transaction CRUD 서비스 + API 엔드포인트
  8. Market 시세 서비스 (SerpAPI + Redis 캐싱)
  9. 자산 계산 로직 (보유량, 평균단가, 수익률)

Phase 3: Frontend
  10. shared/types 에 Asset, Transaction 타입 확장
  11. features/assets/api — TanStack Query hooks
  12. features/assets/ui — 컴포넌트 (AssetCard, TransactionForm 등)
  13. pages/assets — 페이지 조합
  14. API 연동 테스트
```

---

## 5. 리스크 및 고려사항

| 리스크 | 영향 | 대응 방안 |
|--------|------|-----------|
| SerpAPI 무료 플랜 월 100건 제한 | 시세 조회 빈번 시 크레딧 소진 | Redis 5분 캐싱 적극 활용, 배치 조회 최소화 |
| Auth 기능 미구현 상태 | user_id FK 연결 불가 | Phase 1에서 최소 User 모델 + 인증 먼저 구현 |
| 환율 변동으로 해외자산 평가 복잡성 | 원화 환산 정확도 | 거래 시점 환율 기록 + 현재 환율 실시간 반영 |
| 과거 거래 소급 기록 시 시세 불일치 | 평균단가 계산 오류 가능 | 사용자 수동 단가 입력 허용, API 조회는 보조 |

---

## 6. 성공 기준

- [ ] 5가지 자산 유형 등록/삭제 가능
- [ ] 매수/매도/환전 거래 CRUD 정상 동작
- [ ] SerpAPI 시세 조회 + Redis 캐싱 동작 확인
- [ ] 자산 목록에서 현재가/수익률 표시
- [ ] 자산 요약 (총자산, 유형별 소계) 정확한 계산
- [ ] 프론트엔드 자산 관리 페이지 UI 정상 렌더링
- [ ] API 응답 시간 < 500ms (캐시 hit 시 < 100ms)

---

## 7. 다음 단계

Plan 승인 후 → `/pdca design asset-management` 로 상세 설계 문서 작성
