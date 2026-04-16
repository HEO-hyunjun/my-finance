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
  useUpdateBudgetPeriod,
} from '@/features/budget/api';
import {
  useCarryoverSettings,
  useUpsertCarryoverSetting,
} from '@/features/budget/api/carryover';
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from '@/features/categories/api';
import { useAccounts } from '@/features/accounts/api';
import type { CategoryBudget, CategorySpendingRate } from '@/entities/budget/model/types';
import type { Category } from '@/entities/category/model/types';
import type { Account } from '@/entities/account/model/types';
import type {
  CarryoverType,
  CarryoverSettingCreate,
  CarryoverSettingResponse,
} from '@/shared/types/carryover';
import { CARRYOVER_TYPE_LABELS } from '@/shared/types/carryover';
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

// ─── 상수 ─────────────────────────────────────────────────────────────────────

const CARRYOVER_TYPES: CarryoverType[] = ['expire', 'next_month', 'savings', 'transfer', 'deposit'];
const TRANSFER_TARGET_TYPES = new Set(['cash', 'parking']);
const SOURCE_ACCOUNT_TYPES = new Set(['cash', 'parking', 'investment']);

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

// ─── Unified Row Data Type ─────────────────────────────────────────────────────

interface UnifiedCategoryRow {
  category: Category;
  allocation: CategoryBudget | null;
  rate: CategorySpendingRate | null;
  allocated: number;
  spent: number;
  remaining: number;
  usage_rate: number;
  status: 'normal' | 'warning' | 'exceeded' | null;
  carryover: CarryoverSettingResponse | null;
}

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
    { label: '고정 지출', amount: -overview.total_fixed_expense, color: 'text-red-500' },
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
          {overview.total_transfer > 0 && (
            <p className="text-xs text-muted-foreground pt-1">
              * 계획된 자동이체 {formatCurrency(overview.total_transfer)} (계좌 간 이동, 예산 미차감)
            </p>
          )}
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

// ─── Batch Allocation Dialog (예산 일괄 배분) ─────────────────────────────────

interface BatchAllocationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  rows: UnifiedCategoryRow[];
  availableBudget: number;
}

function BatchAllocationDialog({ isOpen, onClose, rows, availableBudget }: BatchAllocationDialogProps) {
  const createAllocation = useCreateAllocation();
  const updateAllocation = useUpdateAllocation();

  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const [isApplying, setIsApplying] = useState(false);

  useEffect(() => {
    if (isOpen) {
      const initial: Record<string, string> = {};
      rows.forEach((r) => {
        initial[r.category.id] = r.allocated > 0 ? String(r.allocated) : '';
      });
      setAmounts(initial);
    }
  }, [isOpen, rows]);

  const totalAllocated = Object.values(amounts).reduce((sum, v) => {
    const n = Number(v);
    return sum + (isNaN(n) ? 0 : n);
  }, 0);

  const unallocated = availableBudget - totalAllocated;

  const handleEqualDistribute = () => {
    if (rows.length === 0) return;
    const perCategory = Math.floor(availableBudget / rows.length);
    const updated: Record<string, string> = {};
    rows.forEach((r) => {
      updated[r.category.id] = String(perCategory);
    });
    setAmounts(updated);
  };

  const handleApply = async () => {
    setIsApplying(true);
    try {
      for (const row of rows) {
        const newAmount = Number(amounts[row.category.id]);
        if (isNaN(newAmount) || newAmount < 0) continue;
        if (newAmount === row.allocated) continue;

        if (row.allocation) {
          await updateAllocation.mutateAsync({ id: row.allocation.allocation_id, amount: newAmount });
        } else if (newAmount > 0) {
          await createAllocation.mutateAsync({ category_id: row.category.id, amount: newAmount });
        }
      }
      onClose();
    } finally {
      setIsApplying(false);
    }
  };

  const hasChanges = rows.some((r) => {
    const newAmount = Number(amounts[r.category.id] ?? '');
    return !isNaN(newAmount) && newAmount !== r.allocated;
  });

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>예산 일괄 배분</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-lg bg-muted/50 px-4 py-3 space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">사용 가능 예산</span>
              <span className="font-semibold">{formatCurrency(availableBudget)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">배분 합계</span>
              <span>{formatCurrency(totalAllocated)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">미배분</span>
              <span className={unallocated < 0 ? 'text-destructive font-semibold' : ''}>
                {formatCurrency(unallocated)}
              </span>
            </div>
          </div>

          <Button variant="outline" size="sm" className="w-full" onClick={handleEqualDistribute}>
            균등 배분 ({rows.length}개 카테고리)
          </Button>

          <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
            {rows.map((row) => (
              <div key={row.category.id} className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 min-w-0 flex-1">
                  {row.category.icon && <span className="text-sm shrink-0">{row.category.icon}</span>}
                  {row.category.color && (
                    <span
                      className="inline-block h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: row.category.color }}
                    />
                  )}
                  <span className="text-sm truncate">{row.category.name}</span>
                </div>
                <Input
                  type="number"
                  min="0"
                  value={amounts[row.category.id] ?? ''}
                  onChange={(e) => setAmounts((prev) => ({ ...prev, [row.category.id]: e.target.value }))}
                  placeholder="0"
                  className="h-8 w-32 text-right text-sm"
                />
              </div>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isApplying}>취소</Button>
          <Button onClick={handleApply} disabled={isApplying || !hasChanges}>
            {isApplying ? '적용 중...' : '적용'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Add Category Dialog ───────────────────────────────────────────────────────

interface AddCategoryDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

function AddCategoryDialog({ isOpen, onClose }: AddCategoryDialogProps) {
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('');
  const [color, setColor] = useState('#6366f1');
  const [budgetAmount, setBudgetAmount] = useState('');

  const createCategory = useCreateCategory();
  const createAllocation = useCreateAllocation();

  useEffect(() => {
    if (isOpen) {
      setName('');
      setIcon('');
      setColor('#6366f1');
      setBudgetAmount('');
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      const newCat = await createCategory.mutateAsync({
        direction: 'expense',
        name: name.trim(),
        icon: icon || null,
        color: color || null,
      });

      const amount = Number(budgetAmount);
      if (!isNaN(amount) && amount > 0) {
        await createAllocation.mutateAsync({ category_id: newCat.id, amount });
      }

      onClose();
    } catch {
      // error handled by mutation
    }
  };

  const isPending = createCategory.isPending || createAllocation.isPending;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>카테고리 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="add_name">카테고리 이름 *</Label>
            <Input
              id="add_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="예: 식비"
              autoFocus
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="add_icon">아이콘</Label>
              <Input
                id="add_icon"
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                placeholder="🍽️"
                className="text-center"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="add_color">색상</Label>
              <div className="flex items-center gap-2">
                <input
                  id="add_color"
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="h-9 w-12 cursor-pointer rounded border"
                  title="색상 선택"
                />
                <span className="text-xs text-muted-foreground font-mono">{color}</span>
              </div>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="add_budget">예산 금액 (선택)</Label>
            <Input
              id="add_budget"
              type="number"
              min="0"
              value={budgetAmount}
              onChange={(e) => setBudgetAmount(e.target.value)}
              placeholder="0"
            />
            <p className="text-xs text-muted-foreground">비워두면 미배분 상태로 생성됩니다.</p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>취소</Button>
            <Button type="submit" disabled={isPending || !name.trim()}>
              {isPending ? '추가 중...' : '추가'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Category Dialog (이름, 아이콘, 색상 + 이월 정책) ──────────────────

interface EditCategoryDialogProps {
  category: Category;
  carryover: CarryoverSettingResponse | null;
  accounts: Account[];
  isOpen: boolean;
  onClose: () => void;
  onCarryoverSave: (data: CarryoverSettingCreate) => void;
  isSavingCarryover: boolean;
}

function EditCategoryDialog({
  category,
  carryover,
  accounts,
  isOpen,
  onClose,
  onCarryoverSave,
  isSavingCarryover,
}: EditCategoryDialogProps) {
  const [name, setName] = useState(category.name);
  const [icon, setIcon] = useState(category.icon ?? '');
  const [color, setColor] = useState(category.color ?? '#6366f1');
  const [defaultAllocation, setDefaultAllocation] = useState(
    category.default_allocation != null ? String(category.default_allocation) : '',
  );

  // 이월 정책 state
  const [coType, setCoType] = useState<CarryoverType>(carryover?.carryover_type ?? 'expire');
  const [coLimit, setCoLimit] = useState(carryover?.carryover_limit?.toString() ?? '');
  const [coSourceId, setCoSourceId] = useState(carryover?.source_asset_id ?? '');
  const [coTargetId, setCoTargetId] = useState(carryover?.target_asset_id ?? '');
  const [coRate, setCoRate] = useState(carryover?.target_annual_rate?.toString() ?? '');

  const updateCategory = useUpdateCategory();

  useEffect(() => {
    if (isOpen) {
      setName(category.name);
      setIcon(category.icon ?? '');
      setColor(category.color ?? '#6366f1');
      setDefaultAllocation(
        category.default_allocation != null ? String(category.default_allocation) : '',
      );
      setCoType(carryover?.carryover_type ?? 'expire');
      setCoLimit(carryover?.carryover_limit?.toString() ?? '');
      setCoSourceId(carryover?.source_asset_id ?? '');
      setCoTargetId(carryover?.target_asset_id ?? '');
      setCoRate(carryover?.target_annual_rate?.toString() ?? '');
    }
  }, [isOpen, category, carryover]);

  const coNeedsTransfer = coType === 'savings' || coType === 'deposit' || coType === 'transfer';

  const coHasChanges =
    coType !== (carryover?.carryover_type ?? 'expire') ||
    (coType === 'next_month' && coLimit !== (carryover?.carryover_limit?.toString() ?? '')) ||
    (coNeedsTransfer && coSourceId !== (carryover?.source_asset_id ?? '')) ||
    (coNeedsTransfer && coTargetId !== (carryover?.target_asset_id ?? '')) ||
    (coType === 'deposit' && coRate !== (carryover?.target_annual_rate?.toString() ?? ''));

  const sourceAccounts = accounts.filter((a) => SOURCE_ACCOUNT_TYPES.has(a.account_type));
  const filteredTargets = accounts.filter((a) => {
    if (coType === 'savings') return a.account_type === 'savings';
    if (coType === 'deposit') return a.account_type === 'deposit';
    if (coType === 'transfer') return TRANSFER_TARGET_TYPES.has(a.account_type);
    return false;
  });

  const handleTargetChange = (id: string) => {
    setCoTargetId(id);
    if (coType === 'deposit' && id) {
      const selected = accounts.find((a) => a.id === id);
      if (selected?.interest_rate != null) setCoRate(selected.interest_rate.toString());
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      const parsedDefault = defaultAllocation === '' ? null : Number(defaultAllocation);
      const catChanged =
        name.trim() !== category.name ||
        (icon || null) !== category.icon ||
        (color || null) !== category.color ||
        parsedDefault !== (category.default_allocation ?? null);

      if (catChanged) {
        await updateCategory.mutateAsync({
          id: category.id,
          name: name.trim(),
          icon: icon || null,
          color: color || null,
          default_allocation: parsedDefault,
        });
      }

      if (coHasChanges) {
        const data: CarryoverSettingCreate = {
          category_id: category.id,
          carryover_type: coType,
        };
        if (coType === 'next_month' && coLimit) data.carryover_limit = Number(coLimit);
        if (coNeedsTransfer && coTargetId) {
          if (coSourceId) data.source_asset_id = coSourceId;
          data.target_asset_id = coTargetId;
          const selected = accounts.find((a) => a.id === coTargetId);
          if (selected) data.target_savings_name = selected.name;
        }
        if (coType === 'deposit' && coRate) data.target_annual_rate = Number(coRate);
        onCarryoverSave(data);
      }

      onClose();
    } catch {
      // error handled by mutation
    }
  };

  const isPending = updateCategory.isPending || isSavingCarryover;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>카테고리 편집</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="edit_name">카테고리 이름 *</Label>
            <Input
              id="edit_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="edit_icon">아이콘</Label>
              <Input
                id="edit_icon"
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                placeholder="🍽️"
                className="text-center"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit_color">색상</Label>
              <div className="flex items-center gap-2">
                <input
                  id="edit_color"
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="h-9 w-12 cursor-pointer rounded border"
                  title="색상 선택"
                />
                <span className="text-xs text-muted-foreground font-mono">{color}</span>
              </div>
            </div>
          </div>

          {category.direction === 'expense' && (
            <div className="space-y-1.5 pt-2 border-t">
              <Label htmlFor="edit_default_allocation" className="text-sm font-medium">
                기본 월 배분액 (원)
              </Label>
              <Input
                id="edit_default_allocation"
                type="number"
                value={defaultAllocation}
                onChange={(e) => setDefaultAllocation(e.target.value)}
                placeholder="설정 안 함"
                min="0"
              />
              <p className="text-xs text-muted-foreground">
                매 기간 시작 시 이 금액으로 예산이 자동 배정됩니다. 이월된 잔여액은 여기에 더해집니다.
              </p>
            </div>
          )}

          {/* 이월 정책 */}
          <div className="space-y-3 pt-2 border-t">
            <Label className="text-sm font-medium">이월 정책</Label>
            <div className="space-y-2">
              <select
                value={coType}
                onChange={(e) => setCoType(e.target.value as CarryoverType)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              >
                {CARRYOVER_TYPES.map((t) => (
                  <option key={t} value={t}>{CARRYOVER_TYPE_LABELS[t]}</option>
                ))}
              </select>

              {coType === 'next_month' && (
                <div className="space-y-1">
                  <Label className="text-xs">이월 한도 (원)</Label>
                  <Input
                    type="number"
                    value={coLimit}
                    onChange={(e) => setCoLimit(e.target.value)}
                    placeholder="한도 없음"
                    min="0"
                  />
                </div>
              )}

              {coNeedsTransfer && (
                <>
                  <div className="space-y-1">
                    <Label className="text-xs">출처 계좌 (어디서)</Label>
                    {sourceAccounts.length > 0 ? (
                      <select
                        value={coSourceId}
                        onChange={(e) => setCoSourceId(e.target.value)}
                        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      >
                        <option value="">선택하세요</option>
                        {sourceAccounts.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name}{a.institution ? ` (${a.institution})` : ''}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <p className="text-xs text-muted-foreground py-1">출금 가능 계좌가 없습니다.</p>
                    )}
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">
                      대상 {coType === 'savings' ? '적금' : coType === 'deposit' ? '예금' : '계좌'} (어디로)
                    </Label>
                    {filteredTargets.length > 0 ? (
                      <select
                        value={coTargetId}
                        onChange={(e) => handleTargetChange(e.target.value)}
                        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      >
                        <option value="">선택하세요</option>
                        {filteredTargets.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name}{a.institution ? ` (${a.institution})` : ''}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <p className="text-xs text-muted-foreground py-1">해당 유형 계좌가 없습니다.</p>
                    )}
                  </div>
                </>
              )}

              {coType === 'deposit' && (
                <div className="space-y-1">
                  <Label className="text-xs">연 이율 (%)</Label>
                  <Input
                    type="number"
                    value={coRate}
                    onChange={(e) => setCoRate(e.target.value)}
                    placeholder="예: 3.5"
                    step="0.1"
                    min="0"
                  />
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>취소</Button>
            <Button type="submit" disabled={isPending || !name.trim()}>
              {isPending ? '저장 중...' : '저장'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
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
                      className={`inline-block h-1.5 w-1.5 rounded-full ${item.is_paid ? 'bg-green-500' : 'bg-amber-400'}`}
                    />
                    {item.name}
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
    <div className="mx-auto max-w-2xl space-y-6 p-6">
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
