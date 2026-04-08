import { useState, useCallback, useEffect } from 'react';
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
  useDeleteAllocation,
  useUpdateBudgetPeriod,
} from '@/features/budget/api';
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from '@/features/categories/api';
import type { CategoryBudget, CategorySpendingRate } from '@/entities/budget/model/types';
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

// ─── 기본 프리셋 ───────────────────────────────────────────────────────────────

const DEFAULT_PRESETS = [
  { name: '식비', icon: '🍽️', color: '#ef4444' },
  { name: '교통', icon: '🚗', color: '#3b82f6' },
  { name: '주거', icon: '🏠', color: '#8b5cf6' },
  { name: '통신', icon: '📱', color: '#06b6d4' },
  { name: '구독비', icon: '🗓️', color: '#f59e0b' },
  { name: '문화/여가', icon: '🎬', color: '#10b981' },
  { name: '의료', icon: '🏥', color: '#ec4899' },
  { name: '쇼핑', icon: '🛍️', color: '#f97316' },
  { name: '교육', icon: '📚', color: '#6366f1' },
  { name: '생활비', icon: '📌', color: '#64748b' },
  { name: '저축', icon: '💰', color: '#22c55e' },
];

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
  if (!status) {
    return <span className="text-xs text-muted-foreground">—</span>;
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

// ─── Preset Dialog ─────────────────────────────────────────────────────────────

interface PresetItem {
  name: string;
  icon: string;
  color: string;
  selected: boolean;
  editedName: string;
  editedIcon: string;
}

interface PresetDialogProps {
  isOpen: boolean;
  onClose: () => void;
  existingNames: Set<string>;
}

function PresetDialog({ isOpen, onClose, existingNames }: PresetDialogProps) {
  const createCategory = useCreateCategory();

  const [items, setItems] = useState<PresetItem[]>(() =>
    DEFAULT_PRESETS.map((p) => ({
      ...p,
      selected: !existingNames.has(p.name),
      editedName: p.name,
      editedIcon: p.icon,
    })),
  );

  useEffect(() => {
    if (isOpen) {
      setItems(
        DEFAULT_PRESETS.map((p) => ({
          ...p,
          selected: !existingNames.has(p.name),
          editedName: p.name,
          editedIcon: p.icon,
        })),
      );
    }
  }, [isOpen, existingNames]);

  const [isApplying, setIsApplying] = useState(false);

  const toggleSelect = (idx: number) => {
    setItems((prev) => prev.map((item, i) => i === idx ? { ...item, selected: !item.selected } : item));
  };

  const updateName = (idx: number, name: string) => {
    setItems((prev) => prev.map((item, i) => i === idx ? { ...item, editedName: name } : item));
  };

  const updateIcon = (idx: number, icon: string) => {
    setItems((prev) => prev.map((item, i) => i === idx ? { ...item, editedIcon: icon } : item));
  };

  const handleApply = async () => {
    const toCreate = items.filter((item) => item.selected && !existingNames.has(item.editedName.trim()));
    if (toCreate.length === 0) { onClose(); return; }
    setIsApplying(true);
    try {
      for (const item of toCreate) {
        await createCategory.mutateAsync({
          direction: 'expense',
          name: item.editedName.trim(),
          icon: item.editedIcon || null,
          color: item.color || null,
        });
      }
      onClose();
    } finally {
      setIsApplying(false);
    }
  };

  const selectedCount = items.filter((item) => item.selected && !existingNames.has(item.editedName.trim())).length;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>기본값 설정</DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            추가할 카테고리를 선택하세요. 이미 존재하는 카테고리는 건너뜁니다.
          </p>

          <div className="max-h-80 overflow-y-auto space-y-1.5 pr-1">
            {items.map((item, idx) => {
              const alreadyExists = existingNames.has(item.editedName.trim());
              return (
                <div
                  key={item.name}
                  className={`rounded-lg border px-3 py-2 ${alreadyExists ? 'opacity-50' : ''} ${item.selected && !alreadyExists ? 'border-primary/50 bg-primary/5' : ''}`}
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={item.selected && !alreadyExists}
                      onChange={() => !alreadyExists && toggleSelect(idx)}
                      disabled={alreadyExists}
                      className="h-4 w-4 rounded"
                    />
                    <span
                      className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <Input
                      value={item.editedIcon}
                      onChange={(e) => updateIcon(idx, e.target.value)}
                      className="h-7 w-12 text-center text-sm p-1"
                      disabled={alreadyExists || !item.selected}
                    />
                    <Input
                      value={item.editedName}
                      onChange={(e) => updateName(idx, e.target.value)}
                      className="h-7 flex-1 text-sm"
                      disabled={alreadyExists || !item.selected}
                    />
                    {alreadyExists && (
                      <span className="text-xs text-muted-foreground whitespace-nowrap">이미 존재</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isApplying}>취소</Button>
          <Button onClick={handleApply} disabled={isApplying || selectedCount === 0}>
            {isApplying ? '적용 중...' : `적용 (${selectedCount}개)`}
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

  // dialog 열릴 때 초기화
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

// ─── Edit Category Dialog (Unified) ───────────────────────────────────────────

interface EditCategoryDialogProps {
  row: UnifiedCategoryRow;
  isOpen: boolean;
  onClose: () => void;
}

function EditCategoryDialog({ row, isOpen, onClose }: EditCategoryDialogProps) {
  const [name, setName] = useState(row.category.name);
  const [icon, setIcon] = useState(row.category.icon ?? '');
  const [color, setColor] = useState(row.category.color ?? '#6366f1');
  const [budgetAmount, setBudgetAmount] = useState(row.allocated > 0 ? String(row.allocated) : '');

  const updateCategory = useUpdateCategory();
  const createAllocation = useCreateAllocation();
  const updateAllocation = useUpdateAllocation();

  // dialog 열릴 때 현재 값으로 초기화
  useEffect(() => {
    if (isOpen) {
      setName(row.category.name);
      setIcon(row.category.icon ?? '');
      setColor(row.category.color ?? '#6366f1');
      setBudgetAmount(row.allocated > 0 ? String(row.allocated) : '');
    }
  }, [isOpen, row]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      // 카테고리 정보가 변경됐으면 업데이트
      const catChanged =
        name.trim() !== row.category.name ||
        (icon || null) !== row.category.icon ||
        (color || null) !== row.category.color;

      if (catChanged) {
        await updateCategory.mutateAsync({
          id: row.category.id,
          name: name.trim(),
          icon: icon || null,
          color: color || null,
        });
      }

      // 예산 금액 처리
      const newAmount = Number(budgetAmount);
      const validAmount = !isNaN(newAmount) && newAmount >= 0;

      if (validAmount && newAmount !== row.allocated) {
        if (row.allocation) {
          await updateAllocation.mutateAsync({ id: row.allocation.allocation_id, amount: newAmount });
        } else if (newAmount > 0) {
          await createAllocation.mutateAsync({ category_id: row.category.id, amount: newAmount });
        }
      }

      onClose();
    } catch {
      // error handled by mutation
    }
  };

  const isPending = updateCategory.isPending || createAllocation.isPending || updateAllocation.isPending;

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
          <div className="space-y-1.5">
            <Label htmlFor="edit_budget">예산 금액</Label>
            <Input
              id="edit_budget"
              type="number"
              min="0"
              value={budgetAmount}
              onChange={(e) => setBudgetAmount(e.target.value)}
              placeholder="0 (미배분)"
            />
            {!row.allocation && (
              <p className="text-xs text-muted-foreground">현재 미배분 상태입니다. 금액 입력 시 배분이 생성됩니다.</p>
            )}
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

// ─── Unified Category Row ──────────────────────────────────────────────────────

interface UnifiedCategoryRowProps {
  row: UnifiedCategoryRow;
  onEdit: () => void;
  onDelete: () => void;
}

function UnifiedCategoryRowItem({ row, onEdit, onDelete }: UnifiedCategoryRowProps) {
  const { category, allocated, spent, status } = row;
  const hasAllocation = row.allocation !== null;
  const usageRate = allocated > 0 ? Math.min(spent / allocated, 1) : 0;
  const isExceeded = hasAllocation && spent > allocated;
  const remaining = allocated - spent;

  const progressColor = isExceeded
    ? 'bg-destructive'
    : status === 'warning'
      ? 'bg-amber-500'
      : 'bg-primary';

  return (
    <div className={`rounded-lg border bg-card px-4 py-3 space-y-2 ${!hasAllocation ? 'border-dashed bg-card/50' : ''}`}>
      {/* 상단 행: 카테고리 정보 + 상태 + 버튼 */}
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
          {!hasAllocation && (
            <span className="text-xs rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground shrink-0">미배분</span>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={status} />
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

      {/* 예산 정보 */}
      <div className="space-y-1">
        {hasAllocation ? (
          <>
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
            <div className="text-right text-xs text-muted-foreground">
              예산: {formatCurrency(allocated)}
            </div>
          </>
        ) : spent > 0 ? (
          <div className="text-xs text-muted-foreground">
            이번 달 지출: {formatCurrency(spent)}
          </div>
        ) : null}
      </div>
    </div>
  );
}

// ─── Unified Category Section ──────────────────────────────────────────────────

interface UnifiedCategorySectionProps {
  rows: UnifiedCategoryRow[];
  isLoading: boolean;
  onOpenPreset: () => void;
  onOpenAdd: () => void;
}

function UnifiedCategorySection({ rows, isLoading, onOpenPreset, onOpenAdd }: UnifiedCategorySectionProps) {
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
          <Button size="sm" variant="outline" onClick={onOpenPreset}>
            <Settings className="mr-1.5 h-3.5 w-3.5" />
            기본값 설정
          </Button>
        </div>
      </div>

      {/* 목록 */}
      {rows.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <p className="text-muted-foreground">지출 카테고리가 없습니다.</p>
            <p className="mt-1 text-xs text-muted-foreground">
              [+ 추가] 또는 [기본값 설정]으로 카테고리를 만들어보세요.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {rows.map((row) => (
            <UnifiedCategoryRowItem
              key={row.category.id}
              row={row}
              onEdit={() => setEditTarget(row)}
              onDelete={() => setConfirmDeleteCatId(row.category.id)}
            />
          ))}
        </div>
      )}

      {/* 편집 다이얼로그 */}
      {editTarget && (
        <EditCategoryDialog
          row={editTarget}
          isOpen={editTarget !== null}
          onClose={() => setEditTarget(null)}
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
// 카테고리별 소진율 카드는 UnifiedCategorySection으로 이동했으므로 제거

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
  const { data: allCategories = [], isLoading: catLoading } = useCategories();
  const { data: expenseCategories = [], isLoading: expCatLoading } = useCategories('expense');
  const { data: analysis, isLoading: analysisLoading } = useBudgetAnalysis();
  const { data: overview } = useBudgetOverview();

  const [showPeriodSettings, setShowPeriodSettings] = useState(false);
  const [showPreset, setShowPreset] = useState(false);
  const [showAddCategory, setShowAddCategory] = useState(false);

  // 기존 카테고리명 Set (프리셋 중복 체크용)
  const existingCategoryNames = new Set<string>(allCategories.map((c) => c.name));

  const isLoading = catBudgetLoading || expCatLoading || catLoading || analysisLoading;

  // 카테고리 + 배분 + 분석 데이터 통합
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
    };
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">예산 관리</h1>
      </div>

      {/* Section 1: Overview */}
      <OverviewCard onPeriodSettingsClick={() => setShowPeriodSettings(true)} />

      {/* Section 2: 카테고리별 예산 (통합) */}
      <div className="space-y-3">
        <UnifiedCategorySection
          rows={unifiedRows}
          isLoading={isLoading}
          onOpenPreset={() => setShowPreset(true)}
          onOpenAdd={() => setShowAddCategory(true)}
        />
      </div>

      {/* Section 3: 예산 분석 (카테고리별 소진율 카드 제외) */}
      <AnalysisSection />

      {/* 기간 설정 모달 */}
      <PeriodSettingsDialog
        isOpen={showPeriodSettings}
        onClose={() => setShowPeriodSettings(false)}
        currentDay={overview?.period_start_day ?? 1}
      />

      {/* 프리셋 모달 */}
      <PresetDialog
        isOpen={showPreset}
        onClose={() => setShowPreset(false)}
        existingNames={existingCategoryNames}
      />

      {/* 카테고리 추가 모달 */}
      <AddCategoryDialog
        isOpen={showAddCategory}
        onClose={() => setShowAddCategory(false)}
      />
    </div>
  );
}
