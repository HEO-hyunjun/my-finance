import { memo } from 'react';
import type { DashboardBudgetSummary } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { ArrowRight } from 'lucide-react';

interface Props {
  budget: DashboardBudgetSummary;
}

function getBarColor(rate: number, color?: string): string {
  if (rate > 100) return '#EF4444';
  if (rate > 80) return '#F59E0B';
  return color || '#22C55E';
}

function BudgetStatusWidgetInner({ budget }: Props) {
  const { total_budget, total_spent, total_usage_rate, top_categories, total_fixed_expenses, total_installments } = budget;

  if (total_budget === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">이번 달 예산</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          <p className="text-sm text-muted-foreground">예산 카테고리를 설정해보세요!</p>
          <a href="/budget" className="mt-2 inline-flex items-center gap-1 text-sm text-primary hover:underline">
            예산 설정하기 <ArrowRight className="h-3 w-3" />
          </a>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">이번 달 예산</CardTitle>
      </CardHeader>
      <CardContent>
        <div>
          <div className="flex items-baseline justify-between">
            <span className="text-lg font-bold">{formatKRW(total_spent)}</span>
            <span className="text-xs text-muted-foreground">/ {formatKRW(total_budget)}</span>
          </div>
          <div className="mt-1.5 h-2.5 w-full rounded-full bg-muted">
            <div
              className="h-2.5 rounded-full"
              style={{ width: `${Math.min(total_usage_rate, 100)}%`, backgroundColor: getBarColor(total_usage_rate) }}
            />
          </div>
          <p className="mt-1 text-right text-xs text-muted-foreground">{total_usage_rate.toFixed(1)}%</p>
        </div>

        <div className="mt-4 space-y-2.5">
          {top_categories.map((cat) => (
            <div key={cat.name}>
              <div className="flex items-center justify-between text-xs">
                <span>
                  {cat.icon && <span className="mr-1">{cat.icon}</span>}
                  {cat.name}
                </span>
                <span className="text-muted-foreground">
                  {formatKRW(cat.spent)} / {formatKRW(cat.budget)}
                </span>
              </div>
              <div className="mt-0.5 h-1.5 w-full rounded-full bg-muted">
                <div
                  className="h-1.5 rounded-full"
                  style={{
                    width: `${Math.min(cat.usage_rate, 100)}%`,
                    backgroundColor: getBarColor(cat.usage_rate, cat.color ?? undefined),
                  }}
                />
              </div>
            </div>
          ))}
        </div>

        {(total_fixed_expenses > 0 || total_installments > 0) && (
          <div className="mt-4 flex gap-4 border-t border-border pt-3 text-xs text-muted-foreground">
            <span>고정비 {formatKRW(total_fixed_expenses)}</span>
            <span>할부 {formatKRW(total_installments)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const BudgetStatusWidget = memo(BudgetStatusWidgetInner);
