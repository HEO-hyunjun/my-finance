# Design: Asset Management (자산 관리)

> **Feature**: asset-management
> **Created**: 2026-02-04
> **Plan Reference**: `docs/01-plan/features/asset-management.plan.md`
> **PRD Reference**: 섹션 2.1, 5.1, 5.2, 6.1
> **PDCA Phase**: Design

---

## 1. Backend 상세 설계

### 1.1 SQLAlchemy 모델

#### 1.1.1 User 모델 (선행 — auth feature와 공유)

**파일**: `backend/app/models/user.py`

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    default_currency: Mapped[str] = mapped_column(
        String(3), default="KRW", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

#### 1.1.2 Asset 모델

**파일**: `backend/app/models/asset.py`

```python
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AssetType(str, PyEnum):
    STOCK_KR = "stock_kr"
    STOCK_US = "stock_us"
    GOLD = "gold"
    CASH_KRW = "cash_krw"
    CASH_USD = "cash_usd"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type_enum"), nullable=False
    )
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    transactions = relationship("Transaction", back_populates="asset", cascade="all, delete-orphan")
```

#### 1.1.3 Transaction 모델

**파일**: `backend/app/models/transaction.py`

```python
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, Enum, Numeric, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransactionType(str, PyEnum):
    BUY = "buy"
    SELL = "sell"
    EXCHANGE = "exchange"


class CurrencyType(str, PyEnum):
    KRW = "KRW"
    USD = "USD"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_transacted", "user_id", "transacted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type_enum"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[CurrencyType] = mapped_column(
        Enum(CurrencyType, name="currency_type_enum"), nullable=False
    )
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    transacted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    asset = relationship("Asset", back_populates="transactions")
```

---

### 1.2 Pydantic 스키마

#### 1.2.1 Asset 스키마

**파일**: `backend/app/schemas/asset.py`

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.asset import AssetType


# --- Request ---

class AssetCreate(BaseModel):
    asset_type: AssetType
    symbol: str | None = None
    name: str = Field(max_length=100)


# --- Response ---

class AssetResponse(BaseModel):
    id: uuid.UUID
    asset_type: AssetType
    symbol: str | None
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetHoldingResponse(BaseModel):
    """자산 상세 — 보유량, 평균단가, 현재가, 수익률 포함"""
    id: uuid.UUID
    asset_type: AssetType
    symbol: str | None
    name: str
    quantity: float           # 보유량
    avg_price: float          # 평균 매입가 (원화 기준)
    current_price: float      # 현재가 (원화 기준)
    exchange_rate: float | None  # 현재 환율 (해외자산)
    total_value_krw: float    # 현재 평가액 (KRW)
    total_invested_krw: float # 총 투자금 (KRW)
    profit_loss: float        # 수익/손실 (KRW)
    profit_loss_rate: float   # 수익률 (%)
    created_at: datetime


class AssetSummaryResponse(BaseModel):
    """자산 요약 — 총자산, 유형별 소계"""
    total_value_krw: float
    total_invested_krw: float
    total_profit_loss: float
    total_profit_loss_rate: float
    breakdown: dict[str, float]  # {"stock_kr": 1234.0, "stock_us": 5678.0, ...}
    holdings: list[AssetHoldingResponse]
```

#### 1.2.2 Transaction 스키마

**파일**: `backend/app/schemas/transaction.py`

```python
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.transaction import TransactionType, CurrencyType


# --- Request ---

class TransactionCreate(BaseModel):
    asset_id: uuid.UUID
    type: TransactionType
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    currency: CurrencyType
    exchange_rate: Decimal | None = None
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    memo: str | None = Field(default=None, max_length=500)
    transacted_at: datetime


class TransactionUpdate(BaseModel):
    type: TransactionType | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    currency: CurrencyType | None = None
    exchange_rate: Decimal | None = None
    fee: Decimal | None = Field(default=None, ge=0)
    memo: str | None = Field(default=None, max_length=500)
    transacted_at: datetime | None = None


class TransactionFilter(BaseModel):
    asset_id: uuid.UUID | None = None
    asset_type: str | None = None
    type: TransactionType | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


# --- Response ---

class TransactionResponse(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    asset_name: str
    asset_type: str
    type: TransactionType
    quantity: float
    unit_price: float
    currency: CurrencyType
    exchange_rate: float | None
    fee: float
    memo: str | None
    transacted_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    data: list[TransactionResponse]
    total: int
    page: int
    per_page: int
```

#### 1.2.3 Market 스키마

**파일**: `backend/app/schemas/market.py`

```python
from pydantic import BaseModel


class PriceResponse(BaseModel):
    symbol: str
    name: str | None = None
    price: float
    currency: str
    change: float | None = None
    change_percent: float | None = None
    is_market_open: bool = True
    cached: bool = False


class ExchangeRateResponse(BaseModel):
    pair: str = "USD/KRW"
    rate: float
    change: float | None = None
    change_percent: float | None = None
    cached: bool = False
```

---

### 1.3 서비스 레이어

#### 1.3.1 Asset Service

**파일**: `backend/app/services/asset_service.py`

**핵심 메서드:**

| 메서드 | 설명 | 인자 | 반환 |
|--------|------|------|------|
| `create_asset(db, user_id, data)` | 자산 등록 | AssetCreate | AssetResponse |
| `get_assets(db, user_id)` | 보유 자산 목록 | - | list[AssetResponse] |
| `get_asset_detail(db, user_id, asset_id, market)` | 자산 상세 + 보유량/수익률 | asset_id | AssetHoldingResponse |
| `get_asset_summary(db, user_id, market)` | 자산 요약 (총자산, 유형별) | - | AssetSummaryResponse |
| `delete_asset(db, user_id, asset_id)` | 자산 삭제 (거래 포함 CASCADE) | asset_id | None |
| `calculate_holding(transactions, current_price, exchange_rate)` | 보유량/수익률 계산 | - | dict |

**자산 계산 로직 상세:**

```python
def calculate_holding(
    buy_transactions: list[Transaction],
    sell_transactions: list[Transaction],
    current_price: float,
    current_exchange_rate: float | None,
    is_foreign: bool,
) -> dict:
    """
    보유량, 평균단가, 수익률 계산

    계산 공식:
    - quantity = sum(buy.qty) - sum(sell.qty)
    - avg_price_native = sum(buy.qty * buy.unit_price) / sum(buy.qty)
    - avg_price_krw:
        - 국내: avg_price_native
        - 해외: sum(buy.qty * buy.unit_price * buy.exchange_rate) / sum(buy.qty)
    - total_invested_krw = quantity * avg_price_krw
    - total_value_krw:
        - 국내: quantity * current_price
        - 해외: quantity * current_price * current_exchange_rate
    - profit_loss = total_value_krw - total_invested_krw
    - profit_loss_rate = (profit_loss / total_invested_krw) * 100
    """
```

**유효성 검증:**
- 매도 시: 보유량 초과 매도 방지 (quantity check)
- 동일 자산 중복 등록 방지: (user_id, asset_type, symbol) unique 검사
- 현금(cash_krw, cash_usd): symbol 불필요, quantity = 금액 그 자체

#### 1.3.2 Transaction Service

**파일**: `backend/app/services/transaction_service.py`

**핵심 메서드:**

| 메서드 | 설명 | 인자 | 반환 |
|--------|------|------|------|
| `create_transaction(db, user_id, data)` | 거래 기록 | TransactionCreate | TransactionResponse |
| `get_transactions(db, user_id, filters)` | 거래 내역 조회 (필터+페이징) | TransactionFilter | TransactionListResponse |
| `update_transaction(db, user_id, tx_id, data)` | 거래 수정 | TransactionUpdate | TransactionResponse |
| `delete_transaction(db, user_id, tx_id)` | 거래 삭제 | tx_id | None |

**비즈니스 규칙:**
- 거래 생성/수정 시 asset 소유권 검증 (user_id 일치)
- 매도(sell) 시 보유량 초과 여부 체크
- exchange 타입: from_asset과 to_asset 간 환전 (향후 확장)
- transacted_at: 과거 날짜 허용 (소급 기록)

#### 1.3.3 Market Service

**파일**: `backend/app/services/market_service.py`

**핵심 메서드:**

| 메서드 | 설명 | 인자 | 반환 |
|--------|------|------|------|
| `get_price(symbol)` | 시세 조회 (Redis 캐시 → SerpAPI) | symbol | PriceResponse |
| `get_exchange_rate()` | USD/KRW 환율 조회 | - | ExchangeRateResponse |
| `_fetch_from_serpapi(query)` | SerpAPI google_finance 직접 호출 | query | dict |
| `_get_cached(key)` | Redis 캐시 조회 | key | dict or None |
| `_set_cached(key, data, ttl)` | Redis 캐시 저장 | key, data, ttl | None |

**SerpAPI 쿼리 매핑:**

| 자산 유형 | SerpAPI 쿼리 | 예시 |
|-----------|-------------|------|
| stock_kr | `{symbol}:KRX` | `005930:KRX` |
| stock_us | `{symbol}:NASDAQ` 또는 `{symbol}:NYSE` | `TSLA:NASDAQ` |
| gold | `GLD:NYSEARCA` | 금 ETF 기준 |
| cash_usd | `USD-KRW` | 환율 |
| cash_krw | - (시세 조회 불필요) | - |

**Redis 캐시 전략:**

```
캐시 키 패턴:
  market:price:{symbol}      → TTL 5분 (300초)
  market:exchange_rate:USDKRW → TTL 5분 (300초)

직렬화: JSON string
```

**에러 처리:**
- SerpAPI 호출 실패 시: 이전 캐시 값 반환 (stale cache fallback), 없으면 503
- Rate limit 초과 시: 429 반환 + Retry-After 헤더

---

### 1.4 API 엔드포인트

#### 1.4.1 Assets Router

**파일**: `backend/app/api/v1/endpoints/assets.py`

```
GET    /api/v1/assets
  - Auth: Required (JWT Bearer)
  - Response: list[AssetResponse]
  - 200: 보유 자산 목록

POST   /api/v1/assets
  - Auth: Required
  - Body: AssetCreate
  - Response: AssetResponse
  - 201: 자산 생성 성공
  - 409: 동일 자산 이미 존재

GET    /api/v1/assets/summary
  - Auth: Required
  - Response: AssetSummaryResponse
  - 200: 자산 요약 (총자산, 유형별, 수익률)
  - 내부: Market Service 호출하여 현재가 반영

GET    /api/v1/assets/{id}
  - Auth: Required
  - Response: AssetHoldingResponse
  - 200: 자산 상세 (보유량, 평균단가, 현재가, 수익률)
  - 404: 자산 없음

DELETE /api/v1/assets/{id}
  - Auth: Required
  - Response: 204 No Content
  - 404: 자산 없음
```

#### 1.4.2 Transactions Router

**파일**: `backend/app/api/v1/endpoints/transactions.py`

```
GET    /api/v1/transactions
  - Auth: Required
  - Query: asset_id?, asset_type?, type?, start_date?, end_date?, page, per_page
  - Response: TransactionListResponse
  - 200: 거래 내역 (페이지네이션)

POST   /api/v1/transactions
  - Auth: Required
  - Body: TransactionCreate
  - Response: TransactionResponse
  - 201: 거래 기록 성공
  - 400: 매도 시 보유량 초과
  - 404: asset_id 없음

PUT    /api/v1/transactions/{id}
  - Auth: Required
  - Body: TransactionUpdate
  - Response: TransactionResponse
  - 200: 거래 수정 성공
  - 404: 거래 없음

DELETE /api/v1/transactions/{id}
  - Auth: Required
  - Response: 204 No Content
  - 404: 거래 없음
```

#### 1.4.3 Market Router

**파일**: `backend/app/api/v1/endpoints/market.py`

```
GET    /api/v1/market/price
  - Auth: Required
  - Query: symbol (required), exchange? (KRX, NASDAQ, NYSE, NYSEARCA)
  - Response: PriceResponse
  - 200: 시세 정보
  - 503: SerpAPI 조회 실패

GET    /api/v1/market/exchange-rate
  - Auth: Required
  - Response: ExchangeRateResponse
  - 200: USD/KRW 환율
```

#### 1.4.4 Auth 의존성 (공통)

**파일**: `backend/app/api/deps.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
```

#### 1.4.5 Redis 의존성

**파일**: `backend/app/core/redis.py`

```python
import redis.asyncio as redis
from app.core.config import settings

redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
```

---

### 1.5 Alembic 마이그레이션

**마이그레이션 순서:**

1. `001_create_users_table.py` — users 테이블
2. `002_create_assets_table.py` — assets 테이블 + asset_type_enum
3. `003_create_transactions_table.py` — transactions 테이블 + 인덱스 + enums

**Alembic 초기 설정 필요사항:**
- `alembic.ini`: DATABASE_URL 환경변수 참조
- `alembic/env.py`: async 설정 + Base.metadata import

---

## 2. Frontend 상세 설계

### 2.1 TypeScript 타입 정의

**파일**: `frontend/src/shared/types/index.ts` (기존 파일 확장)

기존 `AssetType`, `TransactionType`, `AssetHolding` 타입을 유지하며 다음을 추가/수정:

```typescript
// 기존 유지: AssetType, TransactionType

// 자산 (DB 엔티티)
export interface Asset {
  id: string;
  asset_type: AssetType;
  symbol?: string;
  name: string;
  created_at: string;
}

// 거래 (DB 엔티티) — 기존 Transaction 인터페이스 수정
export interface Transaction {
  id: string;
  asset_id: string;
  asset_name: string;
  asset_type: string;
  type: TransactionType;
  quantity: number;
  unit_price: number;
  currency: 'KRW' | 'USD';
  exchange_rate?: number;
  fee: number;
  memo?: string;
  transacted_at: string;
  created_at: string;
}

// AssetHolding — 기존 유지 + 추가 필드
export interface AssetHolding {
  id: string;
  asset_type: AssetType;
  symbol?: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  exchange_rate?: number;
  total_value_krw: number;
  total_invested_krw: number;
  profit_loss: number;
  profit_loss_rate: number;
  created_at: string;
}

// 자산 요약
export interface AssetSummary {
  total_value_krw: number;
  total_invested_krw: number;
  total_profit_loss: number;
  total_profit_loss_rate: number;
  breakdown: Record<AssetType, number>;
  holdings: AssetHolding[];
}

// 시세
export interface PriceInfo {
  symbol: string;
  name?: string;
  price: number;
  currency: string;
  change?: number;
  change_percent?: number;
  is_market_open: boolean;
  cached: boolean;
}

// 거래 생성 요청
export interface TransactionCreateRequest {
  asset_id: string;
  type: TransactionType;
  quantity: number;
  unit_price: number;
  currency: 'KRW' | 'USD';
  exchange_rate?: number;
  fee?: number;
  memo?: string;
  transacted_at: string;
}

// 자산 생성 요청
export interface AssetCreateRequest {
  asset_type: AssetType;
  symbol?: string;
  name: string;
}
```

### 2.2 TanStack Query Hooks

**파일**: `frontend/src/features/assets/api/index.ts`

```typescript
// --- Query Keys ---
export const assetKeys = {
  all: ['assets'] as const,
  list: () => [...assetKeys.all, 'list'] as const,
  detail: (id: string) => [...assetKeys.all, 'detail', id] as const,
  summary: () => [...assetKeys.all, 'summary'] as const,
};

export const transactionKeys = {
  all: ['transactions'] as const,
  list: (filters?: TransactionFilter) => [...transactionKeys.all, 'list', filters] as const,
};

export const marketKeys = {
  price: (symbol: string) => ['market', 'price', symbol] as const,
  exchangeRate: () => ['market', 'exchange-rate'] as const,
};

// --- Queries ---

// useAssets(): 보유 자산 목록
// useAssetDetail(id): 자산 상세 (보유량, 수익률)
// useAssetSummary(): 자산 요약
// useTransactions(filters): 거래 내역 (페이지네이션)
// useMarketPrice(symbol): 실시간 시세

// --- Mutations ---

// useCreateAsset(): 자산 추가 → invalidate assetKeys.list
// useDeleteAsset(): 자산 삭제 → invalidate assetKeys.all
// useCreateTransaction(): 거래 기록 → invalidate transactionKeys.all + assetKeys.all
// useUpdateTransaction(): 거래 수정 → invalidate transactionKeys.all + assetKeys.all
// useDeleteTransaction(): 거래 삭제 → invalidate transactionKeys.all + assetKeys.all
```

### 2.3 UI 컴포넌트 설계

#### 2.3.1 컴포넌트 트리

```
pages/assets/index.tsx
├── AssetSummaryCard          # 총자산, 유형별 소계, 총 수익률
├── AssetList                 # 보유 자산 카드 목록
│   └── AssetCard             # 개별 자산 카드 (종목명, 보유량, 현재가, 수익률)
├── TransactionList           # 거래 내역 테이블
│   ├── TransactionFilter     # 필터 (기간, 자산유형)
│   └── TransactionRow        # 개별 거래 행
├── AddAssetModal             # 자산 추가 모달
│   ├── AssetTypeSelector     # 자산 유형 선택
│   └── SymbolSearchInput     # 종목 검색 (주식)
└── AddTransactionModal       # 거래 기록 모달
    └── TransactionForm       # 거래 폼 (유형, 수량, 단가, 수수료, 메모)
```

#### 2.3.2 컴포넌트 상세

**AssetSummaryCard**
```
┌─────────────────────────────────────────┐
│  총 자산       ₩15,234,500   (+3.2%)    │
│                                         │
│  국내주식  ₩5,200,000  │ 해외주식 ₩6,800,000 │
│  금        ₩1,500,000  │ 현금     ₩1,734,500 │
└─────────────────────────────────────────┘
```
- Props: `summary: AssetSummary`
- 수익률: 양수 초록색, 음수 빨간색

**AssetCard**
```
┌──────────────────────────┐
│  🇰🇷 삼성전자 (005930)   │
│  10주 × ₩72,000         │
│  평가: ₩720,000          │
│  수익: +₩20,000 (+2.8%) │
└──────────────────────────┘
```
- Props: `holding: AssetHolding`
- 클릭 시 자산 상세 패널 또는 거래 내역 필터

**TransactionForm**
- 필드: 자산 선택(드롭다운), 거래유형(buy/sell/exchange), 수량, 단가, 수수료, 환율(해외), 메모, 거래일시
- 단가 자동 조회: 주식 선택 시 Market API 호출하여 현재가 자동 입력 (사용자 수정 가능)
- 유효성 검증: quantity > 0, unit_price >= 0, 매도 시 보유량 초과 경고

---

## 3. 구현 순서 (Implementation Order)

```
Step 1: Auth 기반 (선행)
  ├── backend/app/models/user.py
  ├── backend/app/api/deps.py (get_current_user)
  ├── Alembic 초기 설정 + 001_create_users_table
  └── backend/app/core/redis.py

Step 2: Asset/Transaction 모델
  ├── backend/app/models/asset.py
  ├── backend/app/models/transaction.py
  └── Alembic 002, 003 마이그레이션

Step 3: Pydantic 스키마
  ├── backend/app/schemas/asset.py
  ├── backend/app/schemas/transaction.py
  └── backend/app/schemas/market.py

Step 4: 서비스 레이어
  ├── backend/app/services/asset_service.py
  ├── backend/app/services/transaction_service.py
  └── backend/app/services/market_service.py

Step 5: API 엔드포인트
  ├── backend/app/api/v1/endpoints/assets.py
  ├── backend/app/api/v1/endpoints/transactions.py
  ├── backend/app/api/v1/endpoints/market.py
  └── backend/app/main.py (라우터 등록)

Step 6: Frontend 타입 + API hooks
  ├── frontend/src/shared/types/index.ts (확장)
  └── frontend/src/features/assets/api/index.ts

Step 7: Frontend UI 컴포넌트
  ├── frontend/src/features/assets/ui/AssetSummaryCard.tsx
  ├── frontend/src/features/assets/ui/AssetCard.tsx
  ├── frontend/src/features/assets/ui/AssetList.tsx
  ├── frontend/src/features/assets/ui/TransactionList.tsx
  ├── frontend/src/features/assets/ui/TransactionForm.tsx
  ├── frontend/src/features/assets/ui/AddAssetModal.tsx
  └── frontend/src/features/assets/ui/AddTransactionModal.tsx

Step 8: 페이지 조합
  └── frontend/src/pages/assets/index.tsx (리빌드)
```

---

## 4. 에러 처리 전략

### 4.1 Backend HTTP 에러 코드

| 상황 | 코드 | 응답 |
|------|------|------|
| 인증 실패 / 토큰 만료 | 401 | `{"detail": "Not authenticated"}` |
| 타인의 자산/거래 접근 | 404 | `{"detail": "Asset not found"}` (403 노출 방지) |
| 동일 자산 중복 등록 | 409 | `{"detail": "Asset already exists"}` |
| 매도 시 보유량 초과 | 400 | `{"detail": "Insufficient quantity. Available: 10, Requested: 15"}` |
| SerpAPI 조회 실패 | 503 | `{"detail": "Market data unavailable"}` |
| 유효하지 않은 입력 | 422 | Pydantic 자동 검증 에러 |

### 4.2 Frontend 에러 처리

- **TanStack Query onError**: 토스트 알림으로 사용자에게 에러 메시지 표시
- **401**: Axios 인터셉터에서 자동 토큰 갱신 → 실패 시 로그인 페이지 리다이렉트
- **낙관적 업데이트**: 거래 삭제 시 UI 먼저 제거 → 실패 시 롤백

---

## 5. 검증 체크리스트

Design → Do 전환 시 다음 항목을 구현 검증 기준으로 사용:

- [ ] **BE-1**: User 모델 + Alembic 마이그레이션 동작
- [ ] **BE-2**: Asset CRUD API 4개 (GET list, POST, GET detail, DELETE)
- [ ] **BE-3**: Transaction CRUD API 4개 (GET list, POST, PUT, DELETE)
- [ ] **BE-4**: Asset Summary API (GET /assets/summary)
- [ ] **BE-5**: Market Price API + Redis 캐싱
- [ ] **BE-6**: Exchange Rate API + Redis 캐싱
- [ ] **BE-7**: 자산 계산 로직 (보유량, 평균단가, 수익률) 정확성
- [ ] **BE-8**: 매도 시 보유량 초과 방지 검증
- [ ] **BE-9**: JWT 인증 미들웨어 동작
- [ ] **FE-1**: 자산 요약 카드 렌더링
- [ ] **FE-2**: 자산 목록 (AssetCard) 렌더링
- [ ] **FE-3**: 자산 추가 모달 동작
- [ ] **FE-4**: 거래 기록 모달/폼 동작
- [ ] **FE-5**: 거래 내역 리스트 + 필터 + 페이지네이션
- [ ] **FE-6**: TanStack Query 캐시 무효화 정상 동작
- [ ] **FE-7**: 수익률 양수/음수 색상 표시

---

## 6. 다음 단계

Design 승인 후 → `/pdca do asset-management` 로 구현 시작
