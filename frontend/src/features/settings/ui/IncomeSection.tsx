import { useState } from 'react';
import { Trash2, ToggleLeft, ToggleRight } from 'lucide-react';
import {
  useRecurringIncomes,
  useIncomeSummary,
  useCreateRecurringIncome,
  useDeleteRecurringIncome,
  useToggleRecurringIncome,
} from '../api/income';
import type { RecurringIncomeCreateRequest } from '@/shared/types/settings';
import { INCOME_TYPE_LABELS } from '@/shared/types/settings';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/dialog';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW } from '@/shared/lib/format';

function AddRecurringIncomeModal({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: RecurringIncomeCreateRequest) => void;
  isSubmitting: boolean;
}) {
  const [incomeType, setIncomeType] = useState('salary');
  const [amount, setAmount] = useState('');
  const [name, setName] = useState('');
  const [day, setDay] = useState('25');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || !name || !day) return;
    onSubmit({
      income_type: incomeType,
      amount: Number(amount),
      name,
      day: Number(day),
    });
    setIncomeType('salary');
    setAmount('');
    setName('');
    setDay('25');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>정기 수입 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>유형</Label>
            <select
              value={incomeType}
              onChange={(e) => setIncomeType(e.target.value)}
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
            <Label>이름</Label>
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
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

          <div>
            <Label>매월 수령일</Label>
            <Input
              type="number"
              value={day}
              onChange={(e) => setDay(e.target.value)}
              min="1"
              max="31"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={!amount || !name || !day || isSubmitting}>
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
  const { data: recurringIncomes, isLoading } = useRecurringIncomes();
  const { data: summary } = useIncomeSummary();
  const createRecurring = useCreateRecurringIncome();
  const deleteRecurring = useDeleteRecurringIncome();
  const toggleRecurring = useToggleRecurringIncome();

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
        <CardTitle>정기 수입 관리</CardTitle>
        <Button onClick={() => setModalOpen(true)}>수입 추가</Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {summary && (
          <div className="rounded-md bg-primary/10 px-4 py-3">
            <p className="text-sm text-muted-foreground">월 총 수입</p>
            <p className="text-xl font-bold text-primary">
              {formatKRW(summary.total_income)}원
            </p>
            {summary.incomes.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
                {summary.incomes.map((item, i) => (
                  <span key={i}>
                    {INCOME_TYPE_LABELS[item.income_type] ?? item.income_type} {formatKRW(item.amount)}원
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {(!recurringIncomes || recurringIncomes.length === 0) ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            등록된 정기 수입이 없습니다.
          </p>
        ) : (
          <ul className="space-y-3">
            {recurringIncomes.map((ri) => (
              <li
                key={ri.id}
                className={`flex items-center justify-between rounded-md border border-border px-4 py-3 ${!ri.is_active ? 'opacity-50' : ''}`}
              >
                <div>
                  <p className="text-sm font-medium">{ri.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {INCOME_TYPE_LABELS[ri.income_type] ?? ri.income_type} · 매월 {ri.day}일
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">
                    {formatKRW(ri.amount)}원
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleRecurring.mutate(ri.id)}
                    disabled={toggleRecurring.isPending}
                    title={ri.is_active ? '비활성화' : '활성화'}
                  >
                    {ri.is_active ? (
                      <ToggleRight className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <ToggleLeft className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteRecurring.mutate(ri.id)}
                    disabled={deleteRecurring.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <AddRecurringIncomeModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          onSubmit={(data) => createRecurring.mutate(data)}
          isSubmitting={createRecurring.isPending}
        />
      </CardContent>
    </Card>
  );
}
