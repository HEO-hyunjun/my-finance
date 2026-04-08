import { useState, memo, useMemo } from 'react';
import { useAssetTimeline } from '../api/portfolio';
import { ASSET_TYPE_LABELS } from '@/shared/types/common';
import { formatKRW } from '@/shared/lib/format';
import { getAssetTypeColors } from '@/shared/lib/asset-colors';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
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

const ASSET_TYPE_CHART_LABELS: Record<string, string> = {
  total: '총 자산',
  stock_kr: '국내주식',
  stock_us: '해외주식',
  gold: '금',
  cash_krw: '원화',
  cash_usd: '달러',
  deposit: '예금',
  savings: '적금',
  parking: '파킹',
};

function formatAxisDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
}

interface Props {
  assetTypeColors?: Record<string, string>;
}

function AssetTimelineWidgetInner({ assetTypeColors }: Props) {
  const [period, setPeriod] = useState('1M');
  const { data: timeline, isLoading } = useAssetTimeline(period);

  const { assetTypes, chartData, chartConfig } = useMemo(() => {
    const colors = getAssetTypeColors(assetTypeColors);
    if (!timeline || timeline.snapshots.length === 0) {
      return { assetTypes: [] as string[], chartData: [] as Record<string, unknown>[], chartConfig: {} as ChartConfig };
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

    const chartConfig: ChartConfig = {
      total: { label: '총 자산', color: '#1F2937' },
    };
    assetTypes.forEach((type) => {
      chartConfig[type] = {
        label: ASSET_TYPE_CHART_LABELS[type] ?? ASSET_TYPE_LABELS[type as keyof typeof ASSET_TYPE_LABELS] ?? type,
        color: colors[type] ?? '#9CA3AF',
      };
    });

    return { assetTypes, chartData, chartConfig };
  }, [timeline, assetTypeColors]);

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
        <ChartContainer config={chartConfig} className="h-56 w-full">
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
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-muted-foreground">
                        {chartConfig[name as string]?.label ?? name}
                      </span>
                      <span className="shrink-0 font-mono font-medium">
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
