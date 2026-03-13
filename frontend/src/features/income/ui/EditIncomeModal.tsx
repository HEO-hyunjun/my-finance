import { useState, useEffect } from 'react';
import type { AssetHolding, Income, IncomeUpdateRequest, IncomeType } from '@/shared/types';
import { INCOME_TYPE_LABELS } from '@/shared/types';
import { useAssetSummary } from '@/features/assets/api';
import { useUpdateIncome } from '../api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/dialog';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';

const ALLOWED_TARGET_TYPES = new Set(['cash_krw', 'deposit', 'parking']);

interface Props {
  income: Income;
  isOpen: boolean;
  onClose: () => void;
}

export function EditIncomeModal({ income, isOpen, onClose }: Props) {
  const [type, setType] = useState<IncomeType>(income.type);
  const [amount, setAmount] = useState(String(income.amount));
  const [description, setDescription] = useState(income.description);
  const [receivedAt, setReceivedAt] = useState(income.received_at);
  const [targetAssetId, setTargetAssetId] = useState(income.target_asset_id ?? '');

  const updateIncome = useUpdateIncome();
  const { data: assetSummary } = useAssetSummary();
  const targetAssets = (assetSummary?.holdings ?? []).filter(
    (h: AssetHolding) => ALLOWED_TARGET_TYPES.has(h.asset_type),
  );

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setType(income.type);
    setAmount(String(income.amount));
    setDescription(income.description);
    setReceivedAt(income.received_at);
    setTargetAssetId(income.target_asset_id ?? '');
  }, [income]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || !description || !receivedAt) return;

    const payload: IncomeUpdateRequest = {
      type,
      amount: Number(amount),
      description,
      received_at: receivedAt,
      target_asset_id: targetAssetId || undefined,
    };

    updateIncome.mutate(
      { id: income.id, data: payload },
      { onSuccess: () => onClose() },
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>수입 수정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-income-type">유형</Label>
            <select
              id="edit-income-type"
              value={type}
              onChange={(e) => setType(e.target.value as IncomeType)}
              required
              className="w-full rounded border border-border bg-background text-foreground px-3 py-2 text-sm"
            >
              {(
                Object.entries(INCOME_TYPE_LABELS) as [IncomeType, string][]
              ).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-income-amount">금액</Label>
            <Input
              id="edit-income-amount"
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              required
              min={1}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-income-description">설명</Label>
            <Input
              id="edit-income-description"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="월급, 프리랜서 수입 등"
              required
              maxLength={500}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-received-at">수입일</Label>
            <Input
              id="edit-received-at"
              type="date"
              value={receivedAt}
              onChange={(e) => setReceivedAt(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-target-asset">입금 자산 (선택)</Label>
            <select
              id="edit-target-asset"
              value={targetAssetId}
              onChange={(e) => setTargetAssetId(e.target.value)}
              className="w-full rounded border border-border bg-background text-foreground px-3 py-2 text-sm"
            >
              <option value="">선택 안함</option>
              {targetAssets.map((a: AssetHolding) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({(a.total_value_krw ?? 0).toLocaleString()}원)
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
              disabled={updateIncome.isPending || !amount || !description}
              className="flex-1"
            >
              {updateIncome.isPending ? '저장 중...' : '수정'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
