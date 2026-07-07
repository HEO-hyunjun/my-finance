import {
  PieChart,
  Pie,
  Cell,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';
import { useDashboardSummary } from '@/features/dashboard/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW } from '@/features/dashboard/lib/widget-format';
import { WidgetError } from './WidgetError';

const PIE_COLORS = ['#6366f1', '#06b6d4', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'];

export function AssetDistributionWidget() {
  const { data: summary, isLoading, isError } = useDashboardSummary();

  const distribution: { label: string; amount: number }[] = (summary?.asset_distribution ?? []).map(
    (d: { label: string; amount: number }) => ({ label: d.label, amount: Number(d.amount) }),
  );
  const total = summary?.total_assets_krw ?? 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">자산 분포</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="mx-auto h-40 w-40 rounded-full" />
        ) : isError ? (
          <WidgetError />
        ) : distribution.length === 0 ? (
          <div className="flex h-40 items-center justify-center">
            <p className="text-sm text-muted-foreground">자산 데이터가 없습니다</p>
          </div>
        ) : (
          <div className="space-y-3">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={distribution}
                  dataKey="amount"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                >
                  {distribution.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip
                  formatter={(value: number, name: string) => [formatKRW(value), name]}
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="text-center text-xs text-muted-foreground">
              총 자산 <span className="font-bold text-foreground">{formatKRW(total)}</span>
            </div>
            <div className="space-y-1">
              {distribution.map((d, i) => (
                <div key={d.label} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-sm"
                      style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                    />
                    {d.label}
                  </span>
                  <span className="font-medium">{formatKRW(d.amount)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
