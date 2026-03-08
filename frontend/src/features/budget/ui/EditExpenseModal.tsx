import { useState, useEffect } from 'react';
import type { AssetHolding, BudgetCategory, Expense, ExpenseUpdateRequest } from '@/shared/types';
import { useAssetSummary } from '@/features/assets/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/dialog';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';

const ALLOWED_SOURCE_TYPES = new Set(['cash_krw', 'deposit', 'parking']);

interface Props {
  expense: Expense;
  categories: BudgetCategory[];
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { id: string; data: ExpenseUpdateRequest }) => void;
  isLoading?: boolean;
}

export function EditExpenseModal({ expense, categories, isOpen, onClose, onSubmit, isLoading }: Props) {
  const [categoryId, setCategoryId] = useState(expense.category_id ?? '');
  const [amount, setAmount] = useState(String(expense.amount));
  const [memo, setMemo] = useState(expense.memo ?? '');
  const [spentAt, setSpentAt] = useState(expense.spent_at);
  const [sourceAssetId, setSourceAssetId] = useState(expense.source_asset_id ?? '');

  const { data: assetSummary } = useAssetSummary();
  const sourceAssets = (assetSummary?.holdings ?? []).filter(
    (h: AssetHolding) => ALLOWED_SOURCE_TYPES.has(h.asset_type),
  );

  const activeCategories = categories.filter((c) => c.is_active);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setCategoryId(expense.category_id ?? '');
    setAmount(String(expense.amount));
    setMemo(expense.memo ?? '');
    setSpentAt(expense.spent_at);
    setSourceAssetId(expense.source_asset_id ?? '');
  }, [expense]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || !spentAt) return;

    onSubmit({
      id: expense.id,
      data: {
        category_id: categoryId || undefined,
        amount: Number(amount),
        memo: memo || undefined,
        spent_at: spentAt,
        source_asset_id: sourceAssetId || undefined,
      },
    });
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>지출 수정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-category">카테고리</Label>
            <select
              id="edit-category"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              className="w-full rounded border border-border bg-background text-foreground px-3 py-2 text-sm"
            >
              <option value="">미분류</option>
              {activeCategories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.icon} {c.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-amount">금액</Label>
            <Input
              id="edit-amount"
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              required
              min={1}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-memo">메모</Label>
            <Input
              id="edit-memo"
              type="text"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="점심식사, 택시비 등"
              maxLength={500}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-source-asset">출금 자산</Label>
            <select
              id="edit-source-asset"
              value={sourceAssetId}
              onChange={(e) => setSourceAssetId(e.target.value)}
              className="w-full rounded border border-border bg-background text-foreground px-3 py-2 text-sm"
            >
              <option value="">선택 (선택사항)</option>
              {sourceAssets.map((a: AssetHolding) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({(a.total_value_krw ?? 0).toLocaleString()}원)
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-spent-at">날짜</Label>
            <Input
              id="edit-spent-at"
              type="date"
              value={spentAt}
              onChange={(e) => setSpentAt(e.target.value)}
              required
            />
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1"
            >
              취소
            </Button>
            <Button
              type="submit"
              disabled={isLoading || !amount}
              className="flex-1"
            >
              {isLoading ? '저장 중...' : '수정'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
