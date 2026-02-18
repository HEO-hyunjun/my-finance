import { useState } from 'react';
import type { AssetHolding, BudgetCategory, FixedExpenseCreateRequest } from '@/shared/types';
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
  onSubmit: (data: FixedExpenseCreateRequest) => void;
  isLoading?: boolean;
}

export function AddFixedExpenseModal({ categories, isOpen, onClose, onSubmit, isLoading }: Props) {
  const [categoryId, setCategoryId] = useState('');
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [paymentDay, setPaymentDay] = useState('');
  const [sourceAssetId, setSourceAssetId] = useState('');

  const { data: assetSummary } = useAssetSummary();
  const sourceAssets = (assetSummary?.holdings ?? []).filter(
    (h: AssetHolding) => ALLOWED_SOURCE_TYPES.has(h.asset_type),
  );

  const activeCategories = categories.filter((c) => c.is_active);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryId || !name || !amount || !paymentDay) return;

    onSubmit({
      category_id: categoryId,
      name,
      amount: Number(amount),
      payment_day: Number(paymentDay),
      source_asset_id: sourceAssetId || undefined,
    });

    setCategoryId('');
    setName('');
    setAmount('');
    setPaymentDay('');
    setSourceAssetId('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>고정비 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
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

          <div className="space-y-2">
            <Label htmlFor="name">이름</Label>
            <Input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="월세, 넷플릭스, 통신비 등"
              required
              maxLength={100}
            />
          </div>

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

          <div className="space-y-2">
            <Label htmlFor="payment-day">결제일 (매월)</Label>
            <Input
              id="payment-day"
              type="number"
              value={paymentDay}
              onChange={(e) => setPaymentDay(e.target.value)}
              placeholder="1~31"
              required
              min={1}
              max={31}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="source-asset">출금 자산</Label>
            <select
              id="source-asset"
              value={sourceAssetId}
              onChange={(e) => setSourceAssetId(e.target.value)}
              className="w-full rounded border border-border bg-background text-foreground px-3 py-2 text-sm"
            >
              <option value="">선택 (선택사항)</option>
              {sourceAssets.map((a: AssetHolding) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({(a.principal ?? 0).toLocaleString()}원)
                </option>
              ))}
            </select>
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
              disabled={isLoading || !categoryId || !name || !amount || !paymentDay}
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
