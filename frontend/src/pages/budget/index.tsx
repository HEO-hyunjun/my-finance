import { useState, useCallback, useEffect, useRef } from 'react';
import {
  Plus,
  AlertCircle,
  TrendingDown,
  TrendingUp,
  Wallet,
  Settings,
  Pencil,
  Trash2,
} from 'lucide-react';
import {
  useBudgetOverview,
  useBudgetCategories,
  useBudgetAnalysis,
  useCreateAllocation,
  useUpdateAllocation,
} from '@/features/budget/api';
import { PeriodSettingsDialog } from '@/features/budget/ui/PeriodSettingsDialog';
import { BatchAllocationDialog } from '@/features/budget/ui/BatchAllocationDialog';
import { AddCategoryDialog } from '@/features/budget/ui/AddCategoryDialog';
import { EditCategoryDialog } from '@/features/budget/ui/EditCategoryDialog';
import { formatCurrency, formatPercent } from '@/features/budget/lib/format';
import type { UnifiedCategoryRow } from '@/features/budget/model/unified-row';
import {
  useCarryoverSettings,
  useUpsertCarryoverSetting,
} from '@/features/budget/api/carryover';
import { useCategories, useDeleteCategory } from '@/features/categories/api';
import { useAccounts } from '@/features/accounts/api';
import type { Account } from '@/entities/account/model/types';
import type {
  CarryoverSettingCreate,
  CarryoverSettingResponse,
} from '@/shared/types/carryover';
import { CARRYOVER_TYPE_LABELS } from '@/shared/types/carryover';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Card, CardContent } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';

// ─── Status Badge ──────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  normal: 'text-green-600 bg-green-50 dark:bg-green-950/20',
  warning: 'text-amber-600 bg-amber-50 dark:bg-amber-950/20',
  exceeded: 'text-red-600 bg-red-50 dark:bg-red-950/20',
};

const STATUS_LABELS: Record<string, string> = {
  normal: '정상',
  warning: '주의',
  exceeded: '초과',
};

function StatusBadge({ status }: { status: string | null }) {
  if (!status || status === 'normal') {
    return null;
  }
  return (
    <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${STATUS_COLORS[status] ?? ''}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ─── Overview Card ─────────────────────────────────────────────────────────────

interface OverviewCardProps {
  onPeriodSettingsClick: () => void;
}

function OverviewCard({ onPeriodSettingsClick }: OverviewCardProps) {
  const { data: overview, isLoading, isError } = useBudgetOverview();

  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (isError || !overview) return null;

  const rows: Array<{ label: string; amount: number; color?: string }> = [
    { label: '이번 달 수입', amount: overview.total_income, color: 'text-green-600' },
  ];

  return (
    <Card>
      <CardContent className="pt-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Wallet className="h-5 w-5 text-primary" />
            예산 개요
          </h2>
          <Button variant="ghost" size="sm" onClick={onPeriodSettingsClick}>
            <Settings className="mr-1 h-4 w-4" />
            기간 설정
          </Button>
        </div>

        <div className="space-y-2 text-sm">
          {rows.map((row) => (
            <div key={row.label} className="flex justify-between items-center">
              <span className="text-muted-foreground">{row.label}</span>
              <span className={row.color ?? ''}>
                {row.amount >= 0 ? formatCurrency(row.amount) : `- ${formatCurrency(Math.abs(row.amount))}`}
              </span>
            </div>
          ))}
          <div className="border-t pt-2 flex justify-between items-center font-semibold text-base">
            <span>사용 가능 예산</span>
            <span className={overview.available_budget >= 0 ? 'text-primary' : 'text-destructive'}>
              {formatCurrency(overview.available_budget)}
            </span>
          </div>
        </div>

        <div className="rounded-lg bg-muted/50 px-4 py-3 space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">배분 완료</span>
            <span>{formatCurrency(overview.total_allocated)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">미배분</span>
            <span className={overview.unallocated < 0 ? 'text-destructive' : ''}>
              {formatCurrency(overview.unallocated)}
            </span>
          </div>
          {overview.available_budget > 0 && (
            <div className="pt-1">
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{
                    width: `${Math.min((overview.total_allocated / overview.available_budget) * 100, 100)}%`,
                  }}
                />
              </div>
            </div>
          )}
        </div>

        <p className="text-xs text-muted-foreground text-right">
          기간: {overview.period_start} ~ {overview.period_end}
        </p>
      </CardContent>
    </Card>
  );
}

// ─── Inline Budget Editor (호버 시 인풋 전환) ─────────────────────────────────

interface InlineBudgetEditorProps {
  allocated: number;
  hasAllocation: boolean;
  onSave: (amount: number) => void;
  isSaving: boolean;
}

function InlineBudgetEditor({ allocated, hasAllocation, onSave, isSaving }: InlineBudgetEditorProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const startEdit = () => {
    setValue(allocated > 0 ? String(allocated) : '');
    setEditing(true);
  };

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const handleSave = () => {
    const num = Number(value);
    if (!isNaN(num) && num >= 0 && num !== allocated) {
      onSave(num);
    }
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') setEditing(false);
  };

  if (editing) {
    return (
      <Input
        ref={inputRef}
        type="number"
        min="0"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleSave}
        className="h-7 w-28 text-sm font-semibold text-right px-2"
        disabled={isSaving}
      />
    );
  }

  return (
    <span
      onClick={startEdit}
      className="font-semibold text-sm cursor-pointer rounded px-1.5 py-0.5 transition-colors hover:bg-muted"
      title="클릭하여 예산 수정"
    >
      {hasAllocation ? formatCurrency(allocated) : <span className="text-muted-foreground italic">미배분</span>}
    </span>
  );
}

// ─── Carryover Summary (읽기 전용 한 줄 요약) ─────────────────────────────────

function getCarryoverSummary(
  current: CarryoverSettingResponse | null,
  accounts: Account[],
): string {
  if (!current) return '소멸';
  const typeLabel = CARRYOVER_TYPE_LABELS[current.carryover_type];

  if (current.carryover_type === 'expire') return '소멸';
  if (current.carryover_type === 'next_month') {
    return current.carryover_limit
      ? `다음달 이월 (한도 ${current.carryover_limit.toLocaleString('ko-KR')}원)`
      : '다음달 이월';
  }

  // transfer, savings, deposit
  const source = current.source_asset_id
    ? accounts.find((a) => a.id === current.source_asset_id)
    : null;
  const target = current.target_asset_id
    ? accounts.find((a) => a.id === current.target_asset_id)
    : null;

  if (source && target) {
    return `${typeLabel} ${source.name} → ${target.name}`;
  }
  if (target) {
    return `${typeLabel} → ${target.name}`;
  }
  return `${typeLabel} (미설정)`;
}

// ─── Unified Category Row Item ────────────────────────────────────────────────

interface UnifiedCategoryRowProps {
  row: UnifiedCategoryRow;
  accounts: Account[];
  onEdit: () => void;
  onDelete: () => void;
  onBudgetSave: (categoryId: string, amount: number, allocationId?: string) => void;
  isSavingBudget: boolean;
}

function UnifiedCategoryRowItem({
  row,
  accounts,
  onEdit,
  onDelete,
  onBudgetSave,
  isSavingBudget,
}: UnifiedCategoryRowProps) {
  const { category, allocated, spent, status, carryover } = row;
  const hasAllocation = row.allocation !== null;
  const usageRate = allocated > 0 ? Math.min(spent / allocated, 1) : 0;
  const isExceeded = hasAllocation && spent > allocated;
  const remaining = allocated - spent;

  const progressColor = isExceeded
    ? 'bg-destructive'
    : status === 'warning'
      ? 'bg-amber-500'
      : 'bg-primary';

  const handleBudgetSave = (amount: number) => {
    onBudgetSave(category.id, amount, row.allocation?.allocation_id);
  };

  const carryoverSummary = getCarryoverSummary(carryover, accounts);

  return (
    <div className={`rounded-lg border bg-card px-4 py-3 space-y-3 ${!hasAllocation ? 'border-dashed bg-card/50' : ''}`}>
      {/* 상단: 카테고리 이름 + 예산 금액 (같은 크기) + 액션 버튼 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {category.icon && <span aria-hidden="true" className="text-base shrink-0">{category.icon}</span>}
          {category.color && (
            <span
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: category.color }}
              aria-hidden="true"
            />
          )}
          <span className={`font-medium truncate ${!hasAllocation ? 'text-muted-foreground' : ''}`}>
            {category.name}
          </span>
          <StatusBadge status={status} />
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <InlineBudgetEditor
            allocated={allocated}
            hasAllocation={hasAllocation}
            onSave={handleBudgetSave}
            isSaving={isSavingBudget}
          />
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={onEdit} title="편집">
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 text-destructive hover:text-destructive"
            onClick={onDelete}
            title="삭제"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* 예산 사용량 (진행바 + 텍스트) */}
      {hasAllocation && (
        <div className="space-y-1">
          <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${progressColor}`}
              style={{ width: `${Math.min(usageRate * 100, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{formatCurrency(spent)} 사용</span>
            <span>
              {isExceeded ? (
                <span className="text-destructive font-medium">{formatCurrency(Math.abs(remaining))} 초과</span>
              ) : (
                <span>{formatCurrency(remaining)} 남음</span>
              )}
            </span>
          </div>
        </div>
      )}

      {!hasAllocation && spent > 0 && (
        <div className="text-xs text-muted-foreground">
          이번 달 지출: {formatCurrency(spent)}
        </div>
      )}

      {/* 이월 정책 한 줄 요약 */}
      <div className="text-xs text-muted-foreground">
        이월: {carryoverSummary}
      </div>
    </div>
  );
}

// ─── Unified Category Section ──────────────────────────────────────────────────

interface UnifiedCategorySectionProps {
  rows: UnifiedCategoryRow[];
  accounts: Account[];
  isLoading: boolean;
  onOpenBatchAllocation: () => void;
  onOpenAdd: () => void;
  onBudgetSave: (categoryId: string, amount: number, allocationId?: string) => void;
  onCarryoverSave: (data: CarryoverSettingCreate) => void;
  isSavingBudget: boolean;
  isSavingCarryover: boolean;
}

function UnifiedCategorySection({
  rows,
  accounts,
  isLoading,
  onOpenBatchAllocation,
  onOpenAdd,
  onBudgetSave,
  onCarryoverSave,
  isSavingBudget,
  isSavingCarryover,
}: UnifiedCategorySectionProps) {
  const [editTarget, setEditTarget] = useState<UnifiedCategoryRow | null>(null);
  const [confirmDeleteCatId, setConfirmDeleteCatId] = useState<string | null>(null);

  const deleteCategory = useDeleteCategory();

  const handleConfirmDeleteCat = useCallback(() => {
    if (confirmDeleteCatId) {
      deleteCategory.mutate(confirmDeleteCatId);
      setConfirmDeleteCatId(null);
    }
  }, [confirmDeleteCatId, deleteCategory]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  return (
    <>
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">카테고리별 예산</h2>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={onOpenAdd}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            추가
          </Button>
          <Button size="sm" variant="outline" onClick={onOpenBatchAllocation}>
            <Settings className="mr-1.5 h-3.5 w-3.5" />
            일괄 배분
          </Button>
        </div>
      </div>

      {/* 목록 */}
      {rows.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <p className="text-muted-foreground">지출 카테고리가 없습니다.</p>
            <p className="mt-1 text-xs text-muted-foreground">
              [+ 추가]로 카테고리를 만들어보세요.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {rows.map((row) => (
            <UnifiedCategoryRowItem
              key={row.category.id}
              row={row}
              accounts={accounts}
              onEdit={() => setEditTarget(row)}
              onDelete={() => setConfirmDeleteCatId(row.category.id)}
              onBudgetSave={onBudgetSave}
              isSavingBudget={isSavingBudget}
            />
          ))}
        </div>
      )}

      {/* 편집 다이얼로그 (카테고리 메타 + 이월 정책) */}
      {editTarget && (
        <EditCategoryDialog
          category={editTarget.category}
          carryover={editTarget.carryover}
          accounts={accounts}
          isOpen={editTarget !== null}
          onClose={() => setEditTarget(null)}
          onCarryoverSave={onCarryoverSave}
          isSavingCarryover={isSavingCarryover}
        />
      )}

      {/* 삭제 확인 */}
      <ConfirmDialog
        open={confirmDeleteCatId !== null}
        onOpenChange={(open) => { if (!open) setConfirmDeleteCatId(null); }}
        title="카테고리를 삭제하시겠습니까?"
        description="이 카테고리에 연결된 예산 배분도 함께 삭제될 수 있습니다."
        confirmLabel="삭제"
        onConfirm={handleConfirmDeleteCat}
        variant="destructive"
      />
    </>
  );
}

// ─── Analysis Section ──────────────────────────────────────────────────────────

function AnalysisSection() {
  const { data: analysis, isLoading } = useBudgetAnalysis();

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!analysis) return null;

  const { daily_budget, weekly_analysis, fixed_deductions, alerts } = analysis;

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">예산 분석</h2>

      {alerts.length > 0 && (
        <div className="space-y-1.5">
          {alerts.map((alert, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {alert}
            </div>
          ))}
        </div>
      )}

      <Card>
        <CardContent className="pt-4 space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground">일별 사용 가능 예산</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-muted-foreground text-xs">일 예산</p>
              <p className="font-semibold">{formatCurrency(daily_budget.daily_available)}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">오늘 지출</p>
              <p className="font-semibold">{formatCurrency(daily_budget.today_spent)}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">잔여 예산</p>
              <p className={`font-semibold ${daily_budget.remaining_budget < 0 ? 'text-destructive' : ''}`}>
                {formatCurrency(daily_budget.remaining_budget)}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">남은 일수</p>
              <p className="font-semibold">{daily_budget.remaining_days}일</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4 space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground">주간 분석</h3>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">이번 주 지출</span>
            <span className="font-semibold">{formatCurrency(weekly_analysis.week_spent)}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">주간 평균 예산</span>
            <span>{formatCurrency(weekly_analysis.weekly_average_budget)}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">예산 사용률</span>
            <span className={`flex items-center gap-1 ${weekly_analysis.is_over_budget ? 'text-destructive' : 'text-green-600'}`}>
              {weekly_analysis.is_over_budget ? (
                <TrendingUp className="h-3.5 w-3.5" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5" />
              )}
              {formatPercent(weekly_analysis.usage_rate)}
            </span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4 space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground">고정 지출 현황</h3>
          <div className="grid grid-cols-3 gap-2 text-sm text-center">
            <div className="rounded-md bg-muted/50 px-2 py-2">
              <p className="text-xs text-muted-foreground">총액</p>
              <p className="font-semibold">{formatCurrency(fixed_deductions.total_amount)}</p>
            </div>
            <div className="rounded-md bg-green-50 px-2 py-2 dark:bg-green-950/20">
              <p className="text-xs text-muted-foreground">납부 완료</p>
              <p className="font-semibold text-green-600">{formatCurrency(fixed_deductions.paid_amount)}</p>
            </div>
            <div className="rounded-md bg-amber-50 px-2 py-2 dark:bg-amber-950/20">
              <p className="text-xs text-muted-foreground">미납</p>
              <p className="font-semibold text-amber-600">{formatCurrency(fixed_deductions.remaining_amount)}</p>
            </div>
          </div>
          {fixed_deductions.items.length > 0 && (
            <div className="space-y-1 pt-1">
              {fixed_deductions.items.map((item, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1.5">
                    <span
                      className="inline-block h-1.5 w-1.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: item.color ?? '#9CA3AF' }}
                    />
                    <span className={item.is_paid ? 'text-muted-foreground line-through' : ''}>
                      {item.name}
                    </span>
                    <span className="text-xs text-muted-foreground">({item.payment_day === 0 ? '말일' : `${item.payment_day}일`})</span>
                  </span>
                  <span className={item.is_paid ? 'text-muted-foreground line-through' : ''}>
                    {formatCurrency(item.amount)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Page Component ────────────────────────────────────────────────────────────

export function Component() {
  const { data: budgetCategories = [], isLoading: catBudgetLoading } = useBudgetCategories();
  const { isLoading: catLoading } = useCategories();
  const { data: expenseCategories = [], isLoading: expCatLoading } = useCategories('expense');
  const { data: analysis, isLoading: analysisLoading } = useBudgetAnalysis();
  const { data: overview } = useBudgetOverview();
  const { data: carryoverSettings = [] } = useCarryoverSettings();
  const { data: accounts = [] } = useAccounts();

  const createAllocation = useCreateAllocation();
  const updateAllocation = useUpdateAllocation();
  const upsertCarryover = useUpsertCarryoverSetting();

  const [showPeriodSettings, setShowPeriodSettings] = useState(false);
  const [showBatchAllocation, setShowBatchAllocation] = useState(false);
  const [showAddCategory, setShowAddCategory] = useState(false);

  const isLoading = catBudgetLoading || expCatLoading || catLoading || analysisLoading;

  // 이월 설정 맵
  const carryoverMap = new Map(carryoverSettings.map((s) => [s.category_id, s]));

  // 카테고리 + 배분 + 분석 + 이월 데이터 통합
  const unifiedRows: UnifiedCategoryRow[] = expenseCategories.map((cat) => {
    const allocation = budgetCategories.find((b) => b.category_id === cat.id) ?? null;
    const rate = analysis?.category_rates?.find((r) => r.category_id === cat.id) ?? null;
    const allocated = allocation?.allocated ?? 0;
    const spent = allocation?.spent ?? rate?.spent ?? 0;
    const remaining = allocation?.remaining ?? 0;
    const usage_rate =
      rate?.usage_rate ??
      (allocated > 0 ? spent / allocated : 0);

    return {
      category: cat,
      allocation,
      rate,
      allocated,
      spent,
      remaining,
      usage_rate,
      status: rate?.status ?? null,
      carryover: carryoverMap.get(cat.id) ?? null,
    };
  });

  const handleBudgetSave = useCallback(
    (categoryId: string, amount: number, allocationId?: string) => {
      if (allocationId) {
        updateAllocation.mutate({ id: allocationId, amount });
      } else if (amount > 0) {
        createAllocation.mutate({ category_id: categoryId, amount });
      }
    },
    [createAllocation, updateAllocation],
  );

  const handleCarryoverSave = useCallback(
    (data: CarryoverSettingCreate) => {
      upsertCarryover.mutate(data);
    },
    [upsertCarryover],
  );

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">예산 관리</h1>
      </div>

      {/* Section 1: Overview */}
      <OverviewCard onPeriodSettingsClick={() => setShowPeriodSettings(true)} />

      {/* Section 2: 카테고리별 예산 (통합: 배분 + 이월 정책) */}
      <div className="space-y-3">
        <UnifiedCategorySection
          rows={unifiedRows}
          accounts={accounts}
          isLoading={isLoading}
          onOpenBatchAllocation={() => setShowBatchAllocation(true)}
          onOpenAdd={() => setShowAddCategory(true)}
          onBudgetSave={handleBudgetSave}
          onCarryoverSave={handleCarryoverSave}
          isSavingBudget={createAllocation.isPending || updateAllocation.isPending}
          isSavingCarryover={upsertCarryover.isPending}
        />
      </div>

      {/* Section 3: 예산 분석 */}
      <AnalysisSection />

      {/* 기간 설정 모달 */}
      <PeriodSettingsDialog
        isOpen={showPeriodSettings}
        onClose={() => setShowPeriodSettings(false)}
        currentDay={overview?.period_start_day ?? 1}
      />

      {/* 예산 일괄 배분 모달 */}
      <BatchAllocationDialog
        isOpen={showBatchAllocation}
        onClose={() => setShowBatchAllocation(false)}
        rows={unifiedRows}
        availableBudget={overview?.available_budget ?? 0}
      />

      {/* 카테고리 추가 모달 */}
      <AddCategoryDialog
        isOpen={showAddCategory}
        onClose={() => setShowAddCategory(false)}
      />
    </div>
  );
}
