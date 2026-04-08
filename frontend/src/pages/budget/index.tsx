import { useState, useCallback } from 'react';
import {
  Plus,
  AlertCircle,
  Pencil,
  Trash2,
  Settings,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react';
import {
  useBudgetOverview,
  useBudgetCategories,
  useBudgetAnalysis,
  useCreateAllocation,
  useUpdateAllocation,
  useDeleteAllocation,
  useUpdateBudgetPeriod,
} from '@/features/budget/api';
import { useCategories } from '@/features/categories/api';
import { CategorySelect } from '@/features/categories/ui/CategorySelect';
import type { CategoryBudget } from '@/entities/budget/model/types';
import type { Category } from '@/entities/category/model/types';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Card, CardContent } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/shared/ui/dialog';

// ─── 유틸 ─────────────────────────────────────────────────────────────────────

function formatCurrency(amount: number): string {
  try {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'KRW',
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString('ko-KR')} KRW`;
  }
}

function formatPercent(rate: number): string {
  return `${Math.round(rate * 100)}%`;
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
    { label: '고정 지출', amount: -overview.total_fixed_expense, color: 'text-red-500' },
    { label: '자동 이체', amount: -overview.total_transfer, color: 'text-blue-500' },
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

        {/* 계산 breakdown */}
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

        {/* 배분 현황 */}
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
          {/* 배분율 진행바 */}
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

        {/* 기간 정보 */}
        <p className="text-xs text-muted-foreground text-right">
          기간: {overview.period_start} ~ {overview.period_end}
        </p>
      </CardContent>
    </Card>
  );
}

// ─── Period Settings Dialog ────────────────────────────────────────────────────

interface PeriodSettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  currentDay: number;
}

function PeriodSettingsDialog({ isOpen, onClose, currentDay }: PeriodSettingsDialogProps) {
  const [day, setDay] = useState(String(currentDay));
  const updatePeriod = useUpdateBudgetPeriod();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const num = Number(day);
    if (isNaN(num) || num < 1 || num > 28) return;
    updatePeriod.mutate({ period_start_day: num }, { onSuccess: onClose });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>예산 기간 설정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="period_day">월 시작일 (1~28)</Label>
            <Input
              id="period_day"
              type="number"
              min="1"
              max="28"
              value={day}
              onChange={(e) => setDay(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              예산 집계가 시작되는 날짜입니다.
            </p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>취소</Button>
            <Button type="submit" disabled={updatePeriod.isPending}>
              {updatePeriod.isPending ? '저장 중...' : '저장'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Allocation Create Dialog ──────────────────────────────────────────────────

interface CreateAllocationDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

function CreateAllocationDialog({ isOpen, onClose }: CreateAllocationDialogProps) {
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [amount, setAmount] = useState('');
  const createAllocation = useCreateAllocation();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryId || !amount) return;
    createAllocation.mutate(
      { category_id: categoryId, amount: Number(amount) },
      {
        onSuccess: () => {
          setCategoryId(null);
          setAmount('');
          onClose();
        },
      },
    );
  };

  const handleClose = () => {
    setCategoryId(null);
    setAmount('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>예산 배분</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>카테고리 *</Label>
            <CategorySelect
              direction="expense"
              value={categoryId}
              onChange={setCategoryId}
              placeholder="카테고리 선택"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="alloc_amount">금액 *</Label>
            <Input
              id="alloc_amount"
              type="number"
              min="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>취소</Button>
            <Button type="submit" disabled={createAllocation.isPending || !categoryId || !amount}>
              {createAllocation.isPending ? '배분 중...' : '배분'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Allocation Edit Dialog ────────────────────────────────────────────────────

interface EditAllocationDialogProps {
  allocation: CategoryBudget;
  categoryName: string;
  isOpen: boolean;
  onClose: () => void;
}

function EditAllocationDialog({ allocation, categoryName, isOpen, onClose }: EditAllocationDialogProps) {
  const [amount, setAmount] = useState(String(allocation.allocated));
  const updateAllocation = useUpdateAllocation();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount) return;
    updateAllocation.mutate(
      { id: allocation.allocation_id, amount: Number(amount) },
      { onSuccess: onClose },
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{categoryName} 예산 수정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="edit_amount">금액 *</Label>
            <Input
              id="edit_amount"
              type="number"
              min="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>취소</Button>
            <Button type="submit" disabled={updateAllocation.isPending || !amount}>
              {updateAllocation.isPending ? '수정 중...' : '저장'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── CategoryAllocationRow ─────────────────────────────────────────────────────

interface CategoryAllocationRowProps {
  allocation: CategoryBudget;
  category: Category | undefined;
  onEdit: () => void;
  onDelete: () => void;
}

function CategoryAllocationRow({ allocation, category, onEdit, onDelete }: CategoryAllocationRowProps) {
  const usageRate = allocation.allocated > 0
    ? Math.min(allocation.spent / allocation.allocated, 1)
    : 0;
  const isExceeded = allocation.spent > allocation.allocated;

  return (
    <div className="rounded-lg border bg-card px-4 py-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {category?.icon && <span aria-hidden="true">{category.icon}</span>}
          {category?.color && (
            <span
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: category.color }}
              aria-hidden="true"
            />
          )}
          <span className="font-medium">{category?.name ?? allocation.category_id}</span>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={onEdit}>
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 text-destructive hover:text-destructive"
            onClick={onDelete}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* 진행바 */}
      <div className="space-y-1">
        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${isExceeded ? 'bg-destructive' : 'bg-primary'}`}
            style={{ width: `${Math.min(usageRate * 100, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{formatCurrency(allocation.spent)} 사용</span>
          <span>
            {isExceeded ? (
              <span className="text-destructive font-medium">
                {formatCurrency(Math.abs(allocation.remaining))} 초과
              </span>
            ) : (
              <span>{formatCurrency(allocation.remaining)} 남음</span>
            )}
          </span>
        </div>
        <div className="text-right text-xs text-muted-foreground">
          예산: {formatCurrency(allocation.allocated)}
        </div>
      </div>
    </div>
  );
}

// ─── Analysis Section ──────────────────────────────────────────────────────────

function AnalysisSection() {
  const { data: analysis, isLoading } = useBudgetAnalysis();

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!analysis) return null;

  const { daily_budget, weekly_analysis, category_rates, fixed_deductions, alerts } = analysis;

  const STATUS_COLORS: Record<string, string> = {
    normal: 'text-green-600',
    warning: 'text-amber-500',
    exceeded: 'text-red-600',
  };

  const STATUS_LABELS: Record<string, string> = {
    normal: '정상',
    warning: '주의',
    exceeded: '초과',
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">예산 분석</h2>

      {/* 알림 */}
      {alerts.length > 0 && (
        <div className="space-y-1.5">
          {alerts.map((alert, i) => (
            <div key={i} className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {alert}
            </div>
          ))}
        </div>
      )}

      {/* 일별 예산 */}
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

      {/* 주간 분석 */}
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

      {/* 카테고리별 소진율 */}
      {category_rates.length > 0 && (
        <Card>
          <CardContent className="pt-4 space-y-3">
            <h3 className="text-sm font-semibold text-muted-foreground">카테고리별 소진율</h3>
            <div className="space-y-3">
              {category_rates.map((cat) => (
                <div key={cat.category_id} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-1.5">
                      {cat.category_icon && <span aria-hidden="true">{cat.category_icon}</span>}
                      {cat.category_color && (
                        <span
                          className="inline-block h-2 w-2 rounded-full"
                          style={{ backgroundColor: cat.category_color }}
                          aria-hidden="true"
                        />
                      )}
                      {cat.category_name}
                    </span>
                    <span className={`text-xs font-medium ${STATUS_COLORS[cat.status] ?? ''}`}>
                      {STATUS_LABELS[cat.status] ?? cat.status}
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        cat.status === 'exceeded' ? 'bg-destructive' :
                        cat.status === 'warning' ? 'bg-amber-500' : 'bg-primary'
                      }`}
                      style={{ width: `${Math.min(cat.usage_rate * 100, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{formatCurrency(cat.spent)} / {formatCurrency(cat.monthly_budget)}</span>
                    <span>{formatPercent(cat.usage_rate)}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 고정 지출 요약 */}
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
                      className={`inline-block h-1.5 w-1.5 rounded-full ${item.is_paid ? 'bg-green-500' : 'bg-amber-400'}`}
                    />
                    {item.name}
                    <span className="text-xs text-muted-foreground">({item.payment_day}일)</span>
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
  const { data: categories = [] } = useCategories();
  const { data: overview } = useBudgetOverview();
  const deleteAllocation = useDeleteAllocation();

  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState<CategoryBudget | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [showPeriodSettings, setShowPeriodSettings] = useState(false);

  const handleOpenCreate = useCallback(() => setShowCreate(true), []);
  const handleCloseCreate = useCallback(() => setShowCreate(false), []);

  const handleConfirmDelete = useCallback(() => {
    if (confirmDeleteId) {
      deleteAllocation.mutate(confirmDeleteId);
      setConfirmDeleteId(null);
    }
  }, [confirmDeleteId, deleteAllocation]);

  // category_id -> Category 맵
  const categoryMap = new Map<string, Category>(categories.map((c) => [c.id, c]));

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">예산 관리</h1>
      </div>

      {/* Section 1: Overview */}
      <OverviewCard onPeriodSettingsClick={() => setShowPeriodSettings(true)} />

      {/* Section 2: 카테고리 배분 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">카테고리 예산 배분</h2>
          <Button size="sm" onClick={handleOpenCreate}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            배분 추가
          </Button>
        </div>

        {catBudgetLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        ) : budgetCategories.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center py-12">
              <p className="text-muted-foreground">배분된 카테고리가 없습니다.</p>
              <Button className="mt-4" size="sm" onClick={handleOpenCreate}>
                <Plus className="mr-2 h-4 w-4" />
                첫 배분 추가하기
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {budgetCategories.map((alloc) => (
              <CategoryAllocationRow
                key={alloc.allocation_id}
                allocation={alloc}
                category={categoryMap.get(alloc.category_id)}
                onEdit={() => setEditTarget(alloc)}
                onDelete={() => setConfirmDeleteId(alloc.allocation_id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Section 3: 예산 분석 */}
      <AnalysisSection />

      {/* 배분 추가 모달 */}
      <CreateAllocationDialog isOpen={showCreate} onClose={handleCloseCreate} />

      {/* 배분 수정 모달 */}
      {editTarget && (
        <EditAllocationDialog
          allocation={editTarget}
          categoryName={categoryMap.get(editTarget.category_id)?.name ?? editTarget.category_id}
          isOpen={editTarget !== null}
          onClose={() => setEditTarget(null)}
        />
      )}

      {/* 기간 설정 모달 */}
      <PeriodSettingsDialog
        isOpen={showPeriodSettings}
        onClose={() => setShowPeriodSettings(false)}
        currentDay={overview?.period_start_day ?? 1}
      />

      {/* 삭제 확인 모달 */}
      <ConfirmDialog
        open={confirmDeleteId !== null}
        onOpenChange={(open) => { if (!open) setConfirmDeleteId(null); }}
        title="예산 배분을 삭제하시겠습니까?"
        description="이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={handleConfirmDelete}
        variant="destructive"
      />
    </div>
  );
}
