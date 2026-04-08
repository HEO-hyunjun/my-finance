import { memo, useMemo } from 'react';
import type { DashboardBudgetSummary } from '@/shared/types/dashboard';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Wallet, Calendar } from 'lucide-react';
import { cn } from '@/shared/lib/utils';

interface Props {
  budget: DashboardBudgetSummary;
}

function DailyBudgetWidgetInner({ budget }: Props) {
  const { daily_available, today_spent, remaining_days } = budget;

  const { todayRemaining, spentRatio } = useMemo(() => {
    const todayRemaining = daily_available - today_spent;
    const spentRatio = daily_available > 0 ? Math.min((today_spent / daily_available) * 100, 100) : 0;
    return { todayRemaining, spentRatio };
  }, [daily_available, today_spent]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Wallet className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-sm">오늘의 가용 예산</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-4 text-center">
          <p className={cn(
            'text-3xl font-bold',
            todayRemaining >= 0 ? 'text-primary' : 'text-destructive'
          )}>
            {todayRemaining >= 0 ? '+' : ''}{Math.round(todayRemaining).toLocaleString()}원
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            일일 예산 {Math.round(daily_available).toLocaleString()}원 중 {Math.round(today_spent).toLocaleString()}원 사용
          </p>
        </div>

        {/* 사용 진행 바 */}
        <div className="mb-4">
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                'h-full rounded-full transition-[width]',
                spentRatio >= 100 ? 'bg-red-500' : spentRatio >= 80 ? 'bg-yellow-500' : 'bg-primary'
              )}
              style={{ width: `${spentRatio}%` }}
            />
          </div>
          <div className="mt-1 flex justify-between text-xs text-muted-foreground">
            <span>0원</span>
            <span>{Math.round(daily_available).toLocaleString()}원</span>
          </div>
        </div>

        <div className="flex items-center justify-center gap-1 rounded-lg bg-muted px-4 py-2 text-xs text-muted-foreground">
          <Calendar className="h-3 w-3" />
          이번 달 남은 {remaining_days}일 기준
        </div>
      </CardContent>
    </Card>
  );
}

export const DailyBudgetWidget = memo(DailyBudgetWidgetInner);
