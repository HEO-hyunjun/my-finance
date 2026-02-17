# Plan: Dashboard (통합 대시보드)

> **Feature**: dashboard
> **Created**: 2026-02-13
> **PRD Reference**: 섹션 2.3 (대시보드), 2.1.4 (자산 요약 뷰), 2.2 (예산 관리 요약)
> **PDCA Phase**: Plan

---

## 1. 기능 개요

로그인 후 첫 화면으로, 사용자의 전체 재무 상태를 한눈에 파악할 수 있는 종합 대시보드. 자산 현황, 예산 소비율, 최근 거래, 환율 정보를 위젯 형태로 통합 제공한다.

### 1.1 핵심 목표

- 총 자산 가치(KRW 기준) 및 전일 대비 증감 표시
- 자산 유형별 분포 차트 (도넛/파이 차트)
- 이번 달 예산 소비 현황 (진행률 바)
- 최근 거래 내역 (최근 5건)
- USD/KRW 환율 정보 + 금 시세
- 예금/적금 만기 임박 알림
- 고정비/할부 이번 달 결제 일정

### 1.2 기존 구현 피처 연계

| 연계 피처 | 활용 데이터 | API |
|-----------|-------------|-----|
| asset-management | 자산 목록, 보유 현황, 요약 | `GET /api/v1/assets/summary` |
| budget-management | 예산 요약, 지출 현황 | `GET /api/v1/budget/summary` |
| deposit-savings | 예금/적금 보유 현황 | `GET /api/v1/assets` (type filter) |
| market | 환율, 금시세 | `GET /api/v1/market/exchange-rate`, `GET /api/v1/market/price` |
| transactions | 최근 거래 내역 | `GET /api/v1/transactions?limit=5` |
| fixed-expenses | 고정비 결제 일정 | `GET /api/v1/fixed-expenses` |
| installments | 할부 결제 일정 | `GET /api/v1/installments` |

---

## 2. 구현 범위

### 2.1 In Scope (이번 Plan)

#### 대시보드 위젯 구성

- [ ] **총 자산 요약 위젯**: 총 자산 가치, 전일 대비 증감액/증감률
- [ ] **자산 분포 차트 위젯**: 자산 유형별 비중 도넛 차트 (stock_kr, stock_us, gold, cash_krw, cash_usd, deposit, savings, parking)
- [ ] **예산 현황 위젯**: 이번 달 총 예산 vs 지출, 카테고리별 소비 진행률 (상위 3~5개)
- [ ] **최근 거래 위젯**: 최근 5건 거래 내역 (자산명, 유형, 금액, 날짜)
- [ ] **환율/시세 위젯**: USD/KRW 환율, 금 시세(g당), 전일 대비 변동
- [ ] **결제 일정 위젯**: 이번 달 남은 고정비/할부 결제 예정 (날짜순)
- [ ] **예금/적금 만기 알림 위젯**: 만기 30일 이내 상품 표시

#### Backend (대시보드 전용 API)

- [ ] **`GET /api/v1/dashboard/summary`** — 대시보드 통합 데이터 API
  - 총 자산 요약 (AssetSummary)
  - 예산 요약 (BudgetSummary)
  - 최근 거래 5건
  - 환율/시세 정보
  - 고정비/할부 이번 달 일정
  - 만기 임박 상품
- [ ] **Redis 캐싱**: 대시보드 데이터 1분 캐싱 (사용자별 키)

#### Frontend

- [ ] **대시보드 페이지** (`/dashboard`): 위젯 그리드 레이아웃
- [ ] **위젯 컴포넌트**: 각 섹션 독립 컴포넌트
- [ ] **차트 라이브러리**: Recharts 또는 Chart.js 연동
- [ ] **TanStack Query**: 대시보드 데이터 fetch + auto-refetch (5분)
- [ ] **반응형 레이아웃**: 모바일(1열) / 태블릿(2열) / 데스크톱(3열)

### 2.2 Out of Scope (향후 분리)

- 자산 추이 히스토리 차트 (일별 스냅샷 기반 — snapshot feature로 분리)
- 대시보드 위젯 커스터마이징 (위젯 순서 변경, 표시/숨기기)
- AI 기반 재무 인사이트/조언 (ai-insight feature로 분리)
- 뉴스 피드 위젯 (news feature로 분리)
- 알림/푸시 시스템 (notification feature로 분리)

---

## 3. 기술 설계 방향

### 3.1 대시보드 통합 API 설계

```
GET /api/v1/dashboard/summary
Authorization: Bearer {token}

Response:
{
  "asset_summary": {
    "total_value_krw": 52340000,
    "total_invested_krw": 48000000,
    "total_profit_loss": 4340000,
    "total_profit_loss_rate": 9.04,
    "breakdown": {
      "stock_kr": 15000000,
      "stock_us": 20000000,
      "gold": 5000000,
      "cash_krw": 2000000,
      "cash_usd": 3340000,
      "deposit": 5000000,
      "savings": 2000000
    }
  },
  "budget_summary": {
    "total_budget": 2000000,
    "total_spent": 1250000,
    "total_remaining": 750000,
    "total_usage_rate": 62.5,
    "total_fixed_expenses": 450000,
    "total_installments": 200000,
    "top_categories": [
      { "name": "식비", "budget": 500000, "spent": 380000, "usage_rate": 76.0 },
      { "name": "교통", "budget": 200000, "spent": 150000, "usage_rate": 75.0 },
      { "name": "쇼핑", "budget": 300000, "spent": 180000, "usage_rate": 60.0 }
    ]
  },
  "recent_transactions": [
    {
      "id": "...",
      "asset_name": "삼성전자",
      "type": "buy",
      "quantity": 10,
      "unit_price": 72000,
      "transacted_at": "2026-02-13T09:30:00Z"
    }
  ],
  "market_info": {
    "exchange_rate": { "pair": "USD/KRW", "rate": 1320.50, "change": -5.20 },
    "gold_price": { "symbol": "GOLD", "price": 95000, "change": 1200 }
  },
  "upcoming_payments": [
    { "name": "넷플릭스", "amount": 17000, "payment_day": 15, "type": "fixed" },
    { "name": "노트북 할부", "amount": 125000, "payment_day": 20, "type": "installment", "remaining": "3/12" }
  ],
  "maturity_alerts": [
    { "name": "신한 정기예금", "maturity_date": "2026-03-01", "principal": 10000000, "days_remaining": 16 }
  ]
}
```

### 3.2 Backend 아키텍처

```
app/
├── services/
│   └── dashboard_service.py    # 대시보드 통합 데이터 조합 서비스
└── api/v1/endpoints/
    └── dashboard.py            # /api/v1/dashboard 라우터
```

- `DashboardService`는 기존 서비스들을 조합(aggregation)하는 Facade 패턴
- 개별 서비스 호출: `AssetService`, `BudgetService`, `MarketService`, `TransactionService`
- `asyncio.gather()` 로 병렬 데이터 조회
- Redis 캐싱: `dashboard:{user_id}` 키, TTL 60초

### 3.3 Frontend 아키텍처 (FSD)

```
features/dashboard/
├── api/
│   └── index.ts              # useDashboardSummary (TanStack Query)
├── ui/
│   ├── TotalAssetWidget.tsx   # 총 자산 요약
│   ├── AssetDistChart.tsx     # 자산 분포 도넛 차트
│   ├── BudgetStatusWidget.tsx # 예산 현황
│   ├── RecentTxWidget.tsx     # 최근 거래
│   ├── MarketInfoWidget.tsx   # 환율/시세
│   ├── PaymentSchedule.tsx    # 결제 일정
│   └── MaturityAlert.tsx      # 만기 알림
└── lib/
    └── format.ts             # 금액 포맷, 퍼센트 포맷 유틸

pages/dashboard/
└── index.tsx                 # 위젯 그리드 조합
```

### 3.4 위젯 그리드 레이아웃

```
Desktop (3열):
┌──────────────────┬──────────────────┬──────────────────┐
│  총 자산 요약     │  예산 현황        │  환율/시세        │
│  (전체 너비 or)  │                  │                  │
├──────────────────┼──────────────────┼──────────────────┤
│  자산 분포 차트   │  최근 거래        │  결제 일정        │
│                  │                  │  + 만기 알림       │
└──────────────────┴──────────────────┴──────────────────┘

Mobile (1열):
┌──────────────────┐
│  총 자산 요약     │
├──────────────────┤
│  자산 분포 차트   │
├──────────────────┤
│  예산 현황        │
├──────────────────┤
│  최근 거래        │
├──────────────────┤
│  환율/시세        │
├──────────────────┤
│  결제 일정        │
├──────────────────┤
│  만기 알림        │
└──────────────────┘
```

### 3.5 차트 라이브러리 선택

| 라이브러리 | 번들 사이즈 | React 친화도 | 선택 |
|-----------|------------|-------------|------|
| Recharts | ~40KB | React 네이티브 | **선택** |
| Chart.js | ~60KB | react-chartjs-2 래퍼 | 대안 |

- Recharts 선택 이유: React 컴포넌트 기반, 가볍고, 커스텀 쉬움
- 도넛 차트: `<PieChart>` + `<Pie>` 컴포넌트
- 진행률 바: Tailwind CSS `<div>` 기반 커스텀 (추가 의존성 불필요)

---

## 4. 의존성

### 4.1 선행 조건

| 의존성 | 상태 | 비고 |
|--------|------|------|
| asset-management 기능 | 구현 완료 | AssetSummary API 활용 |
| budget-management 기능 | 구현 완료 | BudgetSummary API 활용 |
| deposit-savings 기능 | 구현 완료 | 예금/적금 자산 데이터 활용 |
| Market API (시세/환율) | 구현 완료 | MarketService 활용 |
| Transaction API | 구현 완료 | 최근 거래 조회 |
| Fixed Expenses / Installments API | 구현 완료 | 결제 일정 데이터 |
| Auth (JWT 인증) | 구현 완료 | 사용자별 데이터 조회 |

### 4.2 새로 추가할 의존성

| 패키지 | 용도 | 비고 |
|--------|------|------|
| `recharts` | 차트 라이브러리 | 자산 분포 도넛 차트 |

### 4.3 구현 순서 (권장)

```
Phase 1: Backend — 대시보드 통합 API
  1. DashboardService 작성 (기존 서비스 조합)
  2. Dashboard 엔드포인트 구현 (/api/v1/dashboard/summary)
  3. Pydantic 응답 스키마 정의
  4. Redis 캐싱 적용

Phase 2: Frontend — 공통 설정
  5. recharts 패키지 설치
  6. features/dashboard/api — TanStack Query hook
  7. shared/types에 Dashboard 관련 타입 추가

Phase 3: Frontend — 위젯 구현
  8. TotalAssetWidget (총 자산 요약)
  9. AssetDistChart (자산 분포 도넛 차트)
  10. BudgetStatusWidget (예산 현황)
  11. RecentTxWidget (최근 거래)
  12. MarketInfoWidget (환율/시세)
  13. PaymentSchedule (결제 일정)
  14. MaturityAlert (만기 알림)

Phase 4: Frontend — 페이지 조합
  15. pages/dashboard 위젯 그리드 레이아웃
  16. 반응형 디자인 적용
  17. API 연동 테스트
```

---

## 5. 리스크 및 고려사항

| 리스크 | 영향 | 대응 방안 |
|--------|------|-----------|
| 대시보드 API 응답 지연 (다수 서비스 호출) | 초기 로딩 느림 | `asyncio.gather()` 병렬 조회 + Redis 60초 캐싱 |
| 데이터 없는 신규 사용자 | 빈 대시보드 UX | 빈 상태(Empty State) UI 디자인, 데이터 입력 유도 CTA |
| 차트 렌더링 성능 (다수 자산 유형) | 모바일 성능 저하 | 최대 8개 카테고리 제한, 소규모 카테고리 "기타"로 합산 |
| SerpAPI 호출 크레딧 제한 | 시세 정보 누락 가능 | 캐시 hit 우선, 대시보드에서는 시세 API 직접 호출 최소화 |
| 고정비/할부 데이터 없는 경우 | 결제 일정 위젯 비어있음 | 해당 위젯 조건부 렌더링 또는 안내 메시지 |

---

## 6. 성공 기준

- [ ] 대시보드 페이지에서 총 자산 가치 및 증감률 표시
- [ ] 자산 유형별 분포 도넛 차트 정상 렌더링
- [ ] 이번 달 예산 소비율 (전체 + 카테고리 상위 3개) 표시
- [ ] 최근 거래 5건 목록 표시
- [ ] USD/KRW 환율 및 금 시세 표시
- [ ] 이번 달 남은 고정비/할부 결제 일정 표시
- [ ] 만기 30일 이내 예금/적금 알림 표시
- [ ] 반응형 레이아웃 (모바일/태블릿/데스크톱) 정상 동작
- [ ] 대시보드 API 응답 < 500ms (캐시 hit 시 < 100ms)
- [ ] 데이터 없는 상태에서 빈 상태 UI 정상 표시

---

## 7. 다음 단계

Plan 승인 후 → `/pdca design dashboard` 로 상세 설계 문서 작성
