import { useState } from 'react';
import type { BudgetCategory, FixedExpenseCreateRequest, PaymentMethod } from '@/shared/types';
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
  onSubmit: (data: FixedExpenseCreateRequest) => void;
  isLoading?: boolean;
}

export function AddFixedExpenseModal({ categories, isOpen, onClose, onSubmit, isLoading }: Props) {
  const [categoryId, setCategoryId] = useState('');
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [paymentDay, setPaymentDay] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | ''>('');

  const activeCategories = categories.filter((c) => c.is_active);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryId || !name || !amount || !paymentDay) return;

    onSubmit({
      category_id: categoryId,
      name,
      amount: Number(amount),
      payment_day: Number(paymentDay),
      payment_method: paymentMethod || undefined,
    });

    setCategoryId('');
    setName('');
    setAmount('');
    setPaymentDay('');
    setPaymentMethod('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>고정비 추가</DialogTitle>
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
              placeholder="월세, 넷플릭스, 통신비 등"
              required
              maxLength={100}
            />
          </div>

          <div>
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
