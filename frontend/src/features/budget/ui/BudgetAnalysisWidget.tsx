import { memo } from 'react';
import { useBudgetAnalysis } from '../api/analysis';
import type { CategorySpendingRate } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Skeleton } from '@/shared/ui/skeleton';
import { AlertTriangle } from 'lucide-react';

const StatusBadge = memo(({ status }: { status: string }) => {
  const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
    normal: 'outline',
    warning: 'secondary',
    exceeded: 'destructive',
  };
  const labels: Record<string, string> = { normal: '정상', warning: '주의', exceeded: '초과' };
  return (
    <Badge variant={variants[status] || 'outline'} className="text-xs">
      {labels[status] || status}
    </Badge>
  );
});

const CategoryBar = memo(({ rate }: { rate: CategorySpendingRate }) => {
  const pct = Math.min(rate.usage_rate, 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span>{rate.category_icon} {rate.category_name}</span>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">{formatKRW(rate.spent)} / {formatKRW(rate.monthly_budget)}</span>
          <StatusBadge status={rate.status} />
        </div>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-[width]"
          style={{ width: `${pct}%`, backgroundColor: rate.category_color }}
        />
      </div>
    </div>
  );
});

function BudgetAnalysisWidgetInner() {
  const { data, isLoading, isError } = useBudgetAnalysis();

  if (isLoading) return <Skeleton className="h-96 rounded-xl" />;
  if (isError || !data) return null;

  const { daily_budget, weekly_analysis, category_rates, alerts } = data;

  return (
    <div className="space-y-4">
      {/* Daily Budget Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm text-muted-foreground">오늘 사용 가능 금액</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-bold text-primary">{formatKRW(daily_budget.daily_available)}</p>
          <div className="mt-2 flex gap-4 text-sm text-muted-foreground">
            <span>오늘 지출: {formatKRW(daily_budget.today_spent)}</span>
            <span>남은 예산: {formatKRW(daily_budget.remaining_budget)}</span>
            <span>남은 일수: {daily_budget.remaining_days}일</span>
          </div>
        </CardContent>
      </Card>

      {/* Weekly Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm text-muted-foreground">이번 주 사용 현황</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-2">
            <span className="text-xl font-bold">{formatKRW(weekly_analysis.week_spent)}</span>
            <span className="text-sm text-muted-foreground">/ {formatKRW(weekly_analysis.weekly_average_budget)}</span>
          </div>
          <div className="mt-2 h-3 rounded-full bg-muted">
            <div
              className={`h-full rounded-full transition-[width] ${
                weekly_analysis.is_over_budget ? 'bg-red-500' : 'bg-primary'
              }`}
              style={{ width: `${Math.min(weekly_analysis.usage_rate, 100)}%` }}
            />
          </div>
          <p className={`mt-1 text-xs ${weekly_analysis.is_over_budget ? 'text-red-500' : 'text-muted-foreground'}`}>
            {weekly_analysis.usage_rate.toFixed(1)}% 사용
          </p>
        </CardContent>
      </Card>

      {/* Alerts */}
      {alerts.length > 0 && (
        <Card className="border-amber-500/20 bg-amber-500/10">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <CardTitle className="text-sm text-amber-800 dark:text-amber-400">예산 알림</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {alerts.map((alert, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-300">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  {alert}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Category Rates */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm text-muted-foreground">카테고리별 소진율</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {category_rates.map((rate) => (
            <CategoryBar key={rate.category_id} rate={rate} />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export const BudgetAnalysisWidget = memo(BudgetAnalysisWidgetInner);
