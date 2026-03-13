import { useState } from 'react';
import { Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { INCOME_TYPE_LABELS } from '@/shared/types';
import type { Income, IncomeType } from '@/shared/types';
import { useIncomes, useDeleteIncome } from '../api';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW } from '@/shared/lib/format';

interface Props {
  incomeType?: string;
  startDate?: string;
  endDate?: string;
  onEdit?: (income: Income) => void;
}

export function IncomeList({ incomeType, startDate, endDate, onEdit }: Props) {
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
      <div className="space-y-3">
        <Skeleton className="h-10 w-full" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  const incomes = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / perPage);

  if (incomes.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center">
        <p className="text-muted-foreground">수입 내역이 없습니다.</p>
      </div>
    );
  }

  const getTypeBadgeVariant = (type: string) => {
    if (type === 'salary') return 'default';
    if (type === 'investment') return 'secondary';
    return 'outline';
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-muted-foreground">
          총 <span className="font-semibold text-foreground">{total.toLocaleString()}</span>건
        </p>
      </div>

      <div className="overflow-x-auto" style={{ contentVisibility: 'auto' }}>
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-2 py-2 sm:px-4 sm:py-3">일시</th>
              <th className="px-2 py-2 sm:px-4 sm:py-3">유형</th>
              <th className="hidden sm:table-cell px-4 py-3">설명</th>
              <th className="px-2 py-2 text-right sm:px-4 sm:py-3">금액</th>
              <th className="hidden sm:table-cell px-4 py-3">구분</th>
              <th className="px-2 py-2 sm:px-4 sm:py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {incomes.map((income) => (
              <tr key={income.id} className="hover:bg-muted/50">
                <td className="px-2 py-2 whitespace-nowrap sm:px-4 sm:py-3">
                  {income.received_at}
                </td>
                <td className="px-2 py-2 sm:px-4 sm:py-3">
                  <Badge variant={getTypeBadgeVariant(income.type)}>
                    {INCOME_TYPE_LABELS[income.type as IncomeType] || income.type}
                  </Badge>
                </td>
                <td className="hidden sm:table-cell px-4 py-3 max-w-[200px] truncate">
                  {income.description}
                </td>
                <td className="px-2 py-2 text-right font-medium text-emerald-600 dark:text-emerald-400 whitespace-nowrap sm:px-4 sm:py-3">
                  +{formatKRW(income.amount)}
                </td>
                <td className="hidden sm:table-cell px-4 py-3">
                  {income.recurring_income_id && (
                    <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
                      정기
                    </Badge>
                  )}
                </td>
                <td className="px-2 py-2 sm:px-4 sm:py-3">
                  <div className="flex gap-1">
                    {onEdit && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onEdit(income)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(income.id)}
                      disabled={deleteIncome.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
            이전
          </Button>
          <span className="text-sm text-muted-foreground">
            {page} / {totalPages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            다음
            <ChevronRight className="h-4 w-4" />
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
