import { Target } from 'lucide-react';
import { useGoal } from '@/features/portfolio/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW } from '@/features/dashboard/lib/widget-format';
import { WidgetError } from './WidgetError';

export function GoalAssetWidget({ onOpenSettings }: { onOpenSettings?: () => void }) {
  const { data, isLoading, isError, error } = useGoal();

  const isNotFound =
    isError &&
    error &&
    typeof error === 'object' &&
    'response' in error &&
    (error as { response?: { status?: number } }).response?.status === 404;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Target className="h-4 w-4" />
          목표 자산
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-4 w-32" />
          </div>
        ) : isNotFound || !data ? (
          <div className="flex flex-col items-center py-6 text-center">
            <Target className="mb-2 h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">목표가 설정되지 않았습니다</p>
            <button
              type="button"
              onClick={onOpenSettings}
              className="mt-2 text-xs text-primary underline underline-offset-2"
            >
              목표 설정하기
            </button>
          </div>
        ) : isError ? (
          <WidgetError />
        ) : (
          <div className="space-y-3">
            <div>
              <p className="text-sm text-muted-foreground">목표 금액</p>
              <p className="text-xl font-bold">{formatKRW(data.target_amount)}</p>
            </div>
            {/* 달성률 바 */}
            <div>
              <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                <span>달성률</span>
                <span>{data.achievement_rate.toFixed(1)}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${Math.min(data.achievement_rate, 100)}%` }}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-muted-foreground">현재 자산</p>
                <p className="font-medium">{formatKRW(data.current_amount)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">남은 금액</p>
                <p className="font-medium">{formatKRW(data.remaining_amount)}</p>
              </div>
              {data.monthly_required != null && (
                <div>
                  <p className="text-muted-foreground">월 필요 저축</p>
                  <p className="font-medium">{formatKRW(data.monthly_required)}</p>
                </div>
              )}
              {data.estimated_date && (
                <div>
                  <p className="text-muted-foreground">달성 예상</p>
                  <p className="font-medium">
                    {new Date(data.estimated_date).toLocaleDateString('ko-KR', {
                      year: 'numeric',
                      month: 'short',
                    })}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
