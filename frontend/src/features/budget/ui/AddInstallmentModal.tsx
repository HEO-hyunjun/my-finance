import { useState } from 'react';
import type { BudgetCategory, InstallmentCreateRequest, PaymentMethod } from '@/shared/types';
import { PAYMENT_METHOD_LABELS } from '@/shared/types';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/dialog';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';
import { cn } from '@/shared/lib/utils';

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
  const [totalInstallments, setTotalInstallments] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | ''>('');

  const activeCategories = categories.filter((c) => c.is_active);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryId || !name || !totalAmount || !monthlyAmount || !paymentDay || !totalInstallments || !startDate || !endDate) return;

    onSubmit({
      category_id: categoryId,
      name,
      total_amount: Number(totalAmount),
      monthly_amount: Number(monthlyAmount),
      payment_day: Number(paymentDay),
      total_installments: Number(totalInstallments),
      start_date: startDate,
      end_date: endDate,
      payment_method: paymentMethod || undefined,
    });

    setCategoryId('');
    setName('');
    setTotalAmount('');
    setMonthlyAmount('');
    setPaymentDay('');
    setTotalInstallments('');
    setStartDate('');
    setEndDate('');
    setPaymentMethod('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] max-w-md overflow-y-auto">
        <DialogHeader>
          <DialogTitle>할부금 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
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

          <div>
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
            <div>
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
            <div>
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
            <div>
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
            <div>
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
            <div>
              <Label htmlFor="start-date">시작일</Label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
            </div>
            <div>
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

          <div>
            <Label>결제수단</Label>
            <div className="flex gap-2">
              {(Object.entries(PAYMENT_METHOD_LABELS) as [PaymentMethod, string][]).map(
                ([method, label]) => (
                  <button
                    key={method}
                    type="button"
                    onClick={() => setPaymentMethod(paymentMethod === method ? '' : method)}
                    className={cn(
                      'rounded-full border px-3 py-1 text-sm transition',
                      paymentMethod === method
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border hover:bg-accent',
                    )}
                  >
                    {label}
                  </button>
                ),
              )}
            </div>
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
              disabled={isLoading || !categoryId || !name || !totalAmount || !monthlyAmount || !paymentDay || !totalInstallments || !startDate || !endDate}
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
