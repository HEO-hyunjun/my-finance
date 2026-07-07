import { Lightbulb } from 'lucide-react';
import { useDashboardInsights } from '@/features/dashboard/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { WidgetError } from './WidgetError';

const INSIGHT_SEVERITY_STYLES: Record<
  string,
  { border: string; bg: string; badge: string }
> = {
  info: {
    border: 'border-blue-200',
    bg: 'bg-blue-50/50 dark:bg-blue-950/20',
    badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  },
  warning: {
    border: 'border-yellow-200',
    bg: 'bg-yellow-50/50 dark:bg-yellow-950/20',
    badge: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  },
  success: {
    border: 'border-green-200',
    bg: 'bg-green-50/50 dark:bg-green-950/20',
    badge: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  },
};

const INSIGHT_TYPE_LABELS: Record<string, string> = {
  spending: '지출',
  budget: '예산',
  investment: '투자',
  saving: '저축',
  alert: '알림',
};

export function AIInsightsWidget() {
  const { data, isLoading, isError } = useDashboardInsights();
  const insights = data?.insights ?? [];

  return (
    <Card className="col-span-full">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Lightbulb className="h-4 w-4" />
          AI 인사이트
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-24 w-full rounded-lg" />
            ))}
          </div>
        ) : isError ? (
          <WidgetError />
        ) : insights.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            인사이트를 생성하는 중입니다
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {insights.map((insight, i) => {
              const styles =
                INSIGHT_SEVERITY_STYLES[insight.severity] ?? INSIGHT_SEVERITY_STYLES.info;
              return (
                <div
                  key={i}
                  className={`rounded-lg border p-3 ${styles.border} ${styles.bg}`}
                >
                  <div className="mb-1 flex items-center gap-2">
                    <span
                      className={`rounded-full px-1.5 py-0.5 text-xs font-medium ${styles.badge}`}
                    >
                      {INSIGHT_TYPE_LABELS[insight.type] ?? insight.type}
                    </span>
                  </div>
                  <p className="text-sm font-semibold">{insight.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{insight.description}</p>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
