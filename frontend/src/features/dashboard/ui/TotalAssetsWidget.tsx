import { Wallet, TrendingUp, TrendingDown } from 'lucide-react';
import { useDashboardSummary } from '@/features/dashboard/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW } from '@/features/dashboard/lib/widget-format';
import { WidgetError } from './WidgetError';

export function TotalAssetsWidget() {
  const { data, isLoading, isError } = useDashboardSummary();

  return (
    <Card className="col-span-2">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Wallet className="h-4 w-4" />
          총 자산
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        ) : isError ? (
          <WidgetError />
        ) : (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">순자산</p>
            <p className="text-3xl font-bold tracking-tight">
              {formatKRW(data?.net_worth_krw ?? data?.total_assets_krw ?? 0)}
            </p>
            {(data?.total_debt_krw ?? 0) > 0 && (
              <div className="flex gap-4 text-xs text-muted-foreground">
                <span>총자산 {formatKRW(data?.gross_assets_krw ?? 0)}</span>
                <span className="text-destructive">부채 {formatKRW(data?.total_debt_krw ?? 0)}</span>
              </div>
            )}
            <p className="text-sm text-muted-foreground">
              계좌 {data?.accounts_count ?? 0}개 연동 중
            </p>
            {data?.daily_change != null && (
              <div className="mt-1 flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">전일대비</span>
                {(data.daily_change ?? 0) >= 0 ? (
                  <TrendingUp className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
                ) : (
                  <TrendingDown className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />
                )}
                <span className={(data.daily_change ?? 0) >= 0 ? 'font-medium text-green-600 dark:text-green-400' : 'font-medium text-red-600 dark:text-red-400'}>
                  {(data.daily_change ?? 0) >= 0 ? '+' : ''}{formatKRW(data.daily_change)}
                  {data.daily_change_rate != null && ` (${((data.daily_change_rate ?? 0) * 100).toFixed(2)}%)`}
                </span>
              </div>
            )}
            <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">이번 달 수입</p>
                <p className="font-semibold text-green-600">
                  {formatKRW(data?.monthly_income ?? 0)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">이번 달 지출</p>
                <p className="font-semibold text-destructive">
                  {formatKRW(data?.monthly_expense ?? 0)}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
