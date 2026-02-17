import { useState, memo, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import { useAssetTimeline } from '../api/portfolio';
import { formatKRW } from '@/shared/lib/format';
import { ASSET_TYPE_LABELS } from '@/shared/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
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

const LINE_COLORS: Record<string, string> = {
  stock_kr: '#3B82F6',
  stock_us: '#8B5CF6',
  gold: '#F59E0B',
  cash_krw: '#10B981',
  cash_usd: '#06B6D4',
  deposit: '#6366F1',
  savings: '#EC4899',
  parking: '#84CC16',
  total: '#1F2937',
};

function formatAxisDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
}

function AssetTimelineWidgetInner() {
  const [period, setPeriod] = useState('1M');
  const { data: timeline, isLoading } = useAssetTimeline(period);

  // hooks는 항상 동일한 순서로 호출되어야 하므로 early return 전에 선언
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
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
                tickFormatter={formatAxisDate}
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v: number) => formatKRW(v, true)}
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={false}
                tickLine={false}
                width={70}
              />
              <Tooltip
                labelFormatter={(label: unknown) => String(label)}
                formatter={(value: number | undefined, name: string | undefined) => [
                  formatKRW(value ?? 0, true),
                  name === 'total'
                    ? '총 자산'
                    : (ASSET_TYPE_LABELS[name as keyof typeof ASSET_TYPE_LABELS] ?? name),
                ]}
              />
              <Legend
                formatter={(value: string) =>
                  value === 'total'
                    ? '총 자산'
                    : (ASSET_TYPE_LABELS[value as keyof typeof ASSET_TYPE_LABELS] ?? value)
                }
              />
              {/* Total line - bold */}
              <Line
                type="monotone"
                dataKey="total"
                stroke={LINE_COLORS.total}
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
                  stroke={LINE_COLORS[assetType] ?? '#9CA3AF'}
                  strokeWidth={1}
                  dot={false}
                  activeDot={{ r: 3 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

export const AssetTimelineWidget = memo(AssetTimelineWidgetInner);
