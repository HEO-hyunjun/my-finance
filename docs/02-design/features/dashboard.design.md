# Design: Dashboard (통합 대시보드)

> **Feature**: dashboard
> **Created**: 2026-02-13
> **Plan Reference**: `docs/01-plan/features/dashboard.plan.md`
> **PDCA Phase**: Design

---

## 1. Backend 상세 설계

### 1.1 Pydantic 스키마

**파일**: `backend/app/schemas/dashboard.py`

```python
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


# --- 대시보드 내부 서브 스키마 ---

class DashboardAssetSummary(BaseModel):
    """자산 요약 (기존 AssetSummaryResponse 재활용 가능)"""
    total_value_krw: float
    total_invested_krw: float
    total_profit_loss: float
    total_profit_loss_rate: float
    breakdown: dict[str, float]  # {"stock_kr": 15000000, ...}


class DashboardBudgetCategory(BaseModel):
    """예산 카테고리 요약 (상위 5개)"""
    name: str
    icon: str | None = None
    color: str | None = None
    budget: float
    spent: float
    usage_rate: float


class DashboardBudgetSummary(BaseModel):
    """예산 요약"""
    total_budget: float
    total_spent: float
    total_remaining: float
    total_usage_rate: float
    total_fixed_expenses: float
    total_installments: float
    top_categories: list[DashboardBudgetCategory]


class DashboardTransaction(BaseModel):
    """최근 거래 (축약)"""
    id: str
    asset_name: str
    asset_type: str
    type: str  # buy, sell, exchange
    quantity: float
    unit_price: float
    currency: str
    transacted_at: datetime


class DashboardMarketItem(BaseModel):
    """시세/환율 아이템"""
    symbol: str
    name: str | None = None
    price: float
    currency: str
    change: float | None = None
    change_percent: float | None = None


class DashboardMarketInfo(BaseModel):
    """시세 정보"""
    exchange_rate: DashboardMarketItem
    gold_price: DashboardMarketItem | None = None


class DashboardPayment(BaseModel):
    """결제 일정 아이템"""
    name: str
    amount: float
    payment_day: int
    type: str  # "fixed" or "installment"
    remaining: str | None = None  # 할부: "3/12"
    category_name: str | None = None
    category_color: str | None = None


class DashboardMaturityAlert(BaseModel):
    """만기 알림 아이템"""
    name: str
    asset_type: str  # deposit, savings
    maturity_date: date
    principal: float
    maturity_amount: float | None = None
    days_remaining: int
    bank_name: str | None = None


# --- 대시보드 통합 응답 ---

class DashboardSummaryResponse(BaseModel):
    """대시보드 통합 응답"""
    asset_summary: DashboardAssetSummary
    budget_summary: DashboardBudgetSummary
    recent_transactions: list[DashboardTransaction]
    market_info: DashboardMarketInfo
    upcoming_payments: list[DashboardPayment]
    maturity_alerts: list[DashboardMaturityAlert]
```

---

### 1.2 서비스 레이어

**파일**: `backend/app/services/dashboard_service.py`

```python
import asyncio
import json
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.schemas.dashboard import (
    DashboardAssetSummary,
    DashboardBudgetCategory,
    DashboardBudgetSummary,
    DashboardMarketInfo,
    DashboardMarketItem,
    DashboardMaturityAlert,
    DashboardPayment,
    DashboardSummaryResponse,
    DashboardTransaction,
)
from app.services.asset_service import get_asset_summary
from app.services.budget_service import BudgetService
from app.services.market_service import MarketService
from app.services.transaction_service import get_transactions


async def get_dashboard_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    market: MarketService,
    redis=None,
) -> DashboardSummaryResponse:
    """
    대시보드 통합 데이터를 병렬로 조회하여 반환.

    캐싱 전략:
    - Redis 키: dashboard:{user_id}
    - TTL: 60초
    - 캐시 hit 시 JSON deserialize하여 반환
    - 캐시 miss 시 모든 서비스 병렬 호출 후 캐싱
    """

    # 1. Redis 캐시 확인
    if redis:
        cached = await redis.get(f"dashboard:{user_id}")
        if cached:
            return DashboardSummaryResponse.model_validate_json(cached)

    # 2. 병렬 데이터 조회
    today = date.today()

    (
        asset_summary_raw,
        budget_summary_raw,
        transactions_raw,
        exchange_rate_raw,
        gold_price_raw,
    ) = await asyncio.gather(
        get_asset_summary(db, user_id, market),
        BudgetService.get_budget_summary(db, user_id),
        get_transactions(db, user_id, page=1, per_page=5),
        market.get_exchange_rate(),
        _safe_get_gold_price(market),
    )

    # 3. 고정비 & 할부 조회 (이번 달 결제 예정)
    fixed_expenses = await BudgetService.get_fixed_expenses(db, user_id)
    installments = await BudgetService.get_installments(db, user_id)

    # 4. 만기 임박 예금/적금 조회
    maturity_alerts = await _get_maturity_alerts(db, user_id, today)

    # 5. 응답 조합
    result = DashboardSummaryResponse(
        asset_summary=_map_asset_summary(asset_summary_raw),
        budget_summary=_map_budget_summary(budget_summary_raw),
        recent_transactions=_map_transactions(transactions_raw),
        market_info=_map_market_info(exchange_rate_raw, gold_price_raw),
        upcoming_payments=_map_payments(fixed_expenses, installments, today),
        maturity_alerts=maturity_alerts,
    )

    # 6. Redis 캐시 저장
    if redis:
        await redis.set(
            f"dashboard:{user_id}",
            result.model_dump_json(),
            ex=60,
        )

    return result


async def _safe_get_gold_price(market: MarketService):
    """금 시세 조회 (실패 시 None 반환)"""
    try:
        return await market.get_price("GLD", asset_type=None)
    except Exception:
        return None


async def _get_maturity_alerts(
    db: AsyncSession,
    user_id: uuid.UUID,
    today: date,
    days_threshold: int = 30,
) -> list[DashboardMaturityAlert]:
    """만기 30일 이내 예금/적금 조회"""
    # assets 테이블에서 deposit/savings 타입 + maturity_date 필터
    ...


def _map_asset_summary(raw) -> DashboardAssetSummary:
    """AssetSummaryResponse → DashboardAssetSummary 매핑"""
    return DashboardAssetSummary(
        total_value_krw=raw.total_value_krw,
        total_invested_krw=raw.total_invested_krw,
        total_profit_loss=raw.total_profit_loss,
        total_profit_loss_rate=raw.total_profit_loss_rate,
        breakdown=raw.breakdown,
    )


def _map_budget_summary(raw) -> DashboardBudgetSummary:
    """BudgetSummaryResponse → DashboardBudgetSummary 매핑"""
    # 카테고리 상위 5개 (사용률 기준 내림차순)
    top_cats = sorted(raw.categories, key=lambda c: c.usage_rate, reverse=True)[:5]
    return DashboardBudgetSummary(
        total_budget=raw.total_budget,
        total_spent=raw.total_spent,
        total_remaining=raw.total_remaining,
        total_usage_rate=raw.total_usage_rate,
        total_fixed_expenses=raw.total_fixed_expenses,
        total_installments=raw.total_installments,
        top_categories=[
            DashboardBudgetCategory(
                name=c.category_name,
                icon=c.category_icon,
                color=c.category_color,
                budget=c.monthly_budget,
                spent=c.spent,
                usage_rate=c.usage_rate,
            )
            for c in top_cats
        ],
    )


def _map_transactions(raw) -> list[DashboardTransaction]:
    """TransactionListResponse → list[DashboardTransaction] 매핑"""
    return [
        DashboardTransaction(
            id=str(tx.id),
            asset_name=tx.asset_name,
            asset_type=tx.asset_type,
            type=tx.type.value if hasattr(tx.type, "value") else tx.type,
            quantity=tx.quantity,
            unit_price=tx.unit_price,
            currency=tx.currency.value if hasattr(tx.currency, "value") else tx.currency,
            transacted_at=tx.transacted_at,
        )
        for tx in raw.data
    ]


def _map_market_info(exchange_rate_raw, gold_price_raw) -> DashboardMarketInfo:
    """시세 정보 매핑"""
    return DashboardMarketInfo(
        exchange_rate=DashboardMarketItem(
            symbol="USD/KRW",
            name="미국 달러",
            price=exchange_rate_raw.rate,
            currency="KRW",
            change=exchange_rate_raw.change,
            change_percent=exchange_rate_raw.change_percent,
        ),
        gold_price=(
            DashboardMarketItem(
                symbol=gold_price_raw.symbol,
                name="금",
                price=gold_price_raw.price,
                currency=gold_price_raw.currency,
                change=gold_price_raw.change,
                change_percent=gold_price_raw.change_percent,
            )
            if gold_price_raw
            else None
        ),
    )


def _map_payments(
    fixed_expenses, installments, today: date
) -> list[DashboardPayment]:
    """이번 달 남은 결제 일정 (날짜순 정렬)"""
    payments: list[DashboardPayment] = []
    current_day = today.day

    # 고정비: 활성 상태 + 결제일이 오늘 이후
    for fe in fixed_expenses:
        if fe.is_active and fe.payment_day >= current_day:
            payments.append(
                DashboardPayment(
                    name=fe.name,
                    amount=fe.amount,
                    payment_day=fe.payment_day,
                    type="fixed",
                    category_name=fe.category_name,
                    category_color=fe.category_color,
                )
            )

    # 할부: 활성 상태 + 결제일이 오늘 이후 + 잔여 회차 있음
    for inst in installments:
        if inst.is_active and inst.payment_day >= current_day and inst.remaining_installments > 0:
            payments.append(
                DashboardPayment(
                    name=inst.name,
                    amount=inst.monthly_amount,
                    payment_day=inst.payment_day,
                    type="installment",
                    remaining=f"{inst.paid_installments}/{inst.total_installments}",
                    category_name=inst.category_name,
                    category_color=inst.category_color,
                )
            )

    # 결제일 기준 오름차순 정렬
    payments.sort(key=lambda p: p.payment_day)
    return payments
```

**핵심 설계 원칙:**
- **Facade 패턴**: 기존 서비스(`AssetService`, `BudgetService`, `MarketService`, `TransactionService`)를 조합
- **`asyncio.gather()`**: 5개 서비스 호출을 병렬로 처리하여 응답 시간 최소화
- **Redis 캐싱**: `dashboard:{user_id}` 키, 60초 TTL로 반복 요청 최적화
- **안전한 시세 조회**: `_safe_get_gold_price()`로 금 시세 실패 시에도 대시보드 정상 동작

---

### 1.3 API 엔드포인트

**파일**: `backend/app/api/v1/endpoints/dashboard.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import get_dashboard_summary
from app.services.market_service import MarketService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """대시보드 통합 데이터 조회"""
    redis = await get_redis()
    market = MarketService(redis)
    return await get_dashboard_summary(
        db=db,
        user_id=current_user.id,
        market=market,
        redis=redis,
    )
```

**API 명세:**

```
GET /api/v1/dashboard/summary
  - Auth: Required (JWT Bearer)
  - Response: DashboardSummaryResponse
  - 200: 대시보드 통합 데이터
  - 401: 인증 실패
  - 500: 내부 서버 오류 (개별 서비스 실패 시 부분 데이터 반환 고려)
```

**라우터 등록 (`backend/app/main.py`):**

```python
from app.api.v1.endpoints import dashboard

app.include_router(dashboard.router, prefix="/api/v1")
```

---

## 2. Frontend 상세 설계

### 2.1 TypeScript 타입 정의

**파일**: `frontend/src/shared/types/index.ts` (기존 파일에 추가)

```typescript
// ========== Dashboard Types ==========

export interface DashboardAssetSummary {
  total_value_krw: number;
  total_invested_krw: number;
  total_profit_loss: number;
  total_profit_loss_rate: number;
  breakdown: Record<string, number>;
}

export interface DashboardBudgetCategory {
  name: string;
  icon?: string;
  color?: string;
  budget: number;
  spent: number;
  usage_rate: number;
}

export interface DashboardBudgetSummary {
  total_budget: number;
  total_spent: number;
  total_remaining: number;
  total_usage_rate: number;
  total_fixed_expenses: number;
  total_installments: number;
  top_categories: DashboardBudgetCategory[];
}

export interface DashboardTransaction {
  id: string;
  asset_name: string;
  asset_type: string;
  type: string;
  quantity: number;
  unit_price: number;
  currency: string;
  transacted_at: string;
}

export interface DashboardMarketItem {
  symbol: string;
  name?: string;
  price: number;
  currency: string;
  change?: number;
  change_percent?: number;
}

export interface DashboardMarketInfo {
  exchange_rate: DashboardMarketItem;
  gold_price?: DashboardMarketItem;
}

export interface DashboardPayment {
  name: string;
  amount: number;
  payment_day: number;
  type: 'fixed' | 'installment';
  remaining?: string;
  category_name?: string;
  category_color?: string;
}

export interface DashboardMaturityAlert {
  name: string;
  asset_type: string;
  maturity_date: string;
  principal: number;
  maturity_amount?: number;
  days_remaining: number;
  bank_name?: string;
}

export interface DashboardSummaryResponse {
  asset_summary: DashboardAssetSummary;
  budget_summary: DashboardBudgetSummary;
  recent_transactions: DashboardTransaction[];
  market_info: DashboardMarketInfo;
  upcoming_payments: DashboardPayment[];
  maturity_alerts: DashboardMaturityAlert[];
}
```

---

### 2.2 TanStack Query Hook

**파일**: `frontend/src/features/dashboard/api/index.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/config';
import type { DashboardSummaryResponse } from '@/shared/types';

export const dashboardKeys = {
  all: ['dashboard'] as const,
  summary: () => [...dashboardKeys.all, 'summary'] as const,
};

export function useDashboardSummary() {
  return useQuery({
    queryKey: dashboardKeys.summary(),
    queryFn: async (): Promise<DashboardSummaryResponse> => {
      const { data } = await apiClient.get('/api/v1/dashboard/summary');
      return data;
    },
    staleTime: 5 * 60 * 1000,     // 5분 동안 fresh 유지
    refetchInterval: 5 * 60 * 1000, // 5분마다 자동 리패치
    refetchOnWindowFocus: true,     // 탭 전환 시 리패치
  });
}
```

---

### 2.3 UI 컴포넌트 설계

#### 2.3.1 컴포넌트 트리

```
pages/dashboard/index.tsx
├── TotalAssetWidget          # 총 자산 요약 카드
├── AssetDistChart            # 자산 분포 도넛 차트 (Recharts)
├── BudgetStatusWidget        # 예산 현황 위젯
│   └── BudgetProgressBar     # 카테고리별 진행률 바 (inline)
├── RecentTxWidget            # 최근 거래 위젯
├── MarketInfoWidget          # 환율/시세 위젯
├── PaymentScheduleWidget     # 결제 일정 위젯
└── MaturityAlertWidget       # 만기 알림 위젯
```

#### 2.3.2 컴포넌트 상세

**TotalAssetWidget** — `features/dashboard/ui/TotalAssetWidget.tsx`

```
┌─────────────────────────────────────────────────┐
│  내 총 자산                                      │
│  ₩52,340,000                                    │
│  ▲ ₩4,340,000 (+9.04%)                          │
│                                                 │
│  투자금 ₩48,000,000                              │
└─────────────────────────────────────────────────┘
```

- Props: `summary: DashboardAssetSummary`
- 수익: 양수 → `text-green-600`, 음수 → `text-red-500`
- 금액 포맷: `Intl.NumberFormat('ko-KR')` 사용
- Empty State: "아직 등록된 자산이 없습니다. 자산을 추가해보세요!" + CTA 버튼

**AssetDistChart** — `features/dashboard/ui/AssetDistChart.tsx`

```
┌─────────────────────────────────────┐
│  자산 분포                           │
│                                     │
│       ┌──────────┐                  │
│      /   stock_us  \                │
│     │   38.2%       │               │
│     │   stock_kr    │               │
│      \  28.7%      /                │
│       └──────────┘                  │
│                                     │
│  ● 국내주식 28.7%  ● 미국주식 38.2%  │
│  ● 금 9.6%  ● 예금 9.6%  ...        │
└─────────────────────────────────────┘
```

- Props: `breakdown: Record<string, number>`
- Recharts: `<PieChart>` + `<Pie>` (도넛: `innerRadius={60} outerRadius={80}`)
- 색상 매핑:
  ```typescript
  const ASSET_COLORS: Record<string, string> = {
    stock_kr: '#3B82F6',    // blue-500
    stock_us: '#8B5CF6',    // violet-500
    gold: '#F59E0B',        // amber-500
    cash_krw: '#10B981',    // emerald-500
    cash_usd: '#06B6D4',    // cyan-500
    deposit: '#6366F1',     // indigo-500
    savings: '#EC4899',     // pink-500
    parking: '#84CC16',     // lime-500
  };
  ```
- 소규모 항목 (< 3%): "기타"로 합산
- Empty State: "자산을 등록하면 분포 차트를 볼 수 있어요."

**BudgetStatusWidget** — `features/dashboard/ui/BudgetStatusWidget.tsx`

```
┌─────────────────────────────────────────────────┐
│  이번 달 예산                                    │
│  ₩1,250,000 / ₩2,000,000  (62.5%)               │
│  ██████████████░░░░░░░░░                         │
│                                                 │
│  식비      ₩380,000/₩500,000  ████████████░░  76% │
│  교통      ₩150,000/₩200,000  ██████████░░░░  75% │
│  쇼핑      ₩180,000/₩300,000  ████████░░░░░░  60% │
│                                                 │
│  고정비 ₩450,000  |  할부 ₩200,000               │
└─────────────────────────────────────────────────┘
```

- Props: `budget: DashboardBudgetSummary`
- 진행률 바: Tailwind CSS `<div>` 기반
  - 사용률 < 70%: `bg-green-500`
  - 사용률 70-90%: `bg-yellow-500`
  - 사용률 > 90%: `bg-red-500`
- 최대 5개 카테고리 표시
- Empty State: "예산 카테고리를 설정해보세요!"

**RecentTxWidget** — `features/dashboard/ui/RecentTxWidget.tsx`

```
┌─────────────────────────────────────────────────┐
│  최근 거래                           전체보기 →   │
│─────────────────────────────────────────────────│
│  🟢 삼성전자     매수   10주   ₩720,000  02/13   │
│  🔴 TSLA        매도    5주   $1,250    02/12   │
│  🟢 금 1g       매수    1g    ₩95,000   02/11   │
│  🔵 원→달러     환전   $500   ₩660,000  02/10   │
│  🟢 예금이자     -      -     ₩12,500   02/09   │
└─────────────────────────────────────────────────┘
```

- Props: `transactions: DashboardTransaction[]`
- 거래 유형 아이콘: buy → 초록, sell → 빨강, exchange → 파랑
- "전체보기" 클릭 → `/assets` 페이지 이동 (거래 내역 탭)
- Empty State: "아직 거래 내역이 없습니다."

**MarketInfoWidget** — `features/dashboard/ui/MarketInfoWidget.tsx`

```
┌─────────────────────────────────────┐
│  시세 정보                           │
│                                     │
│  USD/KRW   ₩1,320.50  ▼ -5.20      │
│  금 (g)    ₩95,000    ▲ +1,200     │
└─────────────────────────────────────┘
```

- Props: `market: DashboardMarketInfo`
- 상승: `text-red-500` + ▲, 하락: `text-blue-500` + ▼ (한국 주식 관행)
- 금 시세가 null이면 해당 행 숨김

**PaymentScheduleWidget** — `features/dashboard/ui/PaymentScheduleWidget.tsx`

```
┌─────────────────────────────────────────────────┐
│  이번 달 결제 일정                                │
│─────────────────────────────────────────────────│
│  15일  넷플릭스        고정비    ₩17,000          │
│  20일  노트북 할부     할부 3/12  ₩125,000        │
│  25일  통신비          고정비    ₩55,000          │
│─────────────────────────────────────────────────│
│  총 ₩197,000                                    │
└─────────────────────────────────────────────────┘
```

- Props: `payments: DashboardPayment[]`
- 고정비/할부 구분 배지: `bg-gray-100` / `bg-blue-100`
- 하단에 결제 합계 표시
- Empty State: "등록된 결제 일정이 없습니다."

**MaturityAlertWidget** — `features/dashboard/ui/MaturityAlertWidget.tsx`

```
┌─────────────────────────────────────────────────┐
│  만기 임박                                       │
│─────────────────────────────────────────────────│
│  ⚠️ 신한 정기예금    D-16     원금 ₩10,000,000   │
│     만기일: 2026-03-01                           │
│─────────────────────────────────────────────────│
│  ⏳ KB 적금          D-45     원금 ₩5,000,000    │
│     만기일: 2026-03-30                           │
└─────────────────────────────────────────────────┘
```

- Props: `alerts: DashboardMaturityAlert[]`
- D-day 색상: ≤7일 `text-red-600`, ≤14일 `text-orange-500`, ≤30일 `text-yellow-600`
- 만기 금액 포함 시 만기 예상 수령액 표시
- Empty State: 위젯 자체를 숨김 (만기 임박 상품이 없으면 표시 불필요)

---

### 2.4 포맷 유틸리티

**파일**: `frontend/src/features/dashboard/lib/format.ts`

```typescript
/**
 * 금액 포맷 (한국 원화)
 * formatKRW(1234567) → "₩1,234,567"
 * formatKRW(1234567, true) → "₩123만"
 */
export function formatKRW(amount: number, compact?: boolean): string {
  if (compact && Math.abs(amount) >= 10000) {
    const man = amount / 10000;
    return `₩${man.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}만`;
  }
  return `₩${amount.toLocaleString('ko-KR')}`;
}

/**
 * 퍼센트 포맷
 * formatPercent(9.04) → "+9.04%"
 * formatPercent(-2.5) → "-2.50%"
 */
export function formatPercent(rate: number): string {
  const sign = rate >= 0 ? '+' : '';
  return `${sign}${rate.toFixed(2)}%`;
}

/**
 * 날짜 포맷
 * formatDate("2026-02-13T09:30:00Z") → "02/13"
 */
export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
}
```

---

### 2.5 페이지 레이아웃

**파일**: `frontend/src/pages/dashboard/index.tsx`

```typescript
import { useDashboardSummary } from '@/features/dashboard/api';
import { TotalAssetWidget } from '@/features/dashboard/ui/TotalAssetWidget';
import { AssetDistChart } from '@/features/dashboard/ui/AssetDistChart';
import { BudgetStatusWidget } from '@/features/dashboard/ui/BudgetStatusWidget';
import { RecentTxWidget } from '@/features/dashboard/ui/RecentTxWidget';
import { MarketInfoWidget } from '@/features/dashboard/ui/MarketInfoWidget';
import { PaymentScheduleWidget } from '@/features/dashboard/ui/PaymentScheduleWidget';
import { MaturityAlertWidget } from '@/features/dashboard/ui/MaturityAlertWidget';

export function Component() {
  const { data, isLoading, isError } = useDashboardSummary();

  if (isLoading) return <DashboardSkeleton />;
  if (isError || !data) return <DashboardError />;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Row 1: 총 자산 (전체 너비) */}
      <TotalAssetWidget summary={data.asset_summary} />

      {/* Row 2: 자산분포 + 예산현황 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <AssetDistChart breakdown={data.asset_summary.breakdown} />
        <BudgetStatusWidget budget={data.budget_summary} />
      </div>

      {/* Row 3: 최근거래 + 시세/결제/만기 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <RecentTxWidget transactions={data.recent_transactions} />
        <div className="space-y-6">
          <MarketInfoWidget market={data.market_info} />
          <PaymentScheduleWidget payments={data.upcoming_payments} />
        </div>
        {data.maturity_alerts.length > 0 && (
          <MaturityAlertWidget alerts={data.maturity_alerts} />
        )}
      </div>
    </div>
  );
}
```

**반응형 레이아웃 정리:**

| 뷰포트 | 그리드 | 설명 |
|---------|--------|------|
| Mobile (< 768px) | 1열 | 위젯 세로 스택 |
| Tablet (768~1024px) | 2열 | 자산분포+예산 / 거래+시세 |
| Desktop (> 1024px) | 3열 | 거래 + 시세/결제 + 만기 |

**로딩/에러 상태:**

- `DashboardSkeleton`: 위젯 영역에 `animate-pulse` Tailwind 스켈레톤
- `DashboardError`: "데이터를 불러올 수 없습니다. 다시 시도해주세요." + 재시도 버튼

---

## 3. 구현 순서 (Implementation Order)

```
Step 1: Backend — 스키마 & 서비스
  ├── backend/app/schemas/dashboard.py          (Pydantic 스키마)
  └── backend/app/services/dashboard_service.py (Facade 서비스)

Step 2: Backend — 엔드포인트 & 등록
  ├── backend/app/api/v1/endpoints/dashboard.py (API 라우터)
  └── backend/app/main.py                       (라우터 등록 추가)

Step 3: Frontend — 타입 & API Hook
  ├── frontend/src/shared/types/index.ts        (Dashboard 타입 추가)
  └── frontend/src/features/dashboard/api/index.ts (TanStack Query hook)

Step 4: Frontend — 유틸리티
  └── frontend/src/features/dashboard/lib/format.ts (포맷 함수)

Step 5: Frontend — 위젯 구현
  ├── features/dashboard/ui/TotalAssetWidget.tsx
  ├── features/dashboard/ui/AssetDistChart.tsx    (recharts 설치 필요)
  ├── features/dashboard/ui/BudgetStatusWidget.tsx
  ├── features/dashboard/ui/RecentTxWidget.tsx
  ├── features/dashboard/ui/MarketInfoWidget.tsx
  ├── features/dashboard/ui/PaymentScheduleWidget.tsx
  └── features/dashboard/ui/MaturityAlertWidget.tsx

Step 6: Frontend — 페이지 조합
  └── frontend/src/pages/dashboard/index.tsx     (위젯 그리드 + 스켈레톤)

Step 7: 통합
  └── recharts npm 설치 + API 연동 테스트
```

---

## 4. 에러 처리 전략

### 4.1 Backend

| 상황 | 처리 |
|------|------|
| 개별 서비스 호출 실패 (시세 등) | 해당 필드 기본값/null 반환, 전체 API 실패 아님 |
| 자산 데이터 없음 | 빈 breakdown, holdings 반환 (정상 200) |
| 예산 미설정 | 0값 BudgetSummary 반환 |
| Redis 연결 실패 | 캐시 없이 직접 서비스 호출 (graceful degradation) |
| 인증 실패 | 401 Unauthorized |

### 4.2 Frontend

| 상황 | 처리 |
|------|------|
| API 로딩 중 | DashboardSkeleton (각 위젯 영역 pulse) |
| API 에러 | DashboardError + 재시도 버튼 |
| 데이터 비어있음 | 각 위젯별 Empty State UI |
| 네트워크 오프라인 | TanStack Query 캐시 데이터 유지 표시 |

---

## 5. 검증 체크리스트

Design → Do 전환 시 다음 항목을 구현 검증 기준으로 사용:

- [ ] **BE-1**: `DashboardSummaryResponse` Pydantic 스키마 정의
- [ ] **BE-2**: `dashboard_service.get_dashboard_summary()` 구현 (asyncio.gather 병렬 조회)
- [ ] **BE-3**: `GET /api/v1/dashboard/summary` 엔드포인트 동작
- [ ] **BE-4**: Redis 캐싱 (60초 TTL, 사용자별 키)
- [ ] **BE-5**: 만기 임박 예금/적금 필터링 (30일 이내)
- [ ] **BE-6**: 이번 달 남은 결제 일정 필터링 (오늘 이후)
- [ ] **BE-7**: 금 시세 실패 시 graceful degradation (null 반환)
- [ ] **FE-1**: `useDashboardSummary` TanStack Query hook 구현
- [ ] **FE-2**: `TotalAssetWidget` — 총 자산, 수익률, 투자금 표시
- [ ] **FE-3**: `AssetDistChart` — Recharts 도넛 차트 렌더링
- [ ] **FE-4**: `BudgetStatusWidget` — 예산 진행률 바 + 카테고리 상위 5개
- [ ] **FE-5**: `RecentTxWidget` — 최근 5건 거래 목록
- [ ] **FE-6**: `MarketInfoWidget` — 환율 + 금 시세
- [ ] **FE-7**: `PaymentScheduleWidget` — 고정비/할부 결제 일정
- [ ] **FE-8**: `MaturityAlertWidget` — 만기 임박 알림 (D-day)
- [ ] **FE-9**: 대시보드 페이지 반응형 그리드 레이아웃
- [ ] **FE-10**: 로딩 스켈레톤 + 에러 상태 UI
- [ ] **FE-11**: 각 위젯 Empty State UI
- [ ] **FE-12**: Dashboard 타입 정의 (`shared/types`)

---

## 6. 다음 단계

Design 승인 후 → `/pdca do dashboard` 로 구현 시작
