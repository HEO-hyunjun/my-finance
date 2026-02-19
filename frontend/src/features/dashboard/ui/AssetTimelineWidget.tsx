import { useState, memo, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts';
import { useAssetTimeline } from '../api/portfolio';
import { formatKRW } from '@/shared/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from '@/shared/ui/chart';
import { Skeleton } from '@/shared/ui/skeleton';
import { cn } from '@/shared/lib/utils';
import { BarChart3 } from 'lucide-react';

const PERIODS = [
  { value: '1W', label: '1W' },
  { value: '1M', label: '1M' },
  { value: '3M', label: '3M' },
  { value: '6M', label: '6M' },
  { value: '1Y', label: '1Y' },
  { value: 'ALL', label: 'ALL' },
] as const;

const CHART_CONFIG: ChartConfig = {
  total: { label: '총 자산', color: '#1F2937' },
  stock_kr: { label: '국내주식', color: '#3B82F6' },
  stock_us: { label: '해외주식', color: '#8B5CF6' },
  gold: { label: '금', color: '#F59E0B' },
  cash_krw: { label: '원화', color: '#10B981' },
  cash_usd: { label: '달러', color: '#06B6D4' },
  deposit: { label: '예금', color: '#6366F1' },
  savings: { label: '적금', color: '#EC4899' },
  parking: { label: '파킹', color: '#84CC16' },
};

function formatAxisDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
}

function AssetTimelineWidgetInner() {
  const [period, setPeriod] = useState('1M');
  const { data: timeline, isLoading } = useAssetTimeline(period);

  const { assetTypes, chartData } = useMemo(() => {
    if (!timeline || timeline.snapshots.length === 0) {
      return { assetTypes: [] as string[], chartData: [] as Record<string, unknown>[] };
    }

    const assetTypeSet = new Set<string>();
    timeline.snapshots.forEach((snap) => {
      Object.keys(snap.breakdown).forEach((key) => assetTypeSet.add(key));
    });
    const assetTypes = Array.from(assetTypeSet);

    const chartData = timeline.snapshots.map((snap) => ({
      date: snap.snapshot_date,
      total: snap.total_krw,
      ...snap.breakdown,
    }));

    return { assetTypes, chartData };
  }, [timeline]);

  if (isLoading) {
    return <Skeleton className="h-80 rounded-xl" />;
  }

  if (!timeline || chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm">자산 추이</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="text-center">
          <p className="text-sm text-muted-foreground">
            자산 기록이 쌓이면 추이 차트를 볼 수 있어요.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm">자산 추이</CardTitle>
          </div>
          <div className="flex gap-1">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={cn(
                  'rounded-md px-2 py-1 text-xs font-medium transition-colors',
                  period === p.value
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent'
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ChartContainer config={CHART_CONFIG} className="h-56 w-full">
          <LineChart data={chartData}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatAxisDate}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
            />
            <YAxis
              tickFormatter={(v: number) => formatKRW(v, true)}
              tickLine={false}
              axisLine={false}
              width={70}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(label) => String(label)}
                  formatter={(value, name) => (
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-muted-foreground">
                        {CHART_CONFIG[name as string]?.label ?? name}
                      </span>
                      <span className="font-mono font-medium">
                        {formatKRW(Number(value), true)}
                      </span>
                    </div>
                  )}
                />
              }
            />
            <ChartLegend content={<ChartLegendContent />} />
            {/* Total line - bold */}
            <Line
              type="monotone"
              dataKey="total"
              stroke="var(--color-total)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            {/* Per-asset-type lines */}
            {assetTypes.map((assetType) => (
              <Line
                key={assetType}
                type="monotone"
                dataKey={assetType}
                stroke={`var(--color-${assetType})`}
                strokeWidth={1}
                dot={false}
                activeDot={{ r: 3 }}
              />
            ))}
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}

export const AssetTimelineWidget = memo(AssetTimelineWidgetInner);
