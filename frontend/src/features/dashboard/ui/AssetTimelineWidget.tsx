import { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp } from 'lucide-react';
import { useAssetTimeline } from '@/features/portfolio/api';
import { useAppSettings } from '@/features/settings/api/settings-api';
import { getAssetTypeColors } from '@/shared/lib/asset-colors';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { Button } from '@/shared/ui/button';
import { formatKRW, formatShortDate } from '@/features/dashboard/lib/widget-format';
import { WidgetError } from './WidgetError';

const PERIOD_OPTIONS = ['1W', '1M', '3M', '6M', '1Y', 'ALL'] as const;
type PeriodOption = (typeof PERIOD_OPTIONS)[number];

const BREAKDOWN_KEYS: { key: string; label: string }[] = [
  { key: 'investment', label: '투자' },
  { key: 'cash', label: '현금' },
  { key: 'parking', label: '파킹' },
  { key: 'savings', label: '적금' },
  { key: 'deposit', label: '예금' },
];

export function AssetTimelineWidget() {
  const [period, setPeriod] = useState<PeriodOption>('1M');
  const { data, isLoading, isError } = useAssetTimeline(period);
  const { data: settings } = useAppSettings();
  const colors = getAssetTypeColors(settings?.asset_type_colors ?? undefined);
  const BREAKDOWN_CONFIG = BREAKDOWN_KEYS.map((b) => ({
    ...b,
    color: colors[b.key] ?? '#9CA3AF',
  }));

  const chartData =
    data?.snapshots.map((s) => ({
      date: formatShortDate(s.snapshot_date),
      total: s.total_krw,
      ...(s.breakdown ?? {}),
    })) ?? [];

  // breakdown에 존재하는 키만 필터
  const activeKeys = BREAKDOWN_CONFIG.filter((cfg) =>
    chartData.some((d) => (d[cfg.key as keyof typeof d] as number) > 0),
  );

  return (
    <Card className="col-span-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4" />
            자산 추이
          </CardTitle>
          <div className="flex gap-1">
            {PERIOD_OPTIONS.map((p) => (
              <Button
                key={p}
                variant={period === p ? 'default' : 'ghost'}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setPeriod(p)}
              >
                {p}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : isError ? (
          <WidgetError />
        ) : chartData.length === 0 ? (
          <div className="flex h-48 items-center justify-center">
            <p className="text-sm text-muted-foreground">데이터가 없습니다</p>
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <defs>
                  {activeKeys.map((cfg) => (
                    <linearGradient key={cfg.key} id={`grad_${cfg.key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={cfg.color} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={cfg.color} stopOpacity={0.02} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(v: number) =>
                    v >= 100_000_000
                      ? `${(v / 100_000_000).toFixed(0)}억`
                      : v >= 10_000
                      ? `${(v / 10_000).toFixed(0)}만`
                      : `${v}`
                  }
                  tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                  axisLine={false}
                  tickLine={false}
                  width={48}
                />
                <RechartsTooltip
                  formatter={(value: number, name: string) => {
                    const cfg = BREAKDOWN_CONFIG.find((c) => c.key === name);
                    return [formatKRW(value), cfg?.label ?? name];
                  }}
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                {activeKeys.map((cfg) => (
                  <Area
                    key={cfg.key}
                    type="monotone"
                    dataKey={cfg.key}
                    stackId="1"
                    stroke={cfg.color}
                    strokeWidth={1.5}
                    fill={`url(#grad_${cfg.key})`}
                    dot={false}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
            {/* 범례 */}
            <div className="mt-2 flex flex-wrap gap-3 justify-center">
              {activeKeys.map((cfg) => (
                <span key={cfg.key} className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: cfg.color }} />
                  {cfg.label}
                </span>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
