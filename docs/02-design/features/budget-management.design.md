# Design: Budget Management (가계부 & 예산 관리)

> **Feature**: budget-management
> **Created**: 2026-02-05
> **Plan Reference**: `docs/01-plan/features/budget-management.plan.md`
> **PDCA Phase**: Design
> **Scope**: Phase 1 ~ Phase 4 전체 (Phase 1~2 상세, Phase 3~4 개요)

---

## 1. Phase 1: Core (카테고리 + 지출 + 예산 요약)

### 1.1 Backend 모델

#### 1.1.1 PaymentMethod enum

**파일**: `backend/app/models/budget.py` (신규)

```python
class PaymentMethod(str, PyEnum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
```

#### 1.1.2 BudgetCategory 모델

**파일**: `backend/app/models/budget.py`

```python
class BudgetCategory(Base):
    __tablename__ = "budget_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    monthly_budget: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), default=Decimal("0"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="category", cascade="all, delete-orphan"
    )
```

#### 1.1.3 Expense 모델

**파일**: `backend/app/models/budget.py`

```python
class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_user_spent", "user_id", "spent_at"),
        Index("ix_expenses_user_category_spent", "user_id", "category_id", "spent_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum"), nullable=True
    )
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    spent_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    category: Mapped["BudgetCategory"] = relationship(
        "BudgetCategory", back_populates="expenses"
    )
```

**참고**: `tags`는 PRD에서 `TEXT[]`이나 PostgreSQL 배열 대신 쉼표 구분 TEXT로 간소화 (프론트엔드에서 split/join 처리).

---

### 1.2 Pydantic 스키마

**파일**: `backend/app/schemas/budget.py` (신규)

#### 1.2.1 BudgetCategory 스키마

```python
# --- Request ---

class BudgetCategoryCreate(BaseModel):
    name: str = Field(max_length=50)
    icon: str | None = Field(default=None, max_length=10)
    color: str | None = Field(default=None, max_length=7)
    monthly_budget: Decimal = Field(default=Decimal("0"), ge=0)
    sort_order: int = Field(default=0, ge=0)

class BudgetCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    icon: str | None = None
    color: str | None = None
    monthly_budget: Decimal | None = Field(default=None, ge=0)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

# --- Response ---

class BudgetCategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    icon: str | None
    color: str | None
    monthly_budget: float
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
```

#### 1.2.2 Expense 스키마

```python
class ExpenseCreate(BaseModel):
    category_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    memo: str | None = Field(default=None, max_length=500)
    payment_method: str | None = None
    tags: str | None = Field(default=None, max_length=200)
    spent_at: date

class ExpenseUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    memo: str | None = Field(default=None, max_length=500)
    payment_method: str | None = None
    tags: str | None = None
    spent_at: date | None = None

class ExpenseResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_color: str | None
    amount: float
    memo: str | None
    payment_method: str | None
    tags: str | None
    spent_at: date
    created_at: datetime
```

#### 1.2.3 Budget Summary 스키마

```python
class CategoryBudgetSummary(BaseModel):
    category_id: uuid.UUID
    category_name: str
    category_icon: str | None
    category_color: str | None
    monthly_budget: float
    spent: float
    remaining: float
    usage_rate: float  # 0~100 (%)

class BudgetSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    total_budget: float
    total_spent: float
    total_remaining: float
    total_usage_rate: float
    categories: list[CategoryBudgetSummary]
```

---

### 1.3 서비스 레이어

**파일**: `backend/app/services/budget_service.py` (신규)

#### 1.3.1 카테고리 서비스

```python
DEFAULT_CATEGORIES = [
    {"name": "식비", "icon": "🍽️", "color": "#FF6B6B", "sort_order": 0},
    {"name": "교통", "icon": "🚗", "color": "#4ECDC4", "sort_order": 1},
    {"name": "주거", "icon": "🏠", "color": "#45B7D1", "sort_order": 2},
    {"name": "문화/여가", "icon": "🎬", "color": "#96CEB4", "sort_order": 3},
    {"name": "쇼핑", "icon": "🛍️", "color": "#FFEAA7", "sort_order": 4},
    {"name": "의료", "icon": "🏥", "color": "#DDA0DD", "sort_order": 5},
    {"name": "교육", "icon": "📚", "color": "#74B9FF", "sort_order": 6},
    {"name": "저축", "icon": "💰", "color": "#00B894", "sort_order": 7},
    {"name": "기타", "icon": "📌", "color": "#B2BEC3", "sort_order": 8},
]

async def get_categories(db, user_id) -> list[BudgetCategoryResponse]:
    """카테고리 목록 조회. 없으면 기본 카테고리 자동 생성."""

async def create_category(db, user_id, data) -> BudgetCategoryResponse:
    """카테고리 추가. 동일 이름 중복 체크."""

async def update_category(db, user_id, category_id, data) -> BudgetCategoryResponse:
    """카테고리 수정."""
```

#### 1.3.2 지출 서비스

```python
async def create_expense(db, user_id, data) -> ExpenseResponse:
    """지출 기록. 카테고리 소유권 확인."""

async def get_expenses(db, user_id, category_id?, start_date?, end_date?, page, per_page) -> ExpenseListResponse:
    """지출 목록 조회. 필터 + 페이징."""

async def update_expense(db, user_id, expense_id, data) -> ExpenseResponse:
    """지출 수정."""

async def delete_expense(db, user_id, expense_id) -> None:
    """지출 삭제."""
```

#### 1.3.3 예산 요약 서비스

```python
async def get_budget_summary(db, user_id, period_start?, period_end?) -> BudgetSummaryResponse:
    """
    예산 요약: 카테고리별 예산 대비 지출 비율.
    기간 미지정 시 현재 월 (1일~말일) 기준.
    """
```

---

### 1.4 API 엔드포인트

**파일**: `backend/app/api/v1/endpoints/budget.py` (신규)

```python
router = APIRouter(prefix="/budget", tags=["budget"])

# --- Categories ---
GET    /api/v1/budget/categories          → list[BudgetCategoryResponse]
POST   /api/v1/budget/categories          → BudgetCategoryResponse (201)
PUT    /api/v1/budget/categories/{id}     → BudgetCategoryResponse

# --- Summary ---
GET    /api/v1/budget/summary?start=&end= → BudgetSummaryResponse
```

**파일**: `backend/app/api/v1/endpoints/expenses.py` (신규)

```python
router = APIRouter(prefix="/expenses", tags=["expenses"])

GET    /api/v1/expenses?category_id=&start=&end=&page=&per_page= → ExpenseListResponse
POST   /api/v1/expenses                   → ExpenseResponse (201)
PUT    /api/v1/expenses/{id}              → ExpenseResponse
DELETE /api/v1/expenses/{id}              → 204
```

**main.py 등록**:
```python
from app.api.v1.endpoints import budget, expenses
app.include_router(budget.router, prefix="/api/v1")
app.include_router(expenses.router, prefix="/api/v1")
```

---

### 1.5 Frontend 타입 확장

**파일**: `frontend/src/shared/types/index.ts`

```typescript
// 결제수단
export type PaymentMethod = 'cash' | 'card' | 'transfer';

// 기존 Budget 인터페이스를 확장/교체
export interface BudgetCategory {
  id: string;
  name: string;
  icon?: string;
  color?: string;
  monthly_budget: number;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

export interface BudgetCategoryCreateRequest {
  name: string;
  icon?: string;
  color?: string;
  monthly_budget?: number;
  sort_order?: number;
}

export interface BudgetCategoryUpdateRequest {
  name?: string;
  icon?: string;
  color?: string;
  monthly_budget?: number;
  sort_order?: number;
  is_active?: boolean;
}

export interface Expense {
  id: string;
  category_id: string;
  category_name: string;
  category_color?: string;
  amount: number;
  memo?: string;
  payment_method?: PaymentMethod;
  tags?: string;
  spent_at: string;
  created_at: string;
}

export interface ExpenseCreateRequest {
  category_id: string;
  amount: number;
  memo?: string;
  payment_method?: PaymentMethod;
  tags?: string;
  spent_at: string;
}

export interface ExpenseUpdateRequest {
  category_id?: string;
  amount?: number;
  memo?: string;
  payment_method?: PaymentMethod;
  tags?: string;
  spent_at?: string;
}

export interface CategoryBudgetSummary {
  category_id: string;
  category_name: string;
  category_icon?: string;
  category_color?: string;
  monthly_budget: number;
  spent: number;
  remaining: number;
  usage_rate: number;
}

export interface BudgetSummaryResponse {
  period_start: string;
  period_end: string;
  total_budget: number;
  total_spent: number;
  total_remaining: number;
  total_usage_rate: number;
  categories: CategoryBudgetSummary[];
}

// 결제수단 라벨
export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  cash: '현금',
  card: '카드',
  transfer: '이체',
};
```

### 1.6 Frontend API Hooks

**파일**: `frontend/src/features/budget/api/index.ts` (신규)

```typescript
// Query Keys
const budgetKeys = {
  all: ['budget'] as const,
  categories: () => [...budgetKeys.all, 'categories'] as const,
  summary: (start?: string, end?: string) => [...budgetKeys.all, 'summary', start, end] as const,
  expenses: () => [...budgetKeys.all, 'expenses'] as const,
  expenseList: (filters: Record<string, unknown>) => [...budgetKeys.expenses(), filters] as const,
};

// Hooks
useCategories()              → useQuery (GET /api/v1/budget/categories)
useCreateCategory()          → useMutation (POST /api/v1/budget/categories)
useUpdateCategory()          → useMutation (PUT /api/v1/budget/categories/{id})
useBudgetSummary(start, end) → useQuery (GET /api/v1/budget/summary)
useExpenses(filters)         → useQuery (GET /api/v1/expenses)
useCreateExpense()           → useMutation (POST /api/v1/expenses)
useUpdateExpense()           → useMutation (PUT /api/v1/expenses/{id})
useDeleteExpense()           → useMutation (DELETE /api/v1/expenses/{id})
```

### 1.7 Frontend UI 컴포넌트

**파일 구조**:
```
frontend/src/features/budget/
├── api/index.ts
└── ui/
    ├── BudgetSummaryCard.tsx       (총 예산/지출/잔여 요약)
    ├── CategoryBudgetList.tsx      (카테고리별 소진율 프로그레스 바)
    ├── ExpenseList.tsx             (지출 목록 + 필터)
    ├── AddExpenseModal.tsx         (지출 추가 모달)
    └── CategoryManager.tsx         (카테고리 관리 — 추가/수정/예산 설정)
```

**페이지 레이아웃** (`pages/budget/index.tsx`):
```
┌──────────────────────────────────┐
│ 예산 관리         [지출 추가 +]    │
├──────────────────────────────────┤
│ ┌──────────────────────────────┐ │
│ │ BudgetSummaryCard            │ │
│ │ 총 예산: ₩2,000,000         │ │
│ │ 지출: ₩850,000 (42.5%)      │ │
│ │ 잔여: ₩1,150,000            │ │
│ │ ████████░░░░░░░░░ 42.5%     │ │
│ └──────────────────────────────┘ │
│                                  │
│ ┌──────────────────────────────┐ │
│ │ CategoryBudgetList           │ │
│ │ 🍽️ 식비     ₩300K/₩500K 60%│ │
│ │ ████████████░░░░░░░░ 60%    │ │
│ │ 🚗 교통     ₩80K/₩200K  40%│ │
│ │ ████████░░░░░░░░░░░░ 40%    │ │
│ │ ...                          │ │
│ └──────────────────────────────┘ │
│                                  │
│ ┌──────────────────────────────┐ │
│ │ ExpenseList                  │ │
│ │ 2/5 🍽️ 점심식사   ₩12,000  │ │
│ │ 2/4 🚗 택시       ₩15,000  │ │
│ │ 2/4 🛍️ 온라인쇼핑 ₩35,000  │ │
│ │ ...                          │ │
│ └──────────────────────────────┘ │
│                                  │
│ [카테고리 관리]                    │
└──────────────────────────────────┘
```

---

## 2. Phase 2: 고정비 + 할부금 (상세)

### 2.1 Backend 모델

#### 2.1.1 FixedExpense 모델

**파일**: `backend/app/models/budget.py`에 추가

```python
class FixedExpense(Base):
    __tablename__ = "fixed_expenses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    payment_day: Mapped[int] = mapped_column(nullable=False)  # 1-31
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum", create_type=False), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    category: Mapped["BudgetCategory"] = relationship("BudgetCategory")
```

**참고**: `payment_method`는 Phase 1의 Expense에서 이미 `payment_method_enum`을 생성했으므로 `create_type=False`로 재사용.

#### 2.1.2 Installment 모델

**파일**: `backend/app/models/budget.py`에 추가

```python
class Installment(Base):
    __tablename__ = "installments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    payment_day: Mapped[int] = mapped_column(nullable=False)  # 1-31
    total_installments: Mapped[int] = mapped_column(nullable=False)
    paid_installments: Mapped[int] = mapped_column(default=0, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum", create_type=False), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    category: Mapped["BudgetCategory"] = relationship("BudgetCategory")
```

---

### 2.2 Pydantic 스키마

**파일**: `backend/app/schemas/budget.py`에 추가

#### 2.2.1 FixedExpense 스키마

```python
# --- FixedExpense Request ---

class FixedExpenseCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(max_length=100)
    amount: Decimal = Field(gt=0)
    payment_day: int = Field(ge=1, le=31)
    payment_method: str | None = None

class FixedExpenseUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=100)
    amount: Decimal | None = Field(default=None, gt=0)
    payment_day: int | None = Field(default=None, ge=1, le=31)
    payment_method: str | None = None
    is_active: bool | None = None

# --- FixedExpense Response ---

class FixedExpenseResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_color: str | None
    name: str
    amount: float
    payment_day: int
    payment_method: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

#### 2.2.2 Installment 스키마

```python
# --- Installment Request ---

class InstallmentCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(max_length=100)
    total_amount: Decimal = Field(gt=0)
    monthly_amount: Decimal = Field(gt=0)
    payment_day: int = Field(ge=1, le=31)
    total_installments: int = Field(gt=0)
    start_date: date
    end_date: date
    payment_method: str | None = None

class InstallmentUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=100)
    monthly_amount: Decimal | None = Field(default=None, gt=0)
    payment_day: int | None = Field(default=None, ge=1, le=31)
    payment_method: str | None = None
    is_active: bool | None = None

# --- Installment Response ---

class InstallmentResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_color: str | None
    name: str
    total_amount: float
    monthly_amount: float
    payment_day: int
    total_installments: int
    paid_installments: int
    remaining_installments: int      # 계산값: total - paid
    remaining_amount: float          # 계산값: monthly * remaining
    progress_rate: float             # 계산값: paid / total * 100
    start_date: date
    end_date: date
    payment_method: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

#### 2.2.3 BudgetSummaryResponse 확장

```python
class BudgetSummaryResponse(BaseModel):
    # 기존 필드 유지
    period_start: date
    period_end: date
    total_budget: float
    total_spent: float
    total_remaining: float
    total_usage_rate: float
    categories: list[CategoryBudgetSummary]

    # Phase 2 추가 필드
    total_fixed_expenses: float      # 활성 고정비 합계
    total_installments: float        # 활성 할부금 합계
    variable_budget: float           # total_budget - fixed - installments
    variable_spent: float            # total_spent - (이번달 고정비+할부금 지출)
    variable_remaining: float        # variable_budget - variable_spent
```

---

### 2.3 서비스 레이어

**파일**: `backend/app/services/budget_service.py`에 추가

#### 2.3.1 고정비 서비스

```python
async def get_fixed_expenses(db, user_id) -> list[FixedExpenseResponse]:
    """고정비 목록 (sort: payment_day ASC)."""

async def create_fixed_expense(db, user_id, data) -> FixedExpenseResponse:
    """고정비 추가. 카테고리 소유권 확인."""

async def update_fixed_expense(db, user_id, fe_id, data) -> FixedExpenseResponse:
    """고정비 수정."""

async def delete_fixed_expense(db, user_id, fe_id) -> None:
    """고정비 삭제."""

async def toggle_fixed_expense(db, user_id, fe_id) -> FixedExpenseResponse:
    """고정비 활성/비활성 토글."""
```

#### 2.3.2 할부금 서비스

```python
async def get_installments(db, user_id) -> list[InstallmentResponse]:
    """할부금 목록 (활성 우선, 진행률 포함)."""

async def create_installment(db, user_id, data) -> InstallmentResponse:
    """할부금 추가. 카테고리 소유권 확인."""

async def update_installment(db, user_id, inst_id, data) -> InstallmentResponse:
    """할부금 수정."""

async def delete_installment(db, user_id, inst_id) -> None:
    """할부금 삭제."""

async def get_installment_progress(db, user_id, inst_id) -> InstallmentResponse:
    """할부금 진행 상세."""
```

#### 2.3.3 예산 요약 확장

```python
async def get_budget_summary(db, user_id, period_start?, period_end?) -> BudgetSummaryResponse:
    """
    기존 로직 + 고정비/할부금 합계 계산.
    variable_budget = total_budget - total_fixed_expenses - total_installments
    """
```

---

### 2.4 API 엔드포인트

**파일**: `backend/app/api/v1/endpoints/fixed_expenses.py` (신규)

```python
router = APIRouter(prefix="/fixed-expenses", tags=["fixed-expenses"])

GET    /api/v1/fixed-expenses                  → list[FixedExpenseResponse]
POST   /api/v1/fixed-expenses                  → FixedExpenseResponse (201)
PUT    /api/v1/fixed-expenses/{id}             → FixedExpenseResponse
DELETE /api/v1/fixed-expenses/{id}             → 204
PATCH  /api/v1/fixed-expenses/{id}/toggle      → FixedExpenseResponse
```

**파일**: `backend/app/api/v1/endpoints/installments.py` (신규)

```python
router = APIRouter(prefix="/installments", tags=["installments"])

GET    /api/v1/installments                     → list[InstallmentResponse]
POST   /api/v1/installments                     → InstallmentResponse (201)
PUT    /api/v1/installments/{id}               → InstallmentResponse
DELETE /api/v1/installments/{id}               → 204
GET    /api/v1/installments/{id}/progress      → InstallmentResponse
```

**main.py 등록**:
```python
from app.api.v1.endpoints import fixed_expenses, installments
app.include_router(fixed_expenses.router, prefix="/api/v1")
app.include_router(installments.router, prefix="/api/v1")
```

---

### 2.5 Frontend 타입 확장

**파일**: `frontend/src/shared/types/index.ts`에 추가

```typescript
// 고정비
export interface FixedExpense {
  id: string;
  category_id: string;
  category_name: string;
  category_color?: string;
  name: string;
  amount: number;
  payment_day: number;
  payment_method?: PaymentMethod;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FixedExpenseCreateRequest {
  category_id: string;
  name: string;
  amount: number;
  payment_day: number;
  payment_method?: PaymentMethod;
}

export interface FixedExpenseUpdateRequest {
  category_id?: string;
  name?: string;
  amount?: number;
  payment_day?: number;
  payment_method?: PaymentMethod;
  is_active?: boolean;
}

// 할부금
export interface Installment {
  id: string;
  category_id: string;
  category_name: string;
  category_color?: string;
  name: string;
  total_amount: number;
  monthly_amount: number;
  payment_day: number;
  total_installments: number;
  paid_installments: number;
  remaining_installments: number;
  remaining_amount: number;
  progress_rate: number;
  start_date: string;
  end_date: string;
  payment_method?: PaymentMethod;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InstallmentCreateRequest {
  category_id: string;
  name: string;
  total_amount: number;
  monthly_amount: number;
  payment_day: number;
  total_installments: number;
  start_date: string;
  end_date: string;
  payment_method?: PaymentMethod;
}

export interface InstallmentUpdateRequest {
  category_id?: string;
  name?: string;
  monthly_amount?: number;
  payment_day?: number;
  payment_method?: PaymentMethod;
  is_active?: boolean;
}

// BudgetSummaryResponse 확장
export interface BudgetSummaryResponse {
  // 기존 필드 유지
  period_start: string;
  period_end: string;
  total_budget: number;
  total_spent: number;
  total_remaining: number;
  total_usage_rate: number;
  categories: CategoryBudgetSummary[];
  // Phase 2 추가
  total_fixed_expenses: number;
  total_installments: number;
  variable_budget: number;
  variable_spent: number;
  variable_remaining: number;
}
```

### 2.6 Frontend API Hooks

**파일**: `frontend/src/features/budget/api/index.ts`에 추가

```typescript
// Query Keys 확장
fixedExpenses: () => [...budgetKeys.all, 'fixedExpenses'] as const,
installments: () => [...budgetKeys.all, 'installments'] as const,

// Fixed Expense Hooks
useFixedExpenses()                → useQuery (GET /api/v1/fixed-expenses)
useCreateFixedExpense()           → useMutation (POST /api/v1/fixed-expenses)
useUpdateFixedExpense()           → useMutation (PUT /api/v1/fixed-expenses/{id})
useDeleteFixedExpense()           → useMutation (DELETE /api/v1/fixed-expenses/{id})
useToggleFixedExpense()           → useMutation (PATCH /api/v1/fixed-expenses/{id}/toggle)

// Installment Hooks
useInstallments()                 → useQuery (GET /api/v1/installments)
useCreateInstallment()            → useMutation (POST /api/v1/installments)
useUpdateInstallment()            → useMutation (PUT /api/v1/installments/{id})
useDeleteInstallment()            → useMutation (DELETE /api/v1/installments/{id})
```

### 2.7 Frontend UI 컴포넌트

**파일 구조**:
```
frontend/src/features/budget/ui/
├── (Phase 1 기존 파일)
├── FixedExpenseList.tsx          (고정비 목록 + 토글)
├── AddFixedExpenseModal.tsx      (고정비 추가 모달)
├── InstallmentList.tsx           (할부금 목록 + 진행률 바)
└── AddInstallmentModal.tsx       (할부금 추가 모달)
```

#### FixedExpenseList 레이아웃

```
┌──────────────────────────────────────┐
│ 고정비 관리           [+ 고정비 추가]  │
├──────────────────────────────────────┤
│ 🏠 월세              ₩500,000  25일  │
│    주거 | 이체          [ON] [수정]   │
│ 📺 넷플릭스           ₩17,000   1일  │
│    문화/여가 | 카드      [ON] [수정]   │
│ 📱 통신비             ₩65,000  15일  │
│    기타 | 카드          [ON] [수정]   │
│                                      │
│ 월 합계: ₩582,000                    │
└──────────────────────────────────────┘
```

#### InstallmentList 레이아웃

```
┌──────────────────────────────────────┐
│ 할부금 관리           [+ 할부금 추가]  │
├──────────────────────────────────────┤
│ 🧊 LG 냉장고 할부    ₩150,000/월    │
│   쇼핑 | 카드 | 10일                  │
│   ████████████░░░░░ 8/12개월 (66.7%) │
│   총 ₩1,800,000 | 남은 ₩600,000     │
│                                      │
│ 🚗 자동차 할부        ₩350,000/월    │
│   교통 | 이체 | 5일                   │
│   ████░░░░░░░░░░░░░ 12/36개월 (33%) │
│   총 ₩12,600,000 | 남은 ₩8,400,000  │
│                                      │
│ 월 합계: ₩500,000                    │
└──────────────────────────────────────┘
```

#### BudgetSummaryCard 확장

```
┌──────────────────────────────────────┐
│ 2026-02-01 ~ 2026-02-28             │
│                                      │
│ 총 예산     지출      잔여            │
│ ₩2,000,000 ₩850,000 ₩1,150,000     │
│ ████████░░░░░░░░░░ 42.5%            │
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ 고정비: -₩582,000               │ │
│ │ 할부금: -₩500,000               │ │
│ │ 가변 예산: ₩918,000             │ │
│ │ 가변 지출: ₩268,000 (29.2%)     │ │
│ │ 가변 잔여: ₩650,000             │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

#### 페이지 레이아웃 확장 (`pages/budget/index.tsx`)

```
┌──────────────────────────────────────┐
│ 예산 관리               [지출 추가 +] │
├──────────────────────────────────────┤
│ BudgetSummaryCard (확장)             │
│ CategoryBudgetList                   │
│                                      │
│ ─── 탭: [지출내역] [고정비] [할부금] ─│
│                                      │
│ (탭별 콘텐츠)                         │
│ - 지출내역: ExpenseList              │
│ - 고정비: FixedExpenseList           │
│ - 할부금: InstallmentList            │
│                                      │
│ [카테고리 관리]                       │
└──────────────────────────────────────┘
```

---

### 2.8 구현 순서 (Phase 2)

```
Step 1: Backend 모델 — FixedExpense, Installment (budget.py에 추가)

Step 2: Backend 스키마 — Create/Update/Response (schemas/budget.py에 추가)

Step 3: Backend 서비스 — 고정비 CRUD, 할부금 CRUD, 예산 요약 확장 (budget_service.py에 추가)

Step 4: Backend API 라우터
  ├── api/v1/endpoints/fixed_expenses.py (신규)
  ├── api/v1/endpoints/installments.py (신규)
  └── main.py — 라우터 등록

Step 5: Frontend 타입 + API hooks
  ├── shared/types/index.ts — 타입 추가 + BudgetSummaryResponse 확장
  └── features/budget/api/index.ts — hooks 추가

Step 6: Frontend UI
  ├── features/budget/ui/FixedExpenseList.tsx + AddFixedExpenseModal.tsx
  ├── features/budget/ui/InstallmentList.tsx + AddInstallmentModal.tsx
  ├── features/budget/ui/BudgetSummaryCard.tsx 수정 (가변예산 표시)
  └── pages/budget/index.tsx 수정 (탭 추가)

Step 7: 빌드 검증
  └── npm run build
```

---

### 2.9 검증 체크리스트 (Phase 2)

| ID | 항목 | 설명 |
|:---|:-----|:-----|
| **P2-BE-1** | FixedExpense 모델 | category_id FK, name, amount, payment_day, payment_method, is_active, updated_at |
| **P2-BE-2** | Installment 모델 | category_id FK, name, total/monthly amount, payment_day, total/paid installments, start/end date, updated_at |
| **P2-BE-3** | 고정비 CRUD + 토글 | 목록, 추가(카테고리 소유권), 수정, 삭제, 토글 |
| **P2-BE-4** | 할부금 CRUD + 진행률 | 목록(진행률 계산값 포함), 추가, 수정, 삭제, progress 조회 |
| **P2-BE-5** | 예산 요약 확장 | total_fixed_expenses, total_installments, variable_budget/spent/remaining |
| **P2-BE-6** | API 엔드포인트 10개 | fixed-expenses(5) + installments(5) = 10개 |
| **P2-BE-7** | main.py 라우터 등록 | fixed_expenses + installments 라우터 등록 |
| **P2-FE-1** | 타입 확장 | FixedExpense, Installment, BudgetSummaryResponse 확장 |
| **P2-FE-2** | API hooks 9개 | useFixedExpenses 등 5 + useInstallments 등 4 |
| **P2-FE-3** | FixedExpenseList + AddFixedExpenseModal | 고정비 목록(토글/합계) + 추가 모달 |
| **P2-FE-4** | InstallmentList + AddInstallmentModal | 할부금 목록(진행률 바/합계) + 추가 모달 |
| **P2-FE-5** | BudgetSummaryCard 확장 | 고정비/할부금 차감, 가변예산/가변지출/가변잔여 표시 |
| **P2-FE-6** | budget 페이지 탭 추가 | 지출내역/고정비/할부금 3탭 전환 |
| **P2-FE-7** | Frontend 빌드 통과 | tsc -b && vite build 성공 |

---

## 3. Phase 3: 수입 + 이월 정책 (개요)

### 3.1 Backend 모델

#### Income 모델
**파일**: `backend/app/models/budget.py`에 추가

```python
class IncomeType(str, PyEnum):
    SALARY = "salary"
    SIDE = "side"
    INVESTMENT = "investment"
    OTHER = "other"

class Income(Base):
    __tablename__ = "incomes"
    # id, user_id, type(IncomeType), amount, description,
    # is_recurring, recurring_day(nullable), received_at, created_at
```

#### CarryoverType enum + BudgetCarryoverSetting 모델
```python
class CarryoverType(str, PyEnum):
    EXPIRE = "expire"
    NEXT_MONTH = "next_month"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    DEPOSIT = "deposit"

class BudgetCarryoverSetting(Base):
    __tablename__ = "budget_carryover_settings"
    # id, user_id, category_id(FK, UNIQUE with user_id),
    # carryover_type, carryover_limit(nullable), target_asset_id(FK nullable),
    # target_savings_name(nullable), target_annual_rate(nullable), created_at, updated_at
```

#### BudgetCarryoverLog 모델
```python
class BudgetCarryoverLog(Base):
    __tablename__ = "budget_carryover_logs"
    # id, user_id, category_id(FK), budget_period_start, budget_period_end,
    # carryover_type, amount, target_description, executed_at, created_at
```

### 3.2 API 엔드포인트

```
Incomes:
  GET    /api/v1/incomes
  POST   /api/v1/incomes
  PUT    /api/v1/incomes/{id}
  DELETE /api/v1/incomes/{id}

Carryover:
  GET    /api/v1/budget/carryover/settings
  PUT    /api/v1/budget/carryover/settings/{category_id}
  GET    /api/v1/budget/carryover/logs
  GET    /api/v1/budget/carryover/preview
```

---

## 4. Phase 4: 월급일 전환 + 예산 분석 (개요)

### 4.1 예산 기간 계산

```python
def get_budget_period(payday: int, target_date: date) -> tuple[date, date]:
    """
    월급일 기준 예산 기간 계산.
    payday=25, target_date=2026-02-10 → (2026-01-25, 2026-02-24)
    """

def get_transition_period(payday: int, target_date: date) -> tuple[date, date] | None:
    """
    전환 기간 (payday 전후 1주) 계산.
    None이면 전환 기간 아님.
    """
```

### 4.2 분석 API

```
GET /api/v1/budget/summary?period=     → 예산 기간별 요약 (급여일 기준)
GET /api/v1/budget/transition          → 전환 기간 데이터
GET /api/v1/budget/analysis            → 예산 분석 (일별 가용, 주별, 소진율)
```

### 4.3 분석 응답 스키마

```python
class BudgetAnalysisResponse(BaseModel):
    daily_available: float          # 일별 사용 가능 금액
    weekly_budget: float            # 주간 평균 예산
    weekly_spent: float             # 이번 주 사용
    days_remaining: int             # 남은 일수
    category_usage: list[CategoryBudgetSummary]
    carryover_forecast: float       # 이월 예측 금액
```

---

## 5. 구현 순서 (Phase 1 상세)

```
Step 1: Backend 모델 (budget_categories, expenses)
  └── backend/app/models/budget.py — BudgetCategory, Expense, PaymentMethod enum

Step 2: Backend 스키마
  └── backend/app/schemas/budget.py — Create/Update/Response for Category, Expense, Summary

Step 3: Backend 서비스
  └── backend/app/services/budget_service.py — CRUD + 기본 카테고리 자동 생성 + 예산 요약

Step 4: Backend API 라우터
  ├── backend/app/api/v1/endpoints/budget.py — categories + summary
  ├── backend/app/api/v1/endpoints/expenses.py — expenses CRUD
  └── backend/app/main.py — 라우터 등록

Step 5: Frontend 타입 + API
  ├── frontend/src/shared/types/index.ts — 타입 확장 (Budget → BudgetCategory, Expense 등)
  └── frontend/src/features/budget/api/index.ts — React Query hooks

Step 6: Frontend UI
  ├── frontend/src/features/budget/ui/BudgetSummaryCard.tsx
  ├── frontend/src/features/budget/ui/CategoryBudgetList.tsx
  ├── frontend/src/features/budget/ui/ExpenseList.tsx
  ├── frontend/src/features/budget/ui/AddExpenseModal.tsx
  ├── frontend/src/features/budget/ui/CategoryManager.tsx
  └── frontend/src/pages/budget/index.tsx — 페이지 레이아웃 재구성

Step 7: 빌드 검증
  └── npm run build
```

---

## 6. 검증 체크리스트 (Phase 1)

| ID | 항목 | 설명 |
|:---|:-----|:-----|
| **BE-1** | BudgetCategory 모델 | name, icon, color, monthly_budget, sort_order, is_active 필드 |
| **BE-2** | Expense 모델 | category_id FK, amount, memo, payment_method, tags, spent_at + 인덱스 |
| **BE-3** | PaymentMethod enum | cash, card, transfer |
| **BE-4** | 카테고리 CRUD | 목록(자동생성 포함), 추가(중복 체크), 수정 |
| **BE-5** | 지출 CRUD | 추가(카테고리 소유권 확인), 목록(필터+페이징), 수정, 삭제 |
| **BE-6** | 예산 요약 | 카테고리별 budget/spent/remaining/usage_rate 계산 |
| **BE-7** | 기본 카테고리 자동 생성 | 9개 기본 카테고리 (식비~기타) |
| **BE-8** | API 엔드포인트 | budget/categories(3), expenses(4), budget/summary(1) = 8개 |
| **BE-9** | main.py 라우터 등록 | budget + expenses 라우터 등록 |
| **FE-1** | 타입 확장 | BudgetCategory, Expense, BudgetSummaryResponse 등 |
| **FE-2** | API hooks | useCategories, useExpenses, useBudgetSummary 등 8개 |
| **FE-3** | BudgetSummaryCard | 총 예산/지출/잔여 + 프로그레스 바 |
| **FE-4** | CategoryBudgetList | 카테고리별 소진율 프로그레스 바 |
| **FE-5** | ExpenseList + AddExpenseModal | 지출 목록 + 추가 모달 |
| **FE-6** | CategoryManager | 카테고리 추가/수정/예산 설정 |
| **FE-7** | budget 페이지 재구성 | 스텁 → 실제 레이아웃 |
| **FE-8** | Frontend 빌드 통과 | tsc -b && vite build 성공 |

---

## 7. 다음 단계

- Phase 1: ✅ 완료 (Match Rate 97%, 18/18 PASS)
- Phase 2: Design 완료 → `/pdca do budget-management` 로 Phase 2 구현 시작
- Phase 2 완료 후 → Phase 3 Design 상세화 → Do → Check 반복
