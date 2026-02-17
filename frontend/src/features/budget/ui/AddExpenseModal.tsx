import { useState } from 'react';
import type { BudgetCategory, ExpenseCreateRequest, PaymentMethod } from '@/shared/types';
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
  onSubmit: (data: ExpenseCreateRequest) => void;
  isLoading?: boolean;
}

export function AddExpenseModal({ categories, isOpen, onClose, onSubmit, isLoading }: Props) {
  const [categoryId, setCategoryId] = useState('');
  const [amount, setAmount] = useState('');
  const [memo, setMemo] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | ''>('');
  const [tags, setTags] = useState('');
  const [spentAt, setSpentAt] = useState(new Date().toISOString().slice(0, 10));

  const activeCategories = categories.filter((c) => c.is_active);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryId || !amount || !spentAt) return;

    onSubmit({
      category_id: categoryId,
      amount: Number(amount),
      memo: memo || undefined,
      payment_method: paymentMethod || undefined,
      tags: tags || undefined,
      spent_at: spentAt,
    });

    // 리셋
    setCategoryId('');
    setAmount('');
    setMemo('');
    setPaymentMethod('');
    setTags('');
    setSpentAt(new Date().toISOString().slice(0, 10));
    onClose();
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

          {/* 결제수단 */}
          <div className="space-y-2">
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

          {/* 태그 */}
          <div className="space-y-2">
            <Label htmlFor="tags">태그</Label>
            <Input
              id="tags"
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="쉼표로 구분 (예: 회식, 팀점심)"
              maxLength={200}
            />
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
              disabled={isLoading || !categoryId || !amount}
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
