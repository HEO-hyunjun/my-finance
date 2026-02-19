import { memo, useMemo, useCallback } from 'react';
import { Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import type { Expense } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';

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
      <div className="rounded-lg border border-dashed border-border p-8 text-center">
        <p className="text-muted-foreground">지출 내역이 없습니다.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="overflow-x-auto" style={{ contentVisibility: 'auto' }}>
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">일시</th>
              <th className="px-4 py-3">카테고리</th>
              <th className="px-4 py-3">메모</th>
              <th className="px-4 py-3 text-right">금액</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {expenses.map((exp) => (
              <tr key={exp.id} className="hover:bg-muted/50">
                <td className="px-4 py-3 whitespace-nowrap">
                  {exp.spent_at}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 w-2 rounded-full shrink-0"
                      style={{ backgroundColor: exp.category_color || '#B2BEC3' }}
                    />
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                      {exp.category_name}
                    </Badge>
                  </div>
                </td>
                <td className="px-4 py-3 max-w-[200px] truncate text-muted-foreground">
                  {exp.memo || '-'}
                </td>
                <td className="px-4 py-3 text-right font-medium text-red-600">
                  -{formatKRW(exp.amount)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEdit(exp)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(exp.id)}
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
            onClick={handlePrevPage}
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
            onClick={handleNextPage}
          >
            다음
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}

export const ExpenseList = memo(ExpenseListInner);
