import { useState } from 'react';
import type { AssetHolding, BudgetCategory, ExpenseCreateRequest } from '@/shared/types';
import { useAssetSummary } from '@/features/assets/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/dialog';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';

const ALLOWED_SOURCE_TYPES = new Set(['cash_krw', 'deposit', 'parking']);

interface Props {
  categories: BudgetCategory[];
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: ExpenseCreateRequest) => void;
  isLoading?: boolean;
}

export function AddExpenseModal({ categories, isOpen, onClose, onSubmit, isLoading }: Props) {
  const [categoryId, setCategoryId] = useState('');
  const [amount, setAmount] = useState('');
  const [memo, setMemo] = useState('');
  const [spentAt, setSpentAt] = useState(new Date().toISOString().slice(0, 10));
  const [sourceAssetId, setSourceAssetId] = useState('');

  const { data: assetSummary } = useAssetSummary();
  const sourceAssets = (assetSummary?.holdings ?? []).filter(
    (h: AssetHolding) => ALLOWED_SOURCE_TYPES.has(h.asset_type),
  );

  const activeCategories = categories.filter((c) => c.is_active);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryId || !amount || !spentAt || !sourceAssetId) return;

    onSubmit({
      category_id: categoryId,
      amount: Number(amount),
      memo: memo || undefined,
      spent_at: spentAt,
      source_asset_id: sourceAssetId,
    });

    // 금액·메모만 리셋 (카테고리·출금자산·날짜는 유지)
    setAmount('');
    setMemo('');
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>지출 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 카테고리 */}
          <div className="space-y-2">
            <Label htmlFor="category">카테고리</Label>
            <select
              id="category"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              required
              className="w-full rounded border border-border bg-background text-foreground px-3 py-2 text-sm"
            >
              <option value="">선택</option>
              {activeCategories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.icon} {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* 금액 */}
          <div className="space-y-2">
            <Label htmlFor="amount">금액</Label>
            <Input
              id="amount"
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              required
              min={1}
            />
          </div>

          {/* 메모 */}
          <div className="space-y-2">
            <Label htmlFor="memo">메모</Label>
            <Input
              id="memo"
              type="text"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="점심식사, 택시비 등"
              maxLength={500}
            />
          </div>

          {/* 출금 자산 */}
          <div className="space-y-2">
            <Label htmlFor="source-asset">출금 자산</Label>
            <select
              id="source-asset"
              value={sourceAssetId}
              onChange={(e) => setSourceAssetId(e.target.value)}
              required
              className="w-full rounded border border-border bg-background text-foreground px-3 py-2 text-sm"
            >
              <option value="">선택</option>
              {sourceAssets.map((a: AssetHolding) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({(a.total_value_krw ?? 0).toLocaleString()}원)
                </option>
              ))}
            </select>
          </div>

          {/* 날짜 */}
          <div className="space-y-2">
            <Label htmlFor="spent-at">날짜</Label>
            <Input
              id="spent-at"
              type="date"
              value={spentAt}
              onChange={(e) => setSpentAt(e.target.value)}
              required
            />
          </div>

          {/* 버튼 */}
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
              disabled={isLoading || !categoryId || !amount || !sourceAssetId}
              className="flex-1"
            >
              {isLoading ? '저장 중...' : '저장'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
