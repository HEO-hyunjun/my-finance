import uuid
from calendar import monthrange
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.budget import BudgetCategory, Expense, FixedExpense, Installment
from app.models.user import User
from app.services.budget_period import get_budget_period
from app.schemas.budget import (
    BudgetCategoryCreate,
    BudgetCategoryUpdate,
    BudgetCategoryResponse,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseListResponse,
    CategoryBudgetSummary,
    BudgetSummaryResponse,
    FixedExpenseCreate,
    FixedExpenseUpdate,
    FixedExpenseResponse,
    InstallmentCreate,
    InstallmentUpdate,
    InstallmentResponse,
)


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


def _category_to_response(cat: BudgetCategory) -> BudgetCategoryResponse:
    return BudgetCategoryResponse(
        id=cat.id,
        name=cat.name,
        icon=cat.icon,
        color=cat.color,
        monthly_budget=float(cat.monthly_budget),
        sort_order=cat.sort_order,
        is_active=cat.is_active,
        created_at=cat.created_at,
    )


def _fixed_expense_to_response(
    fe: FixedExpense, category: BudgetCategory, source_asset_name: str | None = None
) -> FixedExpenseResponse:
    return FixedExpenseResponse(
        id=fe.id,
        category_id=fe.category_id,
        category_name=category.name,
        category_color=category.color,
        name=fe.name,
        amount=float(fe.amount),
        payment_day=fe.payment_day,
        source_asset_id=fe.source_asset_id,
        source_asset_name=source_asset_name,
        is_active=fe.is_active,
        created_at=fe.created_at,
        updated_at=fe.updated_at,
    )


def _installment_to_response(
    inst: Installment, category: BudgetCategory, source_asset_name: str | None = None
) -> InstallmentResponse:
    remaining = inst.total_installments - inst.paid_installments
    return InstallmentResponse(
        id=inst.id,
        category_id=inst.category_id,
        category_name=category.name,
        category_color=category.color,
        name=inst.name,
        total_amount=float(inst.total_amount),
        monthly_amount=float(inst.monthly_amount),
        payment_day=inst.payment_day,
        total_installments=inst.total_installments,
        paid_installments=inst.paid_installments,
        remaining_installments=remaining,
        remaining_amount=float(inst.monthly_amount) * remaining,
        progress_rate=round(
            inst.paid_installments / inst.total_installments * 100, 1
        )
        if inst.total_installments > 0
        else 0.0,
        start_date=inst.start_date,
        end_date=inst.end_date,
        source_asset_id=inst.source_asset_id,
        source_asset_name=source_asset_name,
        is_active=inst.is_active,
        created_at=inst.created_at,
        updated_at=inst.updated_at,
    )


ALLOWED_SOURCE_TYPES = {AssetType.CASH_KRW, AssetType.DEPOSIT, AssetType.PARKING}


async def _validate_source_asset(
    db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID
) -> Asset:
    asset = await db.get(Asset, asset_id)
    if not asset or asset.user_id != user_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.asset_type not in ALLOWED_SOURCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Asset type '{asset.asset_type.value}' is not allowed for expense linking",
        )
    return asset


async def _adjust_asset_principal(asset: Asset, delta: Decimal) -> None:
    if asset.asset_type == AssetType.CASH_KRW:
        # cash_krw: 잔액은 거래+지출+수입에서 동적 계산 → principal 조정 불필요
        return

    current = Decimal(str(asset.principal)) if asset.principal else Decimal("0")
    new_val = current + delta
    if new_val < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance: {asset.name} (current: {current}, required: {abs(delta)})",
        )
    asset.principal = new_val


def _expense_to_response(
    exp: Expense, category: BudgetCategory, source_asset_name: str | None = None
) -> ExpenseResponse:
    return ExpenseResponse(
        id=exp.id,
        category_id=exp.category_id,
        category_name=category.name,
        category_color=category.color,
        amount=float(exp.amount),
        memo=exp.memo,
        source_asset_id=exp.source_asset_id,
        source_asset_name=source_asset_name,
        spent_at=exp.spent_at,
        created_at=exp.created_at,
    )


# ──────────────────────────────────────────────
# Category CRUD
# ──────────────────────────────────────────────


async def _ensure_default_categories(
    db: AsyncSession, user_id: uuid.UUID
) -> None:
    """사용자에게 카테고리가 없으면 기본 카테고리를 자동 생성한다."""
    count_stmt = select(func.count()).where(BudgetCategory.user_id == user_id)
    count = (await db.execute(count_stmt)).scalar() or 0
    if count > 0:
        return

    for cat_data in DEFAULT_CATEGORIES:
        cat = BudgetCategory(user_id=user_id, **cat_data)
        db.add(cat)
    await db.commit()


async def get_categories(
    db: AsyncSession, user_id: uuid.UUID
) -> list[BudgetCategoryResponse]:
    await _ensure_default_categories(db, user_id)

    stmt = (
        select(BudgetCategory)
        .where(BudgetCategory.user_id == user_id)
        .order_by(BudgetCategory.sort_order)
    )
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return [_category_to_response(c) for c in categories]


async def create_category(
    db: AsyncSession, user_id: uuid.UUID, data: BudgetCategoryCreate
) -> BudgetCategoryResponse:
    # 동일 이름 중복 체크
    dup_stmt = select(BudgetCategory).where(
        BudgetCategory.user_id == user_id,
        BudgetCategory.name == data.name,
    )
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400, detail=f"Category '{data.name}' already exists"
        )

    cat = BudgetCategory(
        user_id=user_id,
        name=data.name,
        icon=data.icon,
        color=data.color,
        monthly_budget=data.monthly_budget,
        sort_order=data.sort_order,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return _category_to_response(cat)


async def update_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    data: BudgetCategoryUpdate,
) -> BudgetCategoryResponse:
    cat = await _get_user_category(db, user_id, category_id)
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(cat, field, value)

    await db.commit()
    await db.refresh(cat)
    return _category_to_response(cat)


# ──────────────────────────────────────────────
# Expense CRUD
# ──────────────────────────────────────────────


async def create_expense(
    db: AsyncSession, user_id: uuid.UUID, data: ExpenseCreate
) -> ExpenseResponse:
    category = await _get_user_category(db, user_id, data.category_id)

    source_asset_name: str | None = None
    if data.source_asset_id:
        asset = await _validate_source_asset(db, user_id, data.source_asset_id)
        await _adjust_asset_principal(asset, -data.amount)
        source_asset_name = asset.name

    exp = Expense(
        user_id=user_id,
        category_id=data.category_id,
        amount=data.amount,
        memo=data.memo,
        spent_at=data.spent_at,
        source_asset_id=data.source_asset_id,
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return _expense_to_response(exp, category, source_asset_name)


async def get_expenses(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    per_page: int = 20,
    memo: str | None = None,
) -> ExpenseListResponse:
    # 조회 기간 내 고정비 자동 Expense 보장
    if start_date and end_date:
        await _ensure_auto_expenses_for_range(db, user_id, start_date, end_date)
    elif not start_date and not end_date:
        ps, pe = await _get_current_period_for_user(db, user_id)
        await _ensure_auto_expenses_for_range(db, user_id, ps, pe)

    base = select(Expense).where(Expense.user_id == user_id)

    if category_id:
        base = base.where(Expense.category_id == category_id)
    if start_date:
        base = base.where(Expense.spent_at >= start_date)
    if end_date:
        base = base.where(Expense.spent_at <= end_date)
    if memo:
        for word in memo.split():
            base = base.where(Expense.memo.ilike(f"%{word}%"))

    # 총 개수
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # 페이지네이션
    offset = (page - 1) * per_page
    stmt = base.order_by(Expense.spent_at.desc(), Expense.created_at.desc()).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    expenses = result.scalars().all()

    # 단일 IN 쿼리로 필요한 모든 카테고리를 한번에 조회
    cat_ids = {exp.category_id for exp in expenses}
    category_cache: dict[uuid.UUID, BudgetCategory] = {}
    if cat_ids:
        cat_stmt = select(BudgetCategory).where(BudgetCategory.id.in_(cat_ids))
        cats = (await db.execute(cat_stmt)).scalars().all()
        category_cache = {cat.id: cat for cat in cats}

    # 자산 이름 조회
    asset_ids = {exp.source_asset_id for exp in expenses if exp.source_asset_id}
    asset_cache: dict[uuid.UUID, str] = {}
    if asset_ids:
        asset_stmt = select(Asset.id, Asset.name).where(Asset.id.in_(asset_ids))
        asset_rows = (await db.execute(asset_stmt)).all()
        asset_cache = {row.id: row.name for row in asset_rows}

    responses = []
    for exp in expenses:
        cat = category_cache.get(exp.category_id)
        if cat:
            asset_name = asset_cache.get(exp.source_asset_id) if exp.source_asset_id else None
            responses.append(_expense_to_response(exp, cat, asset_name))

    return ExpenseListResponse(
        data=responses,
        total=total,
        page=page,
        per_page=per_page,
    )


async def update_expense(
    db: AsyncSession,
    user_id: uuid.UUID,
    expense_id: uuid.UUID,
    data: ExpenseUpdate,
) -> ExpenseResponse:
    exp = await _get_user_expense(db, user_id, expense_id)
    update_data = data.model_dump(exclude_unset=True)

    # 카테고리 변경 시 소유권 확인
    if "category_id" in update_data:
        await _get_user_category(db, user_id, update_data["category_id"])

    # 자산 연동 처리
    old_asset_id = exp.source_asset_id
    new_asset_id = update_data.get("source_asset_id", old_asset_id)
    old_amount = exp.amount
    new_amount = update_data.get("amount", old_amount)

    # 기존 자산 복원
    if old_asset_id:
        old_asset = await db.get(Asset, old_asset_id)
        if old_asset:
            await _adjust_asset_principal(old_asset, Decimal(str(old_amount)))

    # 새 자산 차감
    if new_asset_id:
        new_asset = await _validate_source_asset(db, user_id, new_asset_id)
        await _adjust_asset_principal(new_asset, -Decimal(str(new_amount)))

    for field, value in update_data.items():
        setattr(exp, field, value)

    await db.commit()
    await db.refresh(exp)
    category = await db.get(BudgetCategory, exp.category_id)
    source_asset_name = None
    if exp.source_asset_id:
        sa = await db.get(Asset, exp.source_asset_id)
        source_asset_name = sa.name if sa else None
    return _expense_to_response(exp, category, source_asset_name)


async def delete_expense(
    db: AsyncSession, user_id: uuid.UUID, expense_id: uuid.UUID
) -> None:
    exp = await _get_user_expense(db, user_id, expense_id)

    # 자산 잔액 복원
    if exp.source_asset_id:
        asset = await db.get(Asset, exp.source_asset_id)
        if asset:
            await _adjust_asset_principal(asset, Decimal(str(exp.amount)))

    await db.delete(exp)
    await db.commit()


# ──────────────────────────────────────────────
# Budget Summary
# ──────────────────────────────────────────────


async def get_budget_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
    salary_day: int = 1,
) -> BudgetSummaryResponse:
    # 기간 미지정 시 급여일 기준 예산 기간 계산
    today = date.today()
    if not period_start or not period_end:
        period_start, period_end = get_budget_period(today, salary_day)

    # 조회 기간 내 고정비 자동 Expense 보장
    await _ensure_auto_expenses_for_range(db, user_id, period_start, period_end)

    # 카테고리 목록 (기본 카테고리는 get_categories에서 자동 생성)
    stmt = (
        select(BudgetCategory)
        .where(BudgetCategory.user_id == user_id, BudgetCategory.is_active.is_(True))
        .order_by(BudgetCategory.sort_order)
    )
    result = await db.execute(stmt)
    categories = result.scalars().all()

    category_summaries: list[CategoryBudgetSummary] = []
    total_budget = 0.0
    total_spent = 0.0

    # 단일 GROUP BY 쿼리로 모든 카테고리의 지출 합계를 한번에 조회
    spent_stmt = (
        select(
            Expense.category_id,
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
        )
        .where(
            Expense.user_id == user_id,
            Expense.category_id.in_([cat.id for cat in categories]),
            Expense.spent_at >= period_start,
            Expense.spent_at <= period_end,
        )
        .group_by(Expense.category_id)
    )
    spent_result = await db.execute(spent_stmt)
    spending_map = {row.category_id: float(row.total) for row in spent_result.all()}

    for cat in categories:
        # 해당 카테고리의 기간 내 지출 합계
        spent = spending_map.get(cat.id, 0.0)
        budget = float(cat.monthly_budget)
        remaining = budget - spent
        usage_rate = (spent / budget * 100) if budget > 0 else 0.0

        category_summaries.append(
            CategoryBudgetSummary(
                category_id=cat.id,
                category_name=cat.name,
                category_icon=cat.icon,
                category_color=cat.color,
                monthly_budget=budget,
                spent=spent,
                remaining=remaining,
                usage_rate=round(usage_rate, 1),
            )
        )

        total_budget += budget
        total_spent += spent

    total_remaining = total_budget - total_spent
    total_usage_rate = (total_spent / total_budget * 100) if total_budget > 0 else 0.0

    # Phase 2: 고정비 + 할부금 합계
    fe_stmt = select(func.coalesce(func.sum(FixedExpense.amount), 0)).where(
        FixedExpense.user_id == user_id, FixedExpense.is_active.is_(True)
    )
    total_fixed = float((await db.execute(fe_stmt)).scalar() or 0)

    inst_stmt = select(func.coalesce(func.sum(Installment.monthly_amount), 0)).where(
        Installment.user_id == user_id, Installment.is_active.is_(True)
    )
    total_inst = float((await db.execute(inst_stmt)).scalar() or 0)

    # 고정비 자동 Expense 합계 (fixed_expense_id IS NOT NULL)
    auto_fixed_stmt = (
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.user_id == user_id,
            Expense.fixed_expense_id.isnot(None),
            Expense.spent_at >= period_start,
            Expense.spent_at <= period_end,
        )
    )
    total_auto_fixed_spent = float((await db.execute(auto_fixed_stmt)).scalar() or 0)

    variable_budget = total_budget - total_fixed - total_inst
    variable_spent = total_spent - total_auto_fixed_spent
    variable_remaining = variable_budget - variable_spent

    return BudgetSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        total_budget=total_budget,
        total_spent=total_spent,
        total_remaining=total_remaining,
        total_usage_rate=round(total_usage_rate, 1),
        categories=category_summaries,
        total_fixed_expenses=total_fixed,
        total_installments=total_inst,
        variable_budget=variable_budget,
        variable_spent=variable_spent,
        variable_remaining=variable_remaining,
    )


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


async def _get_current_period_for_user(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[date, date]:
    """User.salary_day 기반 현재 예산 기간 반환."""
    user = await db.get(User, user_id)
    salary_day = user.salary_day if user else 1
    return get_budget_period(date.today(), salary_day)


async def _ensure_auto_expenses_for_range(
    db: AsyncSession, user_id: uuid.UUID,
    range_start: date, range_end: date,
) -> None:
    """기간 내 활성 고정비에 대한 자동 Expense를 누락 시 생성한다."""
    stmt = select(FixedExpense).where(
        FixedExpense.user_id == user_id,
        FixedExpense.is_active.is_(True),
    )
    fixed_expenses = (await db.execute(stmt)).scalars().all()
    if not fixed_expenses:
        return

    # 기간 내 포함된 월 목록
    months: list[tuple[int, int]] = []
    cur = range_start.replace(day=1)
    end_month = range_end.replace(day=1)
    while cur <= end_month:
        months.append((cur.year, cur.month))
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)

    # 이미 존재하는 자동 Expense (고정비ID, 년, 월) 조회
    fe_ids = [fe.id for fe in fixed_expenses]
    existing_stmt = select(
        Expense.fixed_expense_id,
        extract("year", Expense.spent_at).label("y"),
        extract("month", Expense.spent_at).label("m"),
    ).where(
        Expense.fixed_expense_id.in_(fe_ids),
        Expense.spent_at >= range_start,
        Expense.spent_at <= range_end,
    )
    existing = set(
        (row[0], int(row[1]), int(row[2]))
        for row in (await db.execute(existing_stmt)).all()
    )

    # 누락된 자동 Expense 생성
    new_expenses = []
    for fe in fixed_expenses:
        for year, month in months:
            if (fe.id, year, month) in existing:
                continue
            _, last_day = monthrange(year, month)
            pay_day = last_day if fe.payment_day == 0 else min(fe.payment_day, last_day)
            spent_at = date(year, month, pay_day)
            if spent_at < range_start or spent_at > range_end:
                continue
            new_expenses.append(Expense(
                user_id=user_id,
                category_id=fe.category_id,
                amount=fe.amount,
                memo=f"[고정] {fe.name}",
                source_asset_id=fe.source_asset_id,
                fixed_expense_id=fe.id,
                spent_at=spent_at,
            ))

    if new_expenses:
        db.add_all(new_expenses)
        await db.flush()


async def _upsert_auto_expense_for_fixed(
    db: AsyncSession, fe: FixedExpense, period_start: date
) -> None:
    """고정비에 대한 자동 Expense를 upsert (insert or update). 현재 기간용."""
    # 같은 월에 이미 존재하는 자동 Expense 조회
    stmt = select(Expense).where(
        Expense.fixed_expense_id == fe.id,
        extract("year", Expense.spent_at) == period_start.year,
        extract("month", Expense.spent_at) == period_start.month,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    _, last_day = monthrange(period_start.year, period_start.month)
    pay_day = last_day if fe.payment_day == 0 else min(fe.payment_day, last_day)
    spent_at = date(period_start.year, period_start.month, pay_day)

    if existing:
        existing.amount = fe.amount
        existing.category_id = fe.category_id
        existing.source_asset_id = fe.source_asset_id
        existing.memo = f"[고정] {fe.name}"
        existing.spent_at = spent_at
    else:
        expense = Expense(
            user_id=fe.user_id,
            category_id=fe.category_id,
            amount=fe.amount,
            memo=f"[고정] {fe.name}",
            source_asset_id=fe.source_asset_id,
            fixed_expense_id=fe.id,
            spent_at=spent_at,
        )
        db.add(expense)


async def _delete_auto_expense_for_fixed(
    db: AsyncSession, fe_id: uuid.UUID, period_start: date
) -> None:
    """현재 기간(월)의 자동 Expense를 삭제."""
    stmt = select(Expense).where(
        Expense.fixed_expense_id == fe_id,
        extract("year", Expense.spent_at) == period_start.year,
        extract("month", Expense.spent_at) == period_start.month,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        await db.delete(existing)


async def _get_user_category(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID
) -> BudgetCategory:
    stmt = select(BudgetCategory).where(
        BudgetCategory.id == category_id, BudgetCategory.user_id == user_id
    )
    cat = (await db.execute(stmt)).scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


async def _get_user_expense(
    db: AsyncSession, user_id: uuid.UUID, expense_id: uuid.UUID
) -> Expense:
    stmt = select(Expense).where(
        Expense.id == expense_id, Expense.user_id == user_id
    )
    exp = (await db.execute(stmt)).scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Expense not found")
    return exp


async def _get_user_fixed_expense(
    db: AsyncSession, user_id: uuid.UUID, fe_id: uuid.UUID
) -> FixedExpense:
    stmt = select(FixedExpense).where(
        FixedExpense.id == fe_id, FixedExpense.user_id == user_id
    )
    fe = (await db.execute(stmt)).scalar_one_or_none()
    if not fe:
        raise HTTPException(status_code=404, detail="Fixed expense not found")
    return fe


async def _get_user_installment(
    db: AsyncSession, user_id: uuid.UUID, inst_id: uuid.UUID
) -> Installment:
    stmt = select(Installment).where(
        Installment.id == inst_id, Installment.user_id == user_id
    )
    inst = (await db.execute(stmt)).scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Installment not found")
    return inst


# ──────────────────────────────────────────────
# Fixed Expense CRUD
# ──────────────────────────────────────────────


async def get_fixed_expenses(
    db: AsyncSession, user_id: uuid.UUID
) -> list[FixedExpenseResponse]:
    stmt = (
        select(FixedExpense)
        .where(FixedExpense.user_id == user_id)
        .order_by(FixedExpense.payment_day)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    # 단일 IN 쿼리로 필요한 모든 카테고리를 한번에 조회
    cat_ids = {fe.category_id for fe in items}
    cat_cache: dict[uuid.UUID, BudgetCategory] = {}
    if cat_ids:
        cat_stmt = select(BudgetCategory).where(BudgetCategory.id.in_(cat_ids))
        cats = (await db.execute(cat_stmt)).scalars().all()
        cat_cache = {cat.id: cat for cat in cats}

    # 출금 자산명 일괄 조회
    asset_ids = {fe.source_asset_id for fe in items if fe.source_asset_id}
    asset_cache: dict[uuid.UUID, str] = {}
    if asset_ids:
        asset_stmt = select(Asset).where(Asset.id.in_(asset_ids))
        assets = (await db.execute(asset_stmt)).scalars().all()
        asset_cache = {a.id: a.name for a in assets}

    responses = []
    for fe in items:
        cat = cat_cache.get(fe.category_id)
        if cat:
            asset_name = asset_cache.get(fe.source_asset_id) if fe.source_asset_id else None
            responses.append(_fixed_expense_to_response(fe, cat, asset_name))
    return responses


async def create_fixed_expense(
    db: AsyncSession, user_id: uuid.UUID, data: FixedExpenseCreate
) -> FixedExpenseResponse:
    category = await _get_user_category(db, user_id, data.category_id)

    if data.source_asset_id:
        await _validate_source_asset(db, user_id, data.source_asset_id)

    fe = FixedExpense(
        user_id=user_id,
        category_id=data.category_id,
        name=data.name,
        amount=data.amount,
        payment_day=data.payment_day,
        source_asset_id=data.source_asset_id,
    )
    db.add(fe)
    await db.flush()

    # 자동 Expense 생성
    period_start, _ = await _get_current_period_for_user(db, user_id)
    await _upsert_auto_expense_for_fixed(db, fe, period_start)

    await db.commit()
    await db.refresh(fe)
    asset_name = None
    if fe.source_asset_id:
        asset = await db.get(Asset, fe.source_asset_id)
        asset_name = asset.name if asset else None
    return _fixed_expense_to_response(fe, category, asset_name)


async def update_fixed_expense(
    db: AsyncSession,
    user_id: uuid.UUID,
    fe_id: uuid.UUID,
    data: FixedExpenseUpdate,
) -> FixedExpenseResponse:
    fe = await _get_user_fixed_expense(db, user_id, fe_id)
    update_data = data.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        await _get_user_category(db, user_id, update_data["category_id"])

    if "source_asset_id" in update_data and update_data["source_asset_id"]:
        await _validate_source_asset(db, user_id, update_data["source_asset_id"])

    for field, value in update_data.items():
        setattr(fe, field, value)

    # 자동 Expense 동기화 (amount/category/source_asset 변경 시)
    if fe.is_active:
        period_start, _ = await _get_current_period_for_user(db, user_id)
        await _upsert_auto_expense_for_fixed(db, fe, period_start)

    await db.commit()
    await db.refresh(fe)
    category = await db.get(BudgetCategory, fe.category_id)
    asset_name = None
    if fe.source_asset_id:
        asset = await db.get(Asset, fe.source_asset_id)
        asset_name = asset.name if asset else None
    return _fixed_expense_to_response(fe, category, asset_name)


async def delete_fixed_expense(
    db: AsyncSession, user_id: uuid.UUID, fe_id: uuid.UUID
) -> None:
    fe = await _get_user_fixed_expense(db, user_id, fe_id)

    # 현재 기간의 자동 Expense 삭제
    period_start, _ = await _get_current_period_for_user(db, user_id)
    await _delete_auto_expense_for_fixed(db, fe.id, period_start)

    await db.delete(fe)
    await db.commit()


async def toggle_fixed_expense(
    db: AsyncSession, user_id: uuid.UUID, fe_id: uuid.UUID
) -> FixedExpenseResponse:
    fe = await _get_user_fixed_expense(db, user_id, fe_id)
    fe.is_active = not fe.is_active

    period_start, _ = await _get_current_period_for_user(db, user_id)
    if fe.is_active:
        # 활성화 → 자동 Expense 생성
        await _upsert_auto_expense_for_fixed(db, fe, period_start)
    else:
        # 비활성화 → 현재 기간 자동 Expense 삭제
        await _delete_auto_expense_for_fixed(db, fe.id, period_start)

    await db.commit()
    await db.refresh(fe)
    category = await db.get(BudgetCategory, fe.category_id)
    asset_name = None
    if fe.source_asset_id:
        asset = await db.get(Asset, fe.source_asset_id)
        asset_name = asset.name if asset else None
    return _fixed_expense_to_response(fe, category, asset_name)


# ──────────────────────────────────────────────
# Installment CRUD
# ──────────────────────────────────────────────


async def get_installments(
    db: AsyncSession, user_id: uuid.UUID
) -> list[InstallmentResponse]:
    stmt = (
        select(Installment)
        .where(Installment.user_id == user_id)
        .order_by(Installment.is_active.desc(), Installment.payment_day)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    # 단일 IN 쿼리로 필요한 모든 카테고리를 한번에 조회
    cat_ids = {inst.category_id for inst in items}
    cat_cache: dict[uuid.UUID, BudgetCategory] = {}
    if cat_ids:
        cat_stmt = select(BudgetCategory).where(BudgetCategory.id.in_(cat_ids))
        cats = (await db.execute(cat_stmt)).scalars().all()
        cat_cache = {cat.id: cat for cat in cats}

    # 출금 자산명 일괄 조회
    asset_ids = {inst.source_asset_id for inst in items if inst.source_asset_id}
    asset_cache: dict[uuid.UUID, str] = {}
    if asset_ids:
        asset_stmt = select(Asset).where(Asset.id.in_(asset_ids))
        assets = (await db.execute(asset_stmt)).scalars().all()
        asset_cache = {a.id: a.name for a in assets}

    responses = []
    for inst in items:
        cat = cat_cache.get(inst.category_id)
        if cat:
            asset_name = asset_cache.get(inst.source_asset_id) if inst.source_asset_id else None
            responses.append(_installment_to_response(inst, cat, asset_name))
    return responses


async def create_installment(
    db: AsyncSession, user_id: uuid.UUID, data: InstallmentCreate
) -> InstallmentResponse:
    category = await _get_user_category(db, user_id, data.category_id)

    if data.source_asset_id:
        await _validate_source_asset(db, user_id, data.source_asset_id)

    inst = Installment(
        user_id=user_id,
        category_id=data.category_id,
        name=data.name,
        total_amount=data.total_amount,
        monthly_amount=data.monthly_amount,
        payment_day=data.payment_day,
        total_installments=data.total_installments,
        start_date=data.start_date,
        end_date=data.end_date,
        source_asset_id=data.source_asset_id,
    )
    db.add(inst)
    await db.commit()
    await db.refresh(inst)
    asset_name = None
    if inst.source_asset_id:
        asset = await db.get(Asset, inst.source_asset_id)
        asset_name = asset.name if asset else None
    return _installment_to_response(inst, category, asset_name)


async def update_installment(
    db: AsyncSession,
    user_id: uuid.UUID,
    inst_id: uuid.UUID,
    data: InstallmentUpdate,
) -> InstallmentResponse:
    inst = await _get_user_installment(db, user_id, inst_id)
    update_data = data.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        await _get_user_category(db, user_id, update_data["category_id"])

    if "source_asset_id" in update_data and update_data["source_asset_id"]:
        await _validate_source_asset(db, user_id, update_data["source_asset_id"])

    for field, value in update_data.items():
        setattr(inst, field, value)

    await db.commit()
    await db.refresh(inst)
    category = await db.get(BudgetCategory, inst.category_id)
    asset_name = None
    if inst.source_asset_id:
        asset = await db.get(Asset, inst.source_asset_id)
        asset_name = asset.name if asset else None
    return _installment_to_response(inst, category, asset_name)


async def delete_installment(
    db: AsyncSession, user_id: uuid.UUID, inst_id: uuid.UUID
) -> None:
    inst = await _get_user_installment(db, user_id, inst_id)
    await db.delete(inst)
    await db.commit()


async def get_installment_progress(
    db: AsyncSession, user_id: uuid.UUID, inst_id: uuid.UUID
) -> InstallmentResponse:
    inst = await _get_user_installment(db, user_id, inst_id)
    category = await db.get(BudgetCategory, inst.category_id)
    return _installment_to_response(inst, category)
