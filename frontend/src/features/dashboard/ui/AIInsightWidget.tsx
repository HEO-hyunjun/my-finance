import { memo } from 'react';
import { useDashboardInsights } from '@/features/dashboard/api';
import type { AIInsight } from '@/shared/types/dashboard';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { Sparkles, TrendingDown, BarChart3, Target, AlertTriangle, Lightbulb } from 'lucide-react';
import { cn } from '@/shared/lib/utils';

const SEVERITY_STYLES: Record<string, { bg: string; border: string; text: string }> = {
  info: { bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-700 dark:text-blue-400' },
  warning: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-700 dark:text-amber-400' },
  success: { bg: 'bg-green-500/10', border: 'border-green-500/20', text: 'text-green-700 dark:text-green-400' },
};

const TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  spending: TrendingDown,
  budget: BarChart3,
  investment: Target,
  saving: Target,
  alert: AlertTriangle,
};

const InsightCard = memo(function InsightCard({ insight }: { insight: AIInsight }) {
  const style = SEVERITY_STYLES[insight.severity] ?? SEVERITY_STYLES.info;
  const Icon = TYPE_ICONS[insight.type] ?? Lightbulb;

  return (
    <div className={cn('flex gap-3 rounded-lg border p-3', style.bg, style.border)}>
      <Icon className={cn('h-5 w-5 flex-shrink-0', style.text)} />
      <div className="min-w-0">
        <p className={cn('text-sm font-semibold', style.text)}>{insight.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{insight.description}</p>
      </div>
    </div>
  );
});

function AIInsightWidgetInner() {
  const { data, isLoading, isError } = useDashboardInsights();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm">AI Insights</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (isError || !data?.insights?.length) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <CardTitle className="text-sm">AI Insights</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {data.insights.map((insight, i) => (
          <InsightCard key={i} insight={insight} />
        ))}
      </CardContent>
    </Card>
  );
}

export const AIInsightWidget = memo(AIInsightWidgetInner);
