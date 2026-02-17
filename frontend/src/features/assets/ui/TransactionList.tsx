import { memo, useMemo, useCallback } from 'react';
import { Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import type { Transaction } from '@/shared/types';
import { TRANSACTION_TYPE_LABELS } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';

interface Props {
  transactions: Transaction[];
  total: number;
  page: number;
  perPage: number;
  onPageChange?: (page: number) => void;
  onDelete?: (id: string) => void;
}

function TransactionListInner({
  transactions,
  total,
  page,
  perPage,
  onPageChange,
  onDelete,
}: Props) {
  const totalPages = useMemo(() => Math.ceil(total / perPage), [total, perPage]);

  const handlePrevPage = useCallback(() => {
    onPageChange?.(page - 1);
  }, [onPageChange, page]);

  const handleNextPage = useCallback(() => {
    onPageChange?.(page + 1);
  }, [onPageChange, page]);

  if (transactions.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center">
        <p className="text-muted-foreground">거래 내역이 없습니다.</p>
      </div>
    );
  }

  const getTypeBadgeVariant = (type: string) => {
    if (type === 'buy') return 'default';
    if (type === 'sell') return 'destructive';
    return 'secondary';
  };

  return (
    <div>
      <div className="overflow-x-auto" style={{ contentVisibility: 'auto' }}>
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">일시</th>
              <th className="px-4 py-3">유형</th>
              <th className="px-4 py-3">자산</th>
              <th className="px-4 py-3 text-right">수량</th>
              <th className="px-4 py-3 text-right">단가</th>
              <th className="px-4 py-3 text-right">금액</th>
              <th className="px-4 py-3">메모</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {transactions.map((tx) => (
              <tr key={tx.id} className="hover:bg-muted/50">
                <td className="px-4 py-3 whitespace-nowrap">
                  {new Date(tx.transacted_at).toLocaleDateString('ko-KR')}
                </td>
                <td className="px-4 py-3">
                  <Badge variant={getTypeBadgeVariant(tx.type)}>
                    {TRANSACTION_TYPE_LABELS[tx.type] || tx.type}
                  </Badge>
                </td>
                <td className="px-4 py-3">{tx.asset_name}</td>
                <td className="px-4 py-3 text-right">{tx.quantity.toLocaleString()}</td>
                <td className="px-4 py-3 text-right">
                  {tx.currency === 'USD' ? `$${tx.unit_price.toLocaleString()}` : `${formatKRW(tx.unit_price)}`}
                </td>
                <td className="px-4 py-3 text-right font-medium">
                  {formatKRW(tx.quantity * tx.unit_price * (tx.exchange_rate || 1))}
                </td>
                <td className="px-4 py-3 max-w-[120px] truncate text-muted-foreground">{tx.memo}</td>
                <td className="px-4 py-3">
                  {onDelete && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(tx.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
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

export const TransactionList = memo(TransactionListInner);
