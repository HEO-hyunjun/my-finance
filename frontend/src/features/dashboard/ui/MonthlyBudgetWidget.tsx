import { useBudgetAnalysis } from '@/features/budget/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW } from '@/features/dashboard/lib/widget-format';
import { WidgetError } from './WidgetError';

export function MonthlyBudgetWidget() {
  const { data, isLoading, isError } = useBudgetAnalysis();

  const categories = data?.category_rates ?? [];
  const fixed = data?.fixed_deductions;

  const STATUS_COLORS: Record<string, string> = {
    normal: 'bg-primary',
    warning: 'bg-yellow-500',
    exceeded: 'bg-destructive',
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">월 예산 현황</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : isError ? (
          <WidgetError />
        ) : (
          <div className="space-y-3">
            {categories.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                카테고리 예산이 없습니다
              </p>
            ) : (
              categories.map((cat) => (
                <div key={cat.category_id}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1">
                      {cat.category_icon && <span>{cat.category_icon}</span>}
                      <span className="font-medium">{cat.category_name}</span>
                    </span>
                    <span className="text-muted-foreground">
                      {formatKRW(cat.spent)} / {formatKRW(cat.monthly_budget)}
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className={`h-full rounded-full transition-all ${
                        STATUS_COLORS[cat.status] ?? 'bg-primary'
                      }`}
                      style={{ width: `${Math.min(cat.usage_rate, 100)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
            {/* 고정비 / 할부 요약 */}
            {fixed && fixed.items.length > 0 && (
              <div className="mt-3 border-t pt-3">
                <p className="mb-2 text-xs font-medium text-muted-foreground">고정비 / 할부</p>
                {fixed.items.slice(0, 4).map((item, i) => (
                  <div key={i} className="flex items-center justify-between py-0.5 text-xs">
                    <span className="flex items-center gap-1">
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          item.is_paid ? 'bg-green-500' : 'bg-muted-foreground'
                        }`}
                      />
                      {item.name}
                    </span>
                    <span className="font-medium">{formatKRW(item.amount)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
