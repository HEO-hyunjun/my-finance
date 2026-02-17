import { memo, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { ASSET_TYPE_LABELS } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';

const ASSET_COLORS: Record<string, string> = {
  stock_kr: '#3B82F6',
  stock_us: '#8B5CF6',
  gold: '#F59E0B',
  cash_krw: '#10B981',
  cash_usd: '#06B6D4',
  deposit: '#6366F1',
  savings: '#EC4899',
  parking: '#84CC16',
};

interface Props {
  breakdown: Record<string, number>;
}

function AssetDistChartInner({ breakdown }: Props) {
  const { total, mainEntries } = useMemo(() => {
    const total = Object.values(breakdown).reduce((s, v) => s + v, 0);

    if (total === 0) {
      return { total: 0, mainEntries: [] };
    }

    // 3% 미만 항목은 "기타"로 합산
    let etcValue = 0;
    const mainEntries: { name: string; value: number; color: string }[] = [];

    Object.entries(breakdown).forEach(([key, value]) => {
      if (value / total < 0.03) {
        etcValue += value;
      } else {
        mainEntries.push({
          name: ASSET_TYPE_LABELS[key as keyof typeof ASSET_TYPE_LABELS] ?? key,
          value,
          color: ASSET_COLORS[key] ?? '#9CA3AF',
        });
      }
    });

    if (etcValue > 0) {
      mainEntries.push({ name: '기타', value: etcValue, color: '#9CA3AF' });
    }

    return { total, mainEntries };
  }, [breakdown]);

  if (total === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">자산 분포</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          <p className="text-sm text-muted-foreground">자산을 등록하면 분포 차트를 볼 수 있어요.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">자산 분포</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={mainEntries}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                dataKey="value"
                stroke="none"
              >
                {mainEntries.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number | undefined) => formatKRW(value ?? 0, true)}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {mainEntries.map((entry) => (
            <span key={entry.name} className="flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
              {entry.name} {((entry.value / total) * 100).toFixed(1)}%
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export const AssetDistChart = memo(AssetDistChartInner);
