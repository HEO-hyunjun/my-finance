import { memo, useMemo } from 'react';
import type { FixedExpense } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { cn } from '@/shared/lib/utils';

interface Props {
  fixedExpenses: FixedExpense[];
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
}

function FixedExpenseListInner({ fixedExpenses, onToggle, onDelete }: Props) {
  const totalActive = useMemo(
    () => fixedExpenses.filter((fe) => fe.is_active).reduce((sum, fe) => sum + fe.amount, 0),
    [fixedExpenses]
  );

  if (fixedExpenses.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground">
        등록된 고정비가 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-2" style={{ contentVisibility: 'auto' }}>
      {fixedExpenses.map((fe) => (
        <div
          key={fe.id}
          className={cn(
            'flex items-center justify-between rounded-lg border bg-card p-3',
            fe.is_active ? 'border-border' : 'border-border opacity-50'
          )}
        >
          <div>
            <div className="flex items-center gap-2">
              <div
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: fe.category_color || '#B2BEC3' }}
              />
              <span className="font-medium">{fe.name}</span>
              <span className="text-sm font-semibold">{formatKRW(fe.amount)}</span>
            </div>
            <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">{fe.category_name}</Badge>
              {fe.source_asset_name && (
                <span>{fe.source_asset_name}</span>
              )}
              <span>매월 {fe.payment_day}일</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={() => onToggle(fe.id)}
              variant={fe.is_active ? 'default' : 'secondary'}
              size="sm"
              className="h-auto rounded-full px-3 py-1 text-xs"
            >
              {fe.is_active ? 'ON' : 'OFF'}
            </Button>
            <Button
              onClick={() => onDelete(fe.id)}
              variant="ghost"
              size="sm"
              className="h-auto px-2 py-1 text-xs text-destructive hover:text-destructive"
            >
              삭제
            </Button>
          </div>
        </div>
      ))}

      <div className="rounded-lg bg-muted p-3 text-right text-sm">
        <span className="text-muted-foreground">월 합계: </span>
        <span className="font-semibold">{formatKRW(totalActive)}</span>
      </div>
    </div>
  );
}

export const FixedExpenseList = memo(FixedExpenseListInner);
