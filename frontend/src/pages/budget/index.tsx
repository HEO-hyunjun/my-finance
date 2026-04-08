import { useState, useCallback, useRef, useEffect } from 'react';
import {
  Plus,
  AlertCircle,
  TrendingDown,
  TrendingUp,
  Wallet,
  Settings,
  ChevronDown,
  ChevronUp,
  Pencil,
  Trash2,
  Check,
  X,
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

// ─── EditAllocationDialog ──────────────────────────────────────────────────────

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

// ─── Inline Amount Input ───────────────────────────────────────────────────────

interface InlineAmountInputProps {
  initialValue: number;
  onSave: (amount: number) => void;
  onCancel: () => void;
  isPending?: boolean;
}

function InlineAmountInput({ initialValue, onSave, onCancel, isPending }: InlineAmountInputProps) {
  const [value, setValue] = useState(initialValue > 0 ? String(initialValue) : '');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      const num = Number(value);
      if (!isNaN(num) && num >= 0) onSave(num);
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  const handleSave = () => {
    const num = Number(value);
    if (!isNaN(num) && num >= 0) onSave(num);
  };

  return (
    <div className="flex items-center gap-1">
      <Input
        ref={inputRef}
        type="number"
        min="0"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        className="h-7 w-32 text-sm"
        placeholder="금액 입력"
        disabled={isPending}
      />
      <Button
        variant="ghost"
        size="sm"
        className="h-7 w-7 p-0 text-green-600 hover:text-green-700"
        onClick={handleSave}
        disabled={isPending}
      >
        <Check className="h-3.5 w-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-7 w-7 p-0 text-muted-foreground"
        onClick={onCancel}
        disabled={isPending}
      >
        <X className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

// ─── Allocated Category Row ────────────────────────────────────────────────────

interface AllocatedCategoryRowProps {
  allocation: CategoryBudget;
  category: Category | undefined;
  onEdit: () => void;
  onDelete: () => void;
}

function AllocatedCategoryRow({ allocation, category, onEdit, onDelete }: AllocatedCategoryRowProps) {
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

// ─── Unallocated Category Row ──────────────────────────────────────────────────

interface UnallocatedCategoryRowProps {
  category: Category;
  spentFromAnalysis: number;
  onAllocate: (categoryId: string, amount: number) => void;
  isCreating: boolean;
}

function UnallocatedCategoryRow({ category, spentFromAnalysis, onAllocate, isCreating }: UnallocatedCategoryRowProps) {
  const [isEditing, setIsEditing] = useState(false);

  const handleSave = (amount: number) => {
    onAllocate(category.id, amount);
    setIsEditing(false);
  };

  return (
    <div className="rounded-lg border border-dashed bg-card/50 px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {category.icon && <span aria-hidden="true">{category.icon}</span>}
          {category.color && (
            <span
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: category.color }}
              aria-hidden="true"
            />
          )}
          <span className="font-medium text-muted-foreground">{category.name}</span>
          <span className="text-xs rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground">미배분</span>
        </div>
        {!isEditing && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 text-xs"
            onClick={() => setIsEditing(true)}
          >
            <Plus className="h-3 w-3" />
            배분 설정
          </Button>
        )}
      </div>

      {isEditing && (
        <div className="mt-2">
          <InlineAmountInput
            initialValue={0}
            onSave={handleSave}
            onCancel={() => setIsEditing(false)}
            isPending={isCreating}
          />
        </div>
      )}

      {spentFromAnalysis > 0 && (
        <p className="mt-1 text-xs text-muted-foreground">
          이번 달 지출: {formatCurrency(spentFromAnalysis)}
        </p>
      )}
    </div>
  );
}

// ─── Allocation Section ────────────────────────────────────────────────────────

interface AllocationSectionProps {
  expenseCategories: Category[];
  budgetCategories: CategoryBudget[];
  isLoading: boolean;
  analysisSpentMap: Map<string, number>;
}

function AllocationSection({
  expenseCategories,
  budgetCategories,
  isLoading,
  analysisSpentMap,
}: AllocationSectionProps) {
  const [editTarget, setEditTarget] = useState<CategoryBudget | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const createAllocation = useCreateAllocation();
  const deleteAllocation = useDeleteAllocation();

  const allocationMap = new Map<string, CategoryBudget>(
    budgetCategories.map((b) => [b.category_id, b]),
  );

  const handleConfirmDelete = useCallback(() => {
    if (confirmDeleteId) {
      deleteAllocation.mutate(confirmDeleteId);
      setConfirmDeleteId(null);
    }
  }, [confirmDeleteId, deleteAllocation]);

  const handleAllocate = (categoryId: string, amount: number) => {
    createAllocation.mutate({ category_id: categoryId, amount });
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  if (expenseCategories.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center py-12">
          <p className="text-muted-foreground">지출 카테고리가 없습니다.</p>
          <p className="mt-1 text-xs text-muted-foreground">아래 카테고리 관리에서 카테고리를 추가하세요.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {expenseCategories.map((cat) => {
          const alloc = allocationMap.get(cat.id);
          if (alloc) {
            return (
              <AllocatedCategoryRow
                key={cat.id}
                allocation={alloc}
                category={cat}
                onEdit={() => setEditTarget(alloc)}
                onDelete={() => setConfirmDeleteId(alloc.allocation_id)}
              />
            );
          }
          return (
            <UnallocatedCategoryRow
              key={cat.id}
              category={cat}
              spentFromAnalysis={analysisSpentMap.get(cat.id) ?? 0}
              onAllocate={handleAllocate}
              isCreating={createAllocation.isPending}
            />
          );
        })}
      </div>

      {editTarget && (
        <EditAllocationDialog
          allocation={editTarget}
          categoryName={expenseCategories.find((c) => c.id === editTarget.category_id)?.name ?? editTarget.category_id}
          isOpen={editTarget !== null}
          onClose={() => setEditTarget(null)}
        />
      )}

      <ConfirmDialog
        open={confirmDeleteId !== null}
        onOpenChange={(open) => { if (!open) setConfirmDeleteId(null); }}
        title="예산 배분을 삭제하시겠습니까?"
        description="이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={handleConfirmDelete}
        variant="destructive"
      />
    </>
  );
}

// ─── Category Management Section ──────────────────────────────────────────────

interface CategoryManagementSectionProps {
  categories: Category[];
  onOpenPreset: () => void;
}

interface CategoryRowEditState {
  name: string;
  icon: string;
  color: string;
}

function CategoryManagementSection({ categories, onOpenPreset }: CategoryManagementSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editState, setEditState] = useState<CategoryRowEditState>({ name: '', icon: '', color: '' });
  const [confirmDeleteCatId, setConfirmDeleteCatId] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newCat, setNewCat] = useState<CategoryRowEditState>({ name: '', icon: '', color: '#6366f1' });

  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();

  const expenseCategories = categories.filter((c) => c.direction === 'expense');

  const startEdit = (cat: Category) => {
    setEditingId(cat.id);
    setEditState({ name: cat.name, icon: cat.icon ?? '', color: cat.color ?? '#6366f1' });
  };

  const cancelEdit = () => {
    setEditingId(null);
  };

  const saveEdit = (id: string) => {
    updateCategory.mutate(
      { id, name: editState.name, icon: editState.icon || null, color: editState.color || null },
      { onSuccess: () => setEditingId(null) },
    );
  };

  const handleAdd = () => {
    if (!newCat.name.trim()) return;
    createCategory.mutate(
      { direction: 'expense', name: newCat.name.trim(), icon: newCat.icon || null, color: newCat.color || null },
      {
        onSuccess: () => {
          setNewCat({ name: '', icon: '', color: '#6366f1' });
          setShowAddForm(false);
        },
      },
    );
  };

  const handleConfirmDeleteCat = useCallback(() => {
    if (confirmDeleteCatId) {
      deleteCategory.mutate(confirmDeleteCatId);
      setConfirmDeleteCatId(null);
    }
  }, [confirmDeleteCatId, deleteCategory]);

  return (
    <div className="space-y-3">
      <button
        type="button"
        className="flex w-full items-center justify-between text-lg font-semibold"
        onClick={() => setIsExpanded((v) => !v)}
      >
        <span>카테고리 관리</span>
        {isExpanded ? <ChevronUp className="h-5 w-5 text-muted-foreground" /> : <ChevronDown className="h-5 w-5 text-muted-foreground" />}
      </button>

      {isExpanded && (
        <Card>
          <CardContent className="pt-4 space-y-3">
            {/* 액션 버튼 영역 */}
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowAddForm((v) => !v)}
              >
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                카테고리 추가
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={onOpenPreset}
              >
                <Settings className="mr-1.5 h-3.5 w-3.5" />
                기본값 설정
              </Button>
            </div>

            {/* 추가 폼 */}
            {showAddForm && (
              <div className="rounded-lg border border-dashed p-3 space-y-2 bg-muted/30">
                <p className="text-xs font-medium text-muted-foreground">새 카테고리</p>
                <div className="grid grid-cols-[1fr_auto_auto] gap-2 items-center">
                  <Input
                    placeholder="카테고리명"
                    value={newCat.name}
                    onChange={(e) => setNewCat((s) => ({ ...s, name: e.target.value }))}
                    className="h-8 text-sm"
                    onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); if (e.key === 'Escape') setShowAddForm(false); }}
                  />
                  <Input
                    placeholder="아이콘"
                    value={newCat.icon}
                    onChange={(e) => setNewCat((s) => ({ ...s, icon: e.target.value }))}
                    className="h-8 w-16 text-center text-sm"
                  />
                  <input
                    type="color"
                    value={newCat.color}
                    onChange={(e) => setNewCat((s) => ({ ...s, color: e.target.value }))}
                    className="h-8 w-8 cursor-pointer rounded border"
                    title="색상 선택"
                  />
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={handleAdd} disabled={!newCat.name.trim() || createCategory.isPending}>
                    {createCategory.isPending ? '추가 중...' : '추가'}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setShowAddForm(false)}>취소</Button>
                </div>
              </div>
            )}

            {/* 카테고리 목록 */}
            {expenseCategories.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                지출 카테고리가 없습니다.
              </p>
            ) : (
              <div className="space-y-2">
                {expenseCategories.map((cat) => (
                  <div key={cat.id} className="rounded-lg border bg-card px-3 py-2">
                    {editingId === cat.id ? (
                      <div className="space-y-2">
                        <div className="grid grid-cols-[1fr_auto_auto] gap-2 items-center">
                          <Input
                            value={editState.name}
                            onChange={(e) => setEditState((s) => ({ ...s, name: e.target.value }))}
                            className="h-8 text-sm"
                            onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(cat.id); if (e.key === 'Escape') cancelEdit(); }}
                          />
                          <Input
                            value={editState.icon}
                            onChange={(e) => setEditState((s) => ({ ...s, icon: e.target.value }))}
                            className="h-8 w-16 text-center text-sm"
                            placeholder="아이콘"
                          />
                          <input
                            type="color"
                            value={editState.color}
                            onChange={(e) => setEditState((s) => ({ ...s, color: e.target.value }))}
                            className="h-8 w-8 cursor-pointer rounded border"
                            title="색상 선택"
                          />
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" onClick={() => saveEdit(cat.id)} disabled={!editState.name.trim() || updateCategory.isPending}>
                            {updateCategory.isPending ? '저장 중...' : '저장'}
                          </Button>
                          <Button size="sm" variant="outline" onClick={cancelEdit}>취소</Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {cat.icon && <span aria-hidden="true" className="text-base">{cat.icon}</span>}
                          {cat.color && (
                            <span
                              className="inline-block h-3 w-3 shrink-0 rounded-full"
                              style={{ backgroundColor: cat.color }}
                              aria-hidden="true"
                            />
                          )}
                          <span className="text-sm font-medium">{cat.name}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0"
                            onClick={() => startEdit(cat)}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                            onClick={() => setConfirmDeleteCatId(cat.id)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <ConfirmDialog
        open={confirmDeleteCatId !== null}
        onOpenChange={(open) => { if (!open) setConfirmDeleteCatId(null); }}
        title="카테고리를 삭제하시겠습니까?"
        description="이 카테고리에 연결된 예산 배분도 함께 삭제될 수 있습니다."
        confirmLabel="삭제"
        onConfirm={handleConfirmDeleteCat}
        variant="destructive"
      />
    </div>
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

  // dialog가 열릴 때 preset 상태 초기화
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
  const { data: analysis } = useBudgetAnalysis();
  const { data: overview } = useBudgetOverview();

  const [showPeriodSettings, setShowPeriodSettings] = useState(false);
  const [showPreset, setShowPreset] = useState(false);

  // 분석 데이터에서 카테고리별 지출 맵 생성
  const analysisSpentMap = new Map<string, number>(
    (analysis?.category_rates ?? []).map((r) => [r.category_id, r.spent]),
  );

  // 기존 카테고리명 Set (프리셋 중복 체크용)
  const existingCategoryNames = new Set<string>(allCategories.map((c) => c.name));

  const isLoading = catBudgetLoading || expCatLoading || catLoading;

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">예산 관리</h1>
      </div>

      {/* Section 1: Overview */}
      <OverviewCard onPeriodSettingsClick={() => setShowPeriodSettings(true)} />

      {/* Section 2: 카테고리 예산 배분 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">카테고리 예산 배분</h2>
        </div>

        <AllocationSection
          expenseCategories={expenseCategories}
          budgetCategories={budgetCategories}
          isLoading={isLoading}
          analysisSpentMap={analysisSpentMap}
        />
      </div>

      {/* Section 3: 카테고리 관리 */}
      <CategoryManagementSection
        categories={allCategories}
        onOpenPreset={() => setShowPreset(true)}
      />

      {/* Section 4: 예산 분석 */}
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
    </div>
  );
}
