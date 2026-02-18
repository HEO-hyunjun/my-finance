import { useState, useEffect } from 'react';
import type { AssetHolding, IncomeCreateRequest, IncomeType } from '@/shared/types';
import { INCOME_TYPE_LABELS } from '@/shared/types';
import { useAssetSummary } from '@/features/assets/api';
import { useProfile } from '@/features/settings/api';
import { useCreateIncome } from '../api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/dialog';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';

const ALLOWED_TARGET_TYPES = new Set(['cash_krw', 'deposit', 'parking']);

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function AddIncomeModal({ isOpen, onClose }: Props) {
  const [type, setType] = useState<IncomeType>('salary');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [isRecurring, setIsRecurring] = useState(false);
  const [recurringDay, setRecurringDay] = useState('');
  const [receivedAt, setReceivedAt] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [targetAssetId, setTargetAssetId] = useState('');

  const createIncome = useCreateIncome();
  const { data: assetSummary } = useAssetSummary();
  const { data: profile } = useProfile();
  const targetAssets = (assetSummary?.holdings ?? []).filter(
    (h: AssetHolding) => ALLOWED_TARGET_TYPES.has(h.asset_type),
  );

  // 급여 유형 선택 시 설정값 자동 적용
  useEffect(() => {
    if (type === 'salary' && profile) {
      if (profile.salary_amount) setAmount(profile.salary_amount.toString());
      if (profile.salary_asset_id) setTargetAssetId(profile.salary_asset_id);
      setDescription('급여');
      setIsRecurring(true);
      if (profile.salary_day) setRecurringDay(profile.salary_day.toString());
    }
  }, [type, profile]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || !description || !receivedAt) return;

    const payload: IncomeCreateRequest = {
      type,
      amount: Number(amount),
      description,
      is_recurring: isRecurring,
      recurring_day: isRecurring && recurringDay ? Number(recurringDay) : undefined,
      received_at: receivedAt,
      target_asset_id: targetAssetId || undefined,
    };

    createIncome.mutate(payload, {
      onSuccess: () => {
        setType('salary');
        setAmount('');
        setDescription('');
        setIsRecurring(false);
        setRecurringDay('');
        setReceivedAt(new Date().toISOString().slice(0, 10));
        setTargetAssetId('');
        onClose();
      },
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>수입 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="income-type">유형</Label>
            <select
              id="income-type"
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
            <Label htmlFor="income-amount">금액</Label>
            <Input
              id="income-amount"
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              required
              min={1}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="income-description">설명</Label>
            <Input
              id="income-description"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="월급, 프리랜서 수입 등"
              required
              maxLength={500}
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is-recurring"
              checked={isRecurring}
              onChange={(e) => setIsRecurring(e.target.checked)}
              className="h-4 w-4 rounded border-border"
            />
            <Label htmlFor="is-recurring" className="text-sm font-medium">
              정기 수입
            </Label>
          </div>

          {isRecurring && (
            <div className="space-y-2">
              <Label htmlFor="recurring-day">매월 수입일</Label>
              <Input
                id="recurring-day"
                type="number"
                value={recurringDay}
                onChange={(e) => setRecurringDay(e.target.value)}
                placeholder="25"
                min={1}
                max={31}
              />
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="received-at">수입일</Label>
            <Input
              id="received-at"
              type="date"
              value={receivedAt}
              onChange={(e) => setReceivedAt(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="target-asset">입금 자산 (선택)</Label>
            <select
              id="target-asset"
              value={targetAssetId}
              onChange={(e) => setTargetAssetId(e.target.value)}
              className="w-full rounded border border-border bg-background text-foreground px-3 py-2 text-sm"
            >
              <option value="">선택 안함</option>
              {targetAssets.map((a: AssetHolding) => (
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
              disabled={createIncome.isPending || !amount || !description}
              className="flex-1"
            >
              {createIncome.isPending ? '저장 중...' : '저장'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
