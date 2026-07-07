import { useState, useEffect } from 'react';
import { useCreateAllocation, useUpdateAllocation } from '@/features/budget/api';
import { formatCurrency } from '@/features/budget/lib/format';
import type { UnifiedCategoryRow } from '@/features/budget/model/unified-row';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/shared/ui/dialog';

interface BatchAllocationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  rows: UnifiedCategoryRow[];
  availableBudget: number;
}

export function BatchAllocationDialog({ isOpen, onClose, rows, availableBudget }: BatchAllocationDialogProps) {
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
