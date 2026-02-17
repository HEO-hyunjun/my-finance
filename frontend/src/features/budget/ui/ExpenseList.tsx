import { memo, useMemo, useCallback } from 'react';
import type { Expense } from '@/shared/types';
import { PAYMENT_METHOD_LABELS } from '@/shared/types';
import type { PaymentMethod } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';

interface Props {
  expenses: Expense[];
  total: number;
  page: number;
  perPage: number;
  onPageChange: (page: number) => void;
  onEdit: (expense: Expense) => void;
  onDelete: (id: string) => void;
}

function ExpenseListInner({
  expenses,
  total,
  page,
  perPage,
  onPageChange,
  onEdit,
  onDelete,
}: Props) {
  const totalPages = useMemo(() => Math.ceil(total / perPage), [total, perPage]);

  const handlePrevPage = useCallback(() => {
    onPageChange(page - 1);
  }, [onPageChange, page]);

  const handleNextPage = useCallback(() => {
    onPageChange(page + 1);
  }, [onPageChange, page]);

  if (expenses.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground">
        지출 내역이 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-2" style={{ contentVisibility: 'auto' }}>
      {expenses.map((exp) => (
        <div
          key={exp.id}
          className="flex items-center justify-between rounded-lg border border-border bg-card p-3"
        >
          <div className="flex items-center gap-3">
            <div
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: exp.category_color || '#B2BEC3' }}
            />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{exp.memo || exp.category_name}</span>
                <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                  {exp.category_name}
                </Badge>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{exp.spent_at}</span>
                {exp.payment_method && (
                  <span>{PAYMENT_METHOD_LABELS[exp.payment_method as PaymentMethod] || exp.payment_method}</span>
                )}
                {exp.tags && <span>{exp.tags}</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-medium text-red-600">-{formatKRW(exp.amount)}</span>
            <div className="flex gap-1">
              <Button
                onClick={() => onEdit(exp)}
                variant="ghost"
                size="sm"
                className="h-auto px-2 py-1 text-xs"
              >
                수정
              </Button>
              <Button
                onClick={() => onDelete(exp.id)}
                variant="ghost"
                size="sm"
                className="h-auto px-2 py-1 text-xs text-destructive hover:text-destructive"
              >
                삭제
              </Button>
            </div>
          </div>
        </div>
      ))}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 pt-2">
          <Button
            onClick={handlePrevPage}
            disabled={page <= 1}
            variant="outline"
            size="sm"
          >
            이전
          </Button>
          <span className="px-3 py-1 text-sm text-muted-foreground">
            {page} / {totalPages}
          </span>
          <Button
            onClick={handleNextPage}
            disabled={page >= totalPages}
            variant="outline"
            size="sm"
          >
            다음
          </Button>
        </div>
      )}
    </div>
  );
}

export const ExpenseList = memo(ExpenseListInner);
