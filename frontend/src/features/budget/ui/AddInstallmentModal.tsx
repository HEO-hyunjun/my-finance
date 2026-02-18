import { useState } from 'react';
import type { AssetHolding, BudgetCategory, InstallmentCreateRequest } from '@/shared/types';
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
  onSubmit: (data: InstallmentCreateRequest) => void;
  isLoading?: boolean;
}

export function AddInstallmentModal({ categories, isOpen, onClose, onSubmit, isLoading }: Props) {
  const [categoryId, setCategoryId] = useState('');
  const [name, setName] = useState('');
  const [totalAmount, setTotalAmount] = useState('');
  const [monthlyAmount, setMonthlyAmount] = useState('');
  const [paymentDay, setPaymentDay] = useState('');
  const [isMonthEnd, setIsMonthEnd] = useState(false);
  const [totalInstallments, setTotalInstallments] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [sourceAssetId, setSourceAssetId] = useState('');

  const { data: assetSummary } = useAssetSummary();
  const sourceAssets = (assetSummary?.holdings ?? []).filter(
    (h: AssetHolding) => ALLOWED_SOURCE_TYPES.has(h.asset_type),
  );

  const activeCategories = categories.filter((c) => c.is_active);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryId || !name || !totalAmount || !monthlyAmount || (!isMonthEnd && !paymentDay) || !totalInstallments || !startDate || !endDate) return;

    onSubmit({
      category_id: categoryId,
      name,
      total_amount: Number(totalAmount),
      monthly_amount: Number(monthlyAmount),
      payment_day: isMonthEnd ? 0 : Number(paymentDay),
      total_installments: Number(totalInstallments),
      start_date: startDate,
      end_date: endDate,
      source_asset_id: sourceAssetId || undefined,
    });

    setCategoryId('');
    setName('');
    setTotalAmount('');
    setMonthlyAmount('');
    setPaymentDay('');
    setIsMonthEnd(false);
    setTotalInstallments('');
    setStartDate('');
    setEndDate('');
    setSourceAssetId('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] max-w-md overflow-y-auto">
        <DialogHeader>
          <DialogTitle>할부금 추가</DialogTitle>
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
              placeholder="노트북 할부, 가전제품 등"
              required
              maxLength={100}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="total-amount">총 금액</Label>
              <Input
                id="total-amount"
                type="number"
                value={totalAmount}
                onChange={(e) => setTotalAmount(e.target.value)}
                placeholder="0"
                required
                min={1}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="monthly-amount">월 납부액</Label>
              <Input
                id="monthly-amount"
                type="number"
                value={monthlyAmount}
                onChange={(e) => setMonthlyAmount(e.target.value)}
                placeholder="0"
                required
                min={1}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="payment-day">결제일 (매월)</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="payment-day"
                  type="number"
                  value={isMonthEnd ? '' : paymentDay}
                  onChange={(e) => setPaymentDay(e.target.value)}
                  placeholder="1~31"
                  required={!isMonthEnd}
                  disabled={isMonthEnd}
                  min={1}
                  max={31}
                  className="flex-1"
                />
                <label className="flex items-center gap-1 text-sm whitespace-nowrap cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isMonthEnd}
                    onChange={(e) => {
                      setIsMonthEnd(e.target.checked);
                      if (e.target.checked) setPaymentDay('');
                    }}
                    className="h-4 w-4 rounded border-border"
                  />
                  말일
                </label>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="total-installments">총 개월수</Label>
              <Input
                id="total-installments"
                type="number"
                value={totalInstallments}
                onChange={(e) => setTotalInstallments(e.target.value)}
                placeholder="12"
                required
                min={1}
                max={120}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="start-date">시작일</Label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end-date">종료일</Label>
              <Input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </div>
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
              disabled={isLoading || !categoryId || !name || !totalAmount || !monthlyAmount || (!isMonthEnd && !paymentDay) || !totalInstallments || !startDate || !endDate}
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
