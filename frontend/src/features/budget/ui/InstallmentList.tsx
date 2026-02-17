import { memo, useMemo } from 'react';
import type { Installment } from '@/shared/types';
import { PAYMENT_METHOD_LABELS } from '@/shared/types';
import type { PaymentMethod } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { cn } from '@/shared/lib/utils';

interface Props {
  installments: Installment[];
  onDelete: (id: string) => void;
}

function InstallmentListInner({ installments, onDelete }: Props) {
  const totalActive = useMemo(
    () => installments.filter((inst) => inst.is_active).reduce((sum, inst) => sum + inst.monthly_amount, 0),
    [installments]
  );

  if (installments.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground">
        등록된 할부금이 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-3" style={{ contentVisibility: 'auto' }}>
      {installments.map((inst) => (
        <div
          key={inst.id}
          className={cn(
            'rounded-lg border bg-card p-4',
            inst.is_active ? 'border-border' : 'border-border opacity-50'
          )}
        >
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: inst.category_color || '#B2BEC3' }}
              />
              <span className="font-medium">{inst.name}</span>
              <Badge variant="secondary" className="text-xs">{formatKRW(inst.monthly_amount)}/월</Badge>
            </div>
            <Button
              onClick={() => onDelete(inst.id)}
              variant="ghost"
              size="sm"
              className="h-auto px-2 py-1 text-xs text-destructive hover:text-destructive"
            >
              삭제
            </Button>
          </div>

          <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="text-[10px] px-1.5 py-0">{inst.category_name}</Badge>
            {inst.payment_method && (
              <span>
                {PAYMENT_METHOD_LABELS[inst.payment_method as PaymentMethod] || inst.payment_method}
              </span>
            )}
            <span>매월 {inst.payment_day}일</span>
          </div>

          {/* 진행률 바 */}
          <div className="mb-1 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-purple-500 transition-[width]"
              style={{ width: `${Math.min(inst.progress_rate, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>
              {inst.paid_installments}/{inst.total_installments}개월 ({inst.progress_rate.toFixed(1)}%)
            </span>
            <span>남은 {formatKRW(inst.remaining_amount)}</span>
          </div>

          <div className="mt-1 text-xs text-muted-foreground">
            총 {formatKRW(inst.total_amount)} | {inst.start_date} ~ {inst.end_date}
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

export const InstallmentList = memo(InstallmentListInner);
