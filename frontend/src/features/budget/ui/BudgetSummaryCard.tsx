import { memo } from 'react';
import type { BudgetSummaryResponse } from '@/shared/types';
import { Card, CardContent } from '@/shared/ui/card';
import { formatKRW } from '@/shared/lib/format';

interface Props {
  summary: BudgetSummaryResponse;
}

function BudgetSummaryCardInner({ summary }: Props) {
  const usageRate = summary.total_usage_rate;
  const isOver = usageRate > 100;
  const hasFixedOrInstallment = summary.total_fixed_expenses > 0 || summary.total_installments > 0;

  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-3 text-sm font-medium text-muted-foreground">
          {summary.period_start} ~ {summary.period_end}
        </h3>
        <div className="mb-4 grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-muted-foreground">총 예산</p>
            <p className="text-lg font-bold">{formatKRW(summary.total_budget)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">지출</p>
            <p className={`text-lg font-bold ${isOver ? 'text-destructive' : ''}`}>
              {formatKRW(summary.total_spent)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">잔여</p>
            <p className={`text-lg font-bold ${summary.total_remaining < 0 ? 'text-destructive' : 'text-green-600'}`}>
              {formatKRW(summary.total_remaining)}
            </p>
          </div>
        </div>
        {/* 프로그레스 바 */}
        <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full rounded-full transition-[width] ${isOver ? 'bg-destructive' : 'bg-primary'}`}
            style={{ width: `${Math.min(usageRate, 100)}%` }}
          />
        </div>
        <p className={`mt-1 text-right text-xs ${isOver ? 'text-destructive' : 'text-muted-foreground'}`}>
          {usageRate.toFixed(1)}%
        </p>

        {/* Phase 2: 고정비/할부금 차감 표시 */}
        {hasFixedOrInstallment && (
          <div className="mt-4 border-t border-border pt-4">
            <div className="mb-3 space-y-1 text-sm">
              {summary.total_fixed_expenses > 0 && (
                <div className="flex justify-between text-muted-foreground">
                  <span>고정비</span>
                  <span className="font-medium">-{formatKRW(summary.total_fixed_expenses)}</span>
                </div>
              )}
              {summary.total_installments > 0 && (
                <div className="flex justify-between text-muted-foreground">
                  <span>할부금</span>
                  <span className="font-medium">-{formatKRW(summary.total_installments)}</span>
                </div>
              )}
            </div>
            <div className="grid grid-cols-3 gap-4 rounded-lg bg-muted p-3">
              <div>
                <p className="text-xs text-muted-foreground">가변예산</p>
                <p className="text-sm font-bold">{formatKRW(summary.variable_budget)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">가변지출</p>
                <p className="text-sm font-bold">{formatKRW(summary.variable_spent)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">가변잔여</p>
                <p className={`text-sm font-bold ${summary.variable_remaining < 0 ? 'text-destructive' : 'text-green-600'}`}>
                  {formatKRW(summary.variable_remaining)}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const BudgetSummaryCard = memo(BudgetSummaryCardInner);
