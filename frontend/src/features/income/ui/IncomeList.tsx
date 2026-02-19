import { useState } from 'react';
import { INCOME_TYPE_LABELS } from '@/shared/types';
import type { IncomeType } from '@/shared/types';
import { useIncomes, useDeleteIncome } from '../api';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import { Card, CardContent } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW } from '@/shared/lib/format';

interface Props {
  incomeType?: string;
  startDate?: string;
  endDate?: string;
}

export function IncomeList({ incomeType, startDate, endDate }: Props) {
  const [page, setPage] = useState(1);
  const [confirmState, setConfirmState] = useState<{ action: () => void } | null>(null);
  const perPage = 20;

  const { data, isLoading } = useIncomes({
    income_type: incomeType,
    start_date: startDate,
    end_date: endDate,
    page,
    per_page: perPage,
  });

  const deleteIncome = useDeleteIncome();

  const handleDelete = (id: string) => {
    setConfirmState({ action: () => deleteIncome.mutate(id) });
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="flex items-center justify-between py-3">
              <div className="flex items-center gap-3">
                <Skeleton className="h-6 w-16 rounded-full" />
                <div className="space-y-1">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </div>
              <Skeleton className="h-5 w-20" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const incomes = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / perPage);

  if (incomes.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          수입 내역이 없습니다.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {incomes.map((income) => (
        <Card key={income.id}>
          <CardContent className="flex items-center justify-between py-3">
            <div className="flex items-center gap-3">
              <Badge variant="secondary" className="bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400">
                {INCOME_TYPE_LABELS[income.type as IncomeType] || income.type}
              </Badge>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{income.description}</span>
                  {income.is_recurring && (
                    <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
                      정기
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{income.received_at}</span>
                  {income.is_recurring && income.recurring_day && (
                    <span>매월 {income.recurring_day}일</span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-medium text-emerald-600 dark:text-emerald-400">
                +{formatKRW(income.amount)}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDelete(income.id)}
                disabled={deleteIncome.isPending}
                className="text-xs text-destructive hover:text-destructive"
              >
                삭제
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p - 1)}
            disabled={page <= 1}
          >
            이전
          </Button>
          <span className="px-3 py-1 text-sm text-muted-foreground">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
          >
            다음
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={confirmState !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmState(null);
        }}
        title="이 수입을 삭제하시겠습니까?"
        description="이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={() => confirmState?.action()}
        variant="destructive"
      />
    </div>
  );
}
