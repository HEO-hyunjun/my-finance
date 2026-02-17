import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { useIncomes, useIncomeSummary, useCreateIncome, useDeleteIncome } from '../api/income';
import type { IncomeType, IncomeCreateRequest } from '@/shared/types';
import { INCOME_TYPE_LABELS } from '@/shared/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/dialog';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW } from '@/shared/lib/format';

function AddIncomeModal({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: IncomeCreateRequest) => void;
  isSubmitting: boolean;
}) {
  const [type, setType] = useState<IncomeType>('salary');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [isRecurring, setIsRecurring] = useState(true);
  const [recurringDay, setRecurringDay] = useState('25');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || !description) return;
    onSubmit({
      type,
      amount: Number(amount),
      description,
      is_recurring: isRecurring,
      recurring_day: isRecurring ? Number(recurringDay) : undefined,
      received_at: new Date().toISOString().slice(0, 10),
    });
    setType('salary');
    setAmount('');
    setDescription('');
    setIsRecurring(true);
    setRecurringDay('25');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>수입 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>유형</Label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as IncomeType)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              {Object.entries(INCOME_TYPE_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label>설명</Label>
            <Input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="예: 회사 급여"
            />
          </div>

          <div>
            <Label>금액</Label>
            <Input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              min="0"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              id="is-recurring"
              type="checkbox"
              checked={isRecurring}
              onChange={(e) => setIsRecurring(e.target.checked)}
              className="h-4 w-4 rounded border-border"
            />
            <Label htmlFor="is-recurring" className="font-normal cursor-pointer">
              매월 반복
            </Label>
          </div>

          {isRecurring && (
            <div>
              <Label>수령일</Label>
              <Input
                type="number"
                value={recurringDay}
                onChange={(e) => setRecurringDay(e.target.value)}
                min="1"
                max="31"
              />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={!amount || !description || isSubmitting}>
              {isSubmitting ? '추가 중...' : '추가'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function IncomeSection() {
  const [modalOpen, setModalOpen] = useState(false);
  const { data: incomes, isLoading } = useIncomes({ is_recurring: true });
  const { data: summary } = useIncomeSummary();
  const createIncome = useCreateIncome();
  const deleteIncome = useDeleteIncome();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>수입 관리</CardTitle>
        <Button onClick={() => setModalOpen(true)}>수입 추가</Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {summary && (
          <div className="rounded-md bg-primary/10 px-4 py-3">
            <p className="text-sm text-muted-foreground">월 총 수입</p>
            <p className="text-xl font-bold text-primary">
              {formatKRW(summary.total_monthly_income)}원
            </p>
            <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
              {summary.salary_income > 0 && (
                <span>급여 {formatKRW(summary.salary_income)}원</span>
              )}
              {summary.side_income > 0 && (
                <span>부수입 {formatKRW(summary.side_income)}원</span>
              )}
              {summary.investment_income > 0 && (
                <span>투자수익 {formatKRW(summary.investment_income)}원</span>
              )}
              {summary.other_income > 0 && (
                <span>기타 {formatKRW(summary.other_income)}원</span>
              )}
            </div>
          </div>
        )}

        {(!incomes || incomes.length === 0) ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            등록된 반복 수입이 없습니다.
          </p>
        ) : (
          <ul className="space-y-3">
            {incomes.map((income) => (
              <li
                key={income.id}
                className="flex items-center justify-between rounded-md border border-border px-4 py-3"
              >
                <div>
                  <p className="text-sm font-medium">{income.description}</p>
                  <p className="text-xs text-muted-foreground">
                    {INCOME_TYPE_LABELS[income.type]}
                    {income.recurring_day && ` · 매월 ${income.recurring_day}일`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold">
                    {formatKRW(income.amount)}원
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteIncome.mutate(income.id)}
                    disabled={deleteIncome.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <AddIncomeModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          onSubmit={(data) => createIncome.mutate(data)}
          isSubmitting={createIncome.isPending}
        />
      </CardContent>
    </Card>
  );
}
