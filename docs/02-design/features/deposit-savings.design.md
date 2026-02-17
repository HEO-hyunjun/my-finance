# Design: Deposit & Savings (예금/적금/파킹통장)

> **Feature**: deposit-savings
> **Created**: 2026-02-05
> **Plan Reference**: `docs/01-plan/features/deposit-savings.plan.md`
> **Parent Feature**: asset-management (확장)
> **PDCA Phase**: Design

---

## 1. Backend 상세 설계

### 1.1 모델 변경

#### 1.1.1 AssetType enum 확장

**파일**: `backend/app/models/asset.py`

```python
class AssetType(str, PyEnum):
    # 기존
    STOCK_KR = "stock_kr"
    STOCK_US = "stock_us"
    GOLD = "gold"
    CASH_KRW = "cash_krw"
    CASH_USD = "cash_usd"
    # 신규
    DEPOSIT = "deposit"      # 정기예금
    SAVINGS = "savings"      # 적금
    PARKING = "parking"      # CMA/파킹통장
```

#### 1.1.2 InterestType enum 추가

**파일**: `backend/app/models/asset.py`

```python
class InterestType(str, PyEnum):
    SIMPLE = "simple"        # 단리
    COMPOUND = "compound"    # 복리 (월복리)
```

#### 1.1.3 Asset 모델 확장

**파일**: `backend/app/models/asset.py`

기존 필드 유지 + 아래 nullable 필드 추가:

```python
from sqlalchemy import String, DateTime, ForeignKey, Enum, Numeric, Date

class Asset(Base):
    __tablename__ = "assets"

    # --- 기존 필드 (변경 없음) ---
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType, name="asset_type_enum"), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # --- 신규 필드 (예금/적금/파킹통장 전용, nullable) ---
    interest_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 3), nullable=True, comment="연이율 (%, 예: 3.500)"
    )
    interest_type: Mapped[InterestType | None] = mapped_column(
        Enum(InterestType, name="interest_type_enum"), nullable=True, comment="단리/복리"
    )
    principal: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 0), nullable=True, comment="원금 또는 현재잔액 (원)"
    )
    monthly_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 0), nullable=True, comment="월 납입액 (원, 적금 전용)"
    )
    start_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="가입일"
    )
    maturity_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="만기일"
    )
    tax_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 3), nullable=True, default=Decimal("15.400"), comment="이자소득세율 (%, 기본 15.4)"
    )
    bank_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="은행/증권사명"
    )

    # --- Relationships (변경 없음) ---
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="asset", cascade="all, delete-orphan"
    )
```

**주의**: `from datetime import date`를 import에 추가 필요.

---

### 1.2 Pydantic 스키마 확장

#### 1.2.1 AssetCreate 확장

**파일**: `backend/app/schemas/asset.py`

```python
from datetime import date
from decimal import Decimal
from pydantic import model_validator

class AssetCreate(BaseModel):
    # 기존
    asset_type: AssetType
    symbol: str | None = None
    name: str = Field(max_length=100)
    # 신규 (예금/적금/파킹 전용)
    interest_rate: Decimal | None = Field(default=None, gt=0, le=100, description="연이율 (%)")
    interest_type: str | None = Field(default=None, description="simple 또는 compound")
    principal: Decimal | None = Field(default=None, ge=0, description="원금 또는 현재잔액")
    monthly_amount: Decimal | None = Field(default=None, gt=0, description="월 납입액")
    start_date: date | None = None
    maturity_date: date | None = None
    tax_rate: Decimal | None = Field(default=Decimal("15.4"), ge=0, le=100, description="이자소득세율 (%)")
    bank_name: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_by_asset_type(self):
        t = self.asset_type
        if t == AssetType.DEPOSIT:
            if not self.interest_rate:
                raise ValueError("예금은 연이율(interest_rate)이 필수입니다")
            if not self.principal:
                raise ValueError("예금은 원금(principal)이 필수입니다")
            if not self.start_date or not self.maturity_date:
                raise ValueError("예금은 가입일(start_date)과 만기일(maturity_date)이 필수입니다")
            if self.maturity_date <= self.start_date:
                raise ValueError("만기일은 가입일보다 이후여야 합니다")
            if not self.interest_type:
                self.interest_type = "simple"
        elif t == AssetType.SAVINGS:
            if not self.interest_rate:
                raise ValueError("적금은 연이율(interest_rate)이 필수입니다")
            if not self.monthly_amount:
                raise ValueError("적금은 월납입액(monthly_amount)이 필수입니다")
            if not self.start_date or not self.maturity_date:
                raise ValueError("적금은 가입일(start_date)과 만기일(maturity_date)이 필수입니다")
            if self.maturity_date <= self.start_date:
                raise ValueError("만기일은 가입일보다 이후여야 합니다")
        elif t == AssetType.PARKING:
            if not self.interest_rate:
                raise ValueError("파킹통장은 연이율(interest_rate)이 필수입니다")
            if not self.principal:
                raise ValueError("파킹통장은 현재잔액(principal)이 필수입니다")
        return self
```

#### 1.2.2 AssetResponse 확장

**파일**: `backend/app/schemas/asset.py`

```python
class AssetResponse(BaseModel):
    # 기존
    id: uuid.UUID
    asset_type: AssetType
    symbol: str | None
    name: str
    created_at: datetime
    # 신규
    interest_rate: float | None = None
    interest_type: str | None = None
    principal: float | None = None
    monthly_amount: float | None = None
    start_date: date | None = None
    maturity_date: date | None = None
    tax_rate: float | None = None
    bank_name: str | None = None

    model_config = {"from_attributes": True}
```

#### 1.2.3 AssetHoldingResponse 확장

**파일**: `backend/app/schemas/asset.py`

```python
class AssetHoldingResponse(BaseModel):
    """자산 상세 — 보유량, 평균단가, 현재가, 수익률 포함 + 이자 정보"""
    # 기존
    id: uuid.UUID
    asset_type: AssetType
    symbol: str | None
    name: str
    quantity: float
    avg_price: float
    current_price: float
    exchange_rate: float | None
    total_value_krw: float
    total_invested_krw: float
    profit_loss: float
    profit_loss_rate: float
    created_at: datetime
    # 신규 — 예금/적금/파킹 전용 (기존 자산은 모두 None)
    interest_rate: float | None = None
    interest_type: str | None = None
    bank_name: str | None = None
    principal: float | None = None
    monthly_amount: float | None = None
    start_date: date | None = None
    maturity_date: date | None = None
    tax_rate: float | None = None
    accrued_interest_pretax: float | None = None    # 경과 세전이자
    accrued_interest_aftertax: float | None = None  # 경과 세후이자
    maturity_amount: float | None = None            # 만기 예상 수령액 (세후)
    daily_interest: float | None = None             # 일일이자 (파킹통장)
    monthly_interest: float | None = None           # 월예상이자 (파킹통장, 세후)
    elapsed_months: int | None = None               # 경과 개월수
    total_months: int | None = None                 # 총 개월수 (만기까지)
    paid_count: int | None = None                   # 납입 회차 (적금)
```

---

### 1.3 이자 계산 서비스

**파일**: `backend/app/services/interest_service.py` (신규)

```python
from datetime import date
from decimal import Decimal
import math


def calculate_deposit_interest(
    principal: Decimal,
    annual_rate: Decimal,
    start_date: date,
    as_of_date: date,
    maturity_date: date,
    interest_type: str,
    tax_rate: Decimal,
) -> dict:
    """
    예금 이자 계산

    Returns:
        elapsed_months: 경과 개월수
        total_months: 총 개월수
        accrued_interest_pretax: 세전 경과이자
        accrued_interest_aftertax: 세후 경과이자
        maturity_interest_pretax: 만기 세전이자
        maturity_interest_aftertax: 만기 세후이자
        maturity_amount: 만기 수령액 (세후)
        total_value_krw: 현재 평가액 (원금 + 세후 경과이자)
    """
    rate = float(annual_rate) / 100
    tax = float(tax_rate) / 100
    p = float(principal)

    elapsed_days = (as_of_date - start_date).days
    total_days = (maturity_date - start_date).days
    elapsed_months = max(0, round(elapsed_days / 30.44))
    total_months = max(1, round(total_days / 30.44))

    if interest_type == "compound":
        # 월복리
        accrued_pretax = p * ((1 + rate / 12) ** elapsed_months - 1)
        maturity_pretax = p * ((1 + rate / 12) ** total_months - 1)
    else:
        # 단리
        accrued_pretax = p * rate * elapsed_days / 365
        maturity_pretax = p * rate * total_days / 365

    accrued_aftertax = accrued_pretax * (1 - tax)
    maturity_aftertax = maturity_pretax * (1 - tax)
    maturity_amount = p + maturity_aftertax
    total_value = p + accrued_aftertax

    return {
        "elapsed_months": elapsed_months,
        "total_months": total_months,
        "accrued_interest_pretax": round(accrued_pretax),
        "accrued_interest_aftertax": round(accrued_aftertax),
        "maturity_amount": round(maturity_amount),
        "total_value_krw": round(total_value),
    }


def calculate_savings_interest(
    monthly_amount: Decimal,
    annual_rate: Decimal,
    start_date: date,
    as_of_date: date,
    maturity_date: date,
    tax_rate: Decimal,
) -> dict:
    """
    적금 이자 계산 (정액적립식 단리)

    Returns:
        paid_count: 납입 회차
        total_months: 총 개월수
        total_paid: 총 납입액
        accrued_interest_pretax: 세전 경과이자
        accrued_interest_aftertax: 세후 경과이자
        maturity_interest_pretax: 만기 세전이자
        maturity_interest_aftertax: 만기 세후이자
        maturity_amount: 만기 수령액 (세후)
        total_value_krw: 현재 평가액 (납입액 + 세후 경과이자)
    """
    rate = float(annual_rate) / 100
    tax = float(tax_rate) / 100
    m = float(monthly_amount)

    elapsed_days = (as_of_date - start_date).days
    total_days = (maturity_date - start_date).days
    paid_count = max(0, min(
        round(elapsed_days / 30.44),
        round(total_days / 30.44),
    ))
    total_months = max(1, round(total_days / 30.44))

    total_paid = m * paid_count

    # 정액적립식 단리: 각 회차 이자 합산 = m × (rate/12) × n(n+1)/2
    accrued_pretax = m * (rate / 12) * paid_count * (paid_count + 1) / 2
    maturity_pretax = m * (rate / 12) * total_months * (total_months + 1) / 2

    accrued_aftertax = accrued_pretax * (1 - tax)
    maturity_aftertax = maturity_pretax * (1 - tax)
    maturity_amount = m * total_months + maturity_aftertax
    total_value = total_paid + accrued_aftertax

    return {
        "paid_count": paid_count,
        "total_months": total_months,
        "total_paid": round(total_paid),
        "accrued_interest_pretax": round(accrued_pretax),
        "accrued_interest_aftertax": round(accrued_aftertax),
        "maturity_amount": round(maturity_amount),
        "total_value_krw": round(total_value),
    }


def calculate_parking_interest(
    principal: Decimal,
    annual_rate: Decimal,
    tax_rate: Decimal,
) -> dict:
    """
    CMA/파킹통장 일일이자 계산

    Returns:
        daily_interest: 일일이자 (세전)
        monthly_interest: 월예상이자 (세후)
        annual_interest: 연예상이자 (세후)
        total_value_krw: 현재 평가액 (= 잔액, 이자 별도 표시)
    """
    rate = float(annual_rate) / 100
    tax = float(tax_rate) / 100
    p = float(principal)

    daily_interest = p * rate / 365
    monthly_interest = daily_interest * 30 * (1 - tax)
    annual_interest = p * rate * (1 - tax)

    return {
        "daily_interest": round(daily_interest),
        "monthly_interest": round(monthly_interest),
        "annual_interest": round(annual_interest),
        "total_value_krw": round(p),
    }
```

---

### 1.4 asset_service.py 수정

**파일**: `backend/app/services/asset_service.py`

#### 1.4.1 create_asset 확장

Asset 생성 시 신규 필드를 포함:

```python
async def create_asset(db, user_id, data: AssetCreate) -> AssetResponse:
    # 기존 중복 체크 유지
    # ...

    asset = Asset(
        user_id=user_id,
        asset_type=data.asset_type,
        symbol=data.symbol,
        name=data.name,
        # 신규 필드
        interest_rate=data.interest_rate,
        interest_type=InterestType(data.interest_type) if data.interest_type else None,
        principal=data.principal,
        monthly_amount=data.monthly_amount,
        start_date=data.start_date,
        maturity_date=data.maturity_date,
        tax_rate=data.tax_rate,
        bank_name=data.bank_name,
    )
    # ...
```

#### 1.4.2 _calculate_holding 확장

`_calculate_holding` 함수에 예금/적금/파킹통장 분기 추가:

```python
from app.services.interest_service import (
    calculate_deposit_interest,
    calculate_savings_interest,
    calculate_parking_interest,
)
from datetime import date

async def _calculate_holding(asset: Asset, market: MarketService) -> AssetHoldingResponse:
    today = date.today()

    # --- 예금 ---
    if asset.asset_type == AssetType.DEPOSIT:
        result = calculate_deposit_interest(
            principal=asset.principal,
            annual_rate=asset.interest_rate,
            start_date=asset.start_date,
            as_of_date=today,
            maturity_date=asset.maturity_date,
            interest_type=asset.interest_type.value if asset.interest_type else "simple",
            tax_rate=asset.tax_rate,
        )
        return AssetHoldingResponse(
            id=asset.id,
            asset_type=asset.asset_type,
            symbol=None,
            name=asset.name,
            quantity=1,
            avg_price=float(asset.principal),
            current_price=float(asset.principal),
            exchange_rate=None,
            total_value_krw=result["total_value_krw"],
            total_invested_krw=float(asset.principal),
            profit_loss=result["accrued_interest_aftertax"],
            profit_loss_rate=round(result["accrued_interest_aftertax"] / float(asset.principal) * 100, 2) if asset.principal else 0,
            created_at=asset.created_at,
            # 신규 필드
            interest_rate=float(asset.interest_rate),
            interest_type=asset.interest_type.value if asset.interest_type else "simple",
            bank_name=asset.bank_name,
            principal=float(asset.principal),
            start_date=asset.start_date,
            maturity_date=asset.maturity_date,
            tax_rate=float(asset.tax_rate),
            accrued_interest_pretax=result["accrued_interest_pretax"],
            accrued_interest_aftertax=result["accrued_interest_aftertax"],
            maturity_amount=result["maturity_amount"],
            elapsed_months=result["elapsed_months"],
            total_months=result["total_months"],
        )

    # --- 적금 ---
    if asset.asset_type == AssetType.SAVINGS:
        result = calculate_savings_interest(
            monthly_amount=asset.monthly_amount,
            annual_rate=asset.interest_rate,
            start_date=asset.start_date,
            as_of_date=today,
            maturity_date=asset.maturity_date,
            tax_rate=asset.tax_rate,
        )
        return AssetHoldingResponse(
            id=asset.id,
            asset_type=asset.asset_type,
            symbol=None,
            name=asset.name,
            quantity=result["paid_count"],
            avg_price=float(asset.monthly_amount),
            current_price=float(asset.monthly_amount),
            exchange_rate=None,
            total_value_krw=result["total_value_krw"],
            total_invested_krw=result["total_paid"],
            profit_loss=result["accrued_interest_aftertax"],
            profit_loss_rate=round(result["accrued_interest_aftertax"] / result["total_paid"] * 100, 2) if result["total_paid"] else 0,
            created_at=asset.created_at,
            # 신규 필드
            interest_rate=float(asset.interest_rate),
            bank_name=asset.bank_name,
            monthly_amount=float(asset.monthly_amount),
            start_date=asset.start_date,
            maturity_date=asset.maturity_date,
            tax_rate=float(asset.tax_rate),
            accrued_interest_pretax=result["accrued_interest_pretax"],
            accrued_interest_aftertax=result["accrued_interest_aftertax"],
            maturity_amount=result["maturity_amount"],
            elapsed_months=result.get("paid_count"),
            total_months=result["total_months"],
            paid_count=result["paid_count"],
        )

    # --- 파킹통장 ---
    if asset.asset_type == AssetType.PARKING:
        result = calculate_parking_interest(
            principal=asset.principal,
            annual_rate=asset.interest_rate,
            tax_rate=asset.tax_rate,
        )
        return AssetHoldingResponse(
            id=asset.id,
            asset_type=asset.asset_type,
            symbol=None,
            name=asset.name,
            quantity=1,
            avg_price=float(asset.principal),
            current_price=float(asset.principal),
            exchange_rate=None,
            total_value_krw=result["total_value_krw"],
            total_invested_krw=float(asset.principal),
            profit_loss=0,
            profit_loss_rate=0,
            created_at=asset.created_at,
            # 신규 필드
            interest_rate=float(asset.interest_rate),
            bank_name=asset.bank_name,
            principal=float(asset.principal),
            tax_rate=float(asset.tax_rate),
            daily_interest=result["daily_interest"],
            monthly_interest=result["monthly_interest"],
        )

    # --- 기존 자산 유형 (주식, 금, 현금) — 변경 없음 ---
    # ... (기존 _calculate_holding 로직 그대로 유지)
```

---

### 1.5 API 변경사항

기존 API 엔드포인트 자체는 변경 없음. `AssetCreate` 스키마가 확장되므로 POST /api/v1/assets에서 자동으로 신규 필드를 수용함.

**추가 엔드포인트 (선택)**: 파킹통장 잔액 업데이트용

```
PUT /api/v1/assets/{id}/balance
  - Auth: Required
  - Body: { "principal": 5000000 }
  - Response: AssetResponse
  - 200: 잔액 업데이트 성공
  - 기능: parking 타입의 잔액(principal)만 업데이트
```

---

### 1.6 Alembic 마이그레이션

**마이그레이션 내용**:

1. `asset_type_enum`에 `deposit`, `savings`, `parking` 값 추가 (ALTER TYPE ... ADD VALUE)
2. `interest_type_enum` 신규 타입 생성 (simple, compound)
3. `assets` 테이블에 8개 nullable 컬럼 추가:
   - interest_rate, interest_type, principal, monthly_amount, start_date, maturity_date, tax_rate, bank_name

---

## 2. Frontend 상세 설계

### 2.1 TypeScript 타입 변경

**파일**: `frontend/src/shared/types/index.ts`

```typescript
// AssetType 확장
export type AssetType =
  | 'stock_kr' | 'stock_us' | 'gold' | 'cash_krw' | 'cash_usd'
  | 'deposit' | 'savings' | 'parking';

// 이자 유형
export type InterestType = 'simple' | 'compound';

// Asset 인터페이스 확장
export interface Asset {
  id: string;
  asset_type: AssetType;
  symbol?: string;
  name: string;
  created_at: string;
  // 신규
  interest_rate?: number;
  interest_type?: InterestType;
  principal?: number;
  monthly_amount?: number;
  start_date?: string;
  maturity_date?: string;
  tax_rate?: number;
  bank_name?: string;
}

// AssetCreateRequest 확장
export interface AssetCreateRequest {
  asset_type: AssetType;
  symbol?: string;
  name: string;
  // 신규
  interest_rate?: number;
  interest_type?: InterestType;
  principal?: number;
  monthly_amount?: number;
  start_date?: string;
  maturity_date?: string;
  tax_rate?: number;
  bank_name?: string;
}

// AssetHolding 확장
export interface AssetHolding {
  // 기존 필드 유지
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
  // 신규 — 이자 관련 (예금/적금/파킹)
  interest_rate?: number;
  interest_type?: InterestType;
  bank_name?: string;
  principal?: number;
  monthly_amount?: number;
  start_date?: string;
  maturity_date?: string;
  tax_rate?: number;
  accrued_interest_pretax?: number;
  accrued_interest_aftertax?: number;
  maturity_amount?: number;
  daily_interest?: number;
  monthly_interest?: number;
  elapsed_months?: number;
  total_months?: number;
  paid_count?: number;
}

// ASSET_TYPE_LABELS 확장
export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  stock_kr: '국내주식',
  stock_us: '미국주식',
  gold: '금',
  cash_krw: '원화',
  cash_usd: '달러',
  deposit: '예금',
  savings: '적금',
  parking: '파킹통장',
};
```

### 2.2 AddAssetModal 확장

**파일**: `frontend/src/features/assets/ui/AddAssetModal.tsx`

**변경 내용**:
- ASSET_TYPES 배열에 `deposit`, `savings`, `parking` 추가
- AssetTypeSelector 그리드를 `grid-cols-4`로 변경 (8가지 유형)
- 선택된 자산 유형에 따라 조건부 폼 렌더링

```
[deposit 선택 시 표시되는 필드]
├── bank_name (은행명) — text, required
├── principal (원금) — number, required
├── interest_rate (연이율 %) — number, step=0.001, required
├── interest_type (단리/복리) — 토글 버튼 2개
├── start_date (가입일) — date, required
├── maturity_date (만기일) — date, required
└── tax_rate (이자소득세율 %) — number, default=15.4

[savings 선택 시 표시되는 필드]
├── bank_name (은행명) — text, required
├── monthly_amount (월 납입액) — number, required
├── interest_rate (연이율 %) — number, step=0.001, required
├── start_date (가입일) — date, required
├── maturity_date (만기일) — date, required
└── tax_rate (이자소득세율 %) — number, default=15.4

[parking 선택 시 표시되는 필드]
├── bank_name (은행/증권사명) — text, required
├── principal (현재 잔액) — number, required
├── interest_rate (연이율 %) — number, step=0.001, required
└── tax_rate (이자소득세율 %) — number, default=15.4
```

**조건부 렌더링 로직**:
```typescript
const isDeposit = assetType === 'deposit';
const isSavings = assetType === 'savings';
const isParking = assetType === 'parking';
const isInterestBased = isDeposit || isSavings || isParking;
const needsSymbol = ['stock_kr', 'stock_us', 'gold'].includes(assetType);
```

### 2.3 AssetCard 확장

**파일**: `frontend/src/features/assets/ui/AssetCard.tsx`

**변경 내용**:
- ASSET_ICONS에 신규 유형 추가
- 유형에 따라 카드 내용 분기

```typescript
const ASSET_ICONS: Record<string, string> = {
  // 기존
  stock_kr: '🇰🇷', stock_us: '🇺🇸', gold: '🥇', cash_krw: '💴', cash_usd: '💵',
  // 신규
  deposit: '🏦', savings: '💰', parking: '🅿️',
};
```

**카드 레이아웃 분기**:

```
[deposit / savings 카드]
┌──────────────────────────┐
│ 🏦 신한은행 정기예금       │
│    예금 | 연 3.500%       │
│                          │
│ 원금       ₩10,000,000   │
│ 경과이자    ₩175,000 (세후)│
│ 평가금액    ₩10,175,000   │
│ 만기 예상   ₩10,350,000   │
│ 만기일     2027-02-05     │
│            (6/12개월)     │
└──────────────────────────┘

[parking 카드]
┌──────────────────────────┐
│ 🅿️ 토스 파킹통장          │
│    파킹통장 | 연 2.000%    │
│                          │
│ 잔액       ₩5,000,000    │
│ 일일이자    ₩274          │
│ 월예상이자  ₩6,950 (세후)  │
└──────────────────────────┘
```

**렌더링 조건**:
```typescript
const isInterestBased = ['deposit', 'savings', 'parking'].includes(holding.asset_type);
const isParking = holding.asset_type === 'parking';
```

### 2.4 AssetSummaryCard 변경

**파일**: `frontend/src/features/assets/ui/AssetSummaryCard.tsx`

- breakdown 표시에 deposit, savings, parking 라벨 자동 지원 (ASSET_TYPE_LABELS 사용)
- 변경 필요 없음 (이미 `ASSET_TYPE_LABELS[key]`로 동적 렌더링)

---

## 3. 구현 순서 (Implementation Order)

```
Step 1: Backend 모델 확장
  ├── backend/app/models/asset.py — AssetType에 3개 값 추가, InterestType enum 추가, Asset 모델 필드 8개 추가
  └── (Alembic 마이그레이션은 DB 실행 시 필요, 파일 생성은 선택)

Step 2: Backend 이자 계산 서비스
  └── backend/app/services/interest_service.py — calculate_deposit_interest, calculate_savings_interest, calculate_parking_interest

Step 3: Backend 스키마 + 서비스 확장
  ├── backend/app/schemas/asset.py — AssetCreate, AssetResponse, AssetHoldingResponse 확장
  └── backend/app/services/asset_service.py — create_asset 확장, _calculate_holding에 분기 추가

Step 4: Frontend 타입 확장
  └── frontend/src/shared/types/index.ts — AssetType, Asset, AssetCreateRequest, AssetHolding 확장, ASSET_TYPE_LABELS 추가

Step 5: Frontend UI 확장
  ├── frontend/src/features/assets/ui/AddAssetModal.tsx — 조건부 폼 추가
  ├── frontend/src/features/assets/ui/AssetCard.tsx — 이자 기반 카드 레이아웃 추가
  └── frontend/src/features/assets/ui/AssetSummaryCard.tsx — (변경 최소, 라벨만 확인)

Step 6: 빌드 검증
  └── npm run build — TypeScript 에러 없이 빌드 통과 확인
```

---

## 4. 검증 체크리스트

| ID | 항목 | 설명 |
|:---|:-----|:-----|
| **BE-1** | AssetType enum 확장 | deposit, savings, parking 3개 값 추가 |
| **BE-2** | Asset 모델 필드 추가 | interest_rate, interest_type, principal, monthly_amount, start_date, maturity_date, tax_rate, bank_name 8개 nullable 필드 |
| **BE-3** | AssetCreate 유효성 검증 | 자산 유형별 필수 필드 검증 (model_validator) |
| **BE-4** | 예금 이자 계산 | 단리/복리, 경과이자, 만기예상액 정확성 |
| **BE-5** | 적금 이자 계산 | 정액적립식 단리, 납입회차, 만기예상액 정확성 |
| **BE-6** | 파킹통장 이자 계산 | 일일이자, 월예상이자(세후) 정확성 |
| **BE-7** | 이자소득세 적용 | 15.4% 기본값, 세전/세후 구분 |
| **BE-8** | asset_service 분기 | _calculate_holding에서 deposit/savings/parking 분기 정상 동작 |
| **BE-9** | 기존 자산 호환 | 주식/금/현금 자산의 동작에 영향 없음 |
| **FE-1** | AssetType 타입 확장 | deposit, savings, parking 추가 + ASSET_TYPE_LABELS |
| **FE-2** | AddAssetModal 확장 | 유형별 조건부 폼 (deposit: 원금/이율/만기, savings: 월납/이율/만기, parking: 잔액/이율) |
| **FE-3** | AssetCard 확장 | deposit/savings: 이율/만기/경과이자, parking: 잔액/일일이자/월예상이자 |
| **FE-4** | 자산 요약 통합 | breakdown에 deposit/savings/parking 포함 |
| **FE-5** | Frontend 빌드 통과 | tsc -b && vite build 성공 |

---

## 5. 다음 단계

Design 승인 후 → `/pdca do deposit-savings` 로 구현 시작
