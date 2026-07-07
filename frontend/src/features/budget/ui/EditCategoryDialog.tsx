import { useState, useEffect } from 'react';
import { useUpdateCategory } from '@/features/categories/api';
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/shared/ui/dialog';

const CARRYOVER_TYPES: CarryoverType[] = ['expire', 'next_month', 'savings', 'transfer', 'deposit'];
const TRANSFER_TARGET_TYPES = new Set(['cash', 'parking']);
const SOURCE_ACCOUNT_TYPES = new Set(['cash', 'parking', 'investment']);

interface EditCategoryDialogProps {
  category: Category;
  carryover: CarryoverSettingResponse | null;
  accounts: Account[];
  isOpen: boolean;
  onClose: () => void;
  onCarryoverSave: (data: CarryoverSettingCreate) => void;
  isSavingCarryover: boolean;
}

export function EditCategoryDialog({
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
