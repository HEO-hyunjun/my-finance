import { DollarSign } from 'lucide-react';
import { useBudgetAnalysis } from '@/features/budget/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW } from '@/features/dashboard/lib/widget-format';
import { WidgetError } from './WidgetError';

export function DailyBudgetWidget() {
  const { data, isLoading, isError } = useBudgetAnalysis();

  const daily = data?.daily_budget;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <DollarSign className="h-4 w-4" />
          오늘 사용 가능 예산
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-36" />
            <Skeleton className="h-4 w-24" />
          </div>
        ) : isError || !daily ? (
          <WidgetError />
        ) : (
          <div className="space-y-3">
            <div>
              <p className="text-sm text-muted-foreground">하루 가용 예산</p>
              <p className="text-2xl font-bold text-primary">
                {formatKRW(daily.daily_available)}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-muted-foreground">오늘 사용</p>
                <p className="font-semibold text-destructive">
                  {formatKRW(daily.today_spent)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">남은 일수</p>
                <p className="font-semibold">{daily.remaining_days}일</p>
              </div>
              <div>
                <p className="text-muted-foreground">남은 예산</p>
                <p
                  className={`font-semibold ${
                    daily.remaining_budget < 0 ? 'text-destructive' : 'text-green-600'
                  }`}
                >
                  {formatKRW(daily.remaining_budget)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">기간</p>
                <p className="font-medium">
                  {new Date(daily.period_start).toLocaleDateString('ko-KR', {
                    month: 'short',
                    day: 'numeric',
                  })}{' '}
                  ~{' '}
                  {new Date(daily.period_end).toLocaleDateString('ko-KR', {
                    month: 'short',
                    day: 'numeric',
                  })}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
