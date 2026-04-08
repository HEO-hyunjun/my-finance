import { memo, useMemo } from 'react';
import { ASSET_TYPE_LABELS } from '@/shared/types/common';
import { formatKRW } from '@/shared/lib/format';
import { getAssetTypeColors } from '@/shared/lib/asset-colors';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  PieChart,
  Pie,
  Cell,
  Label,
  type ChartConfig,
} from '@/shared/ui/chart';

interface Props {
  breakdown: Record<string, number>;
  assetTypeColors?: Record<string, string>;
}

function AssetDistChartInner({ breakdown, assetTypeColors }: Props) {
  const { total, mainEntries, chartConfig } = useMemo(() => {
    const colors = getAssetTypeColors(assetTypeColors);
    const total = Object.values(breakdown).reduce((s, v) => s + v, 0);

    if (total === 0) {
      return { total: 0, mainEntries: [], chartConfig: {} as ChartConfig };
    }

    // 3% 미만 항목은 "기타"로 합산
    let etcValue = 0;
    const mainEntries: { name: string; key: string; value: number; fill: string }[] = [];

    Object.entries(breakdown).forEach(([key, value]) => {
      if (value / total < 0.03) {
        etcValue += value;
      } else {
        mainEntries.push({
          key,
          name: ASSET_TYPE_LABELS[key as keyof typeof ASSET_TYPE_LABELS] ?? key,
          value,
          fill: colors[key] ?? '#9CA3AF',
        });
      }
    });

    if (etcValue > 0) {
      mainEntries.push({ key: 'etc', name: '기타', value: etcValue, fill: '#9CA3AF' });
    }

    // ChartConfig 동적 생성
    const chartConfig: ChartConfig = {};
    mainEntries.forEach((entry) => {
      chartConfig[entry.name] = {
        label: entry.name,
        color: entry.fill,
      };
    });

    return { total, mainEntries, chartConfig };
  }, [breakdown, assetTypeColors]);

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
        <ChartContainer config={chartConfig} className="mx-auto aspect-square h-48">
          <PieChart>
            <ChartTooltip
              content={
                <ChartTooltipContent
                  formatter={(value) => formatKRW(Number(value), true)}
                  nameKey="name"
                />
              }
            />
            <Pie
              data={mainEntries}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              dataKey="value"
              nameKey="name"
              stroke="none"
            >
              {mainEntries.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
              <Label
                content={({ viewBox }) => {
                  if (viewBox && 'cx' in viewBox && 'cy' in viewBox) {
                    return (
                      <text x={viewBox.cx} y={viewBox.cy} textAnchor="middle" dominantBaseline="middle">
                        <tspan x={viewBox.cx} y={viewBox.cy} className="fill-foreground text-sm font-bold">
                          {formatKRW(total, true)}
                        </tspan>
                      </text>
                    );
                  }
                }}
              />
            </Pie>
          </PieChart>
        </ChartContainer>
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {mainEntries.map((entry) => (
            <span key={entry.name} className="flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.fill }} />
              {entry.name} {((entry.value / total) * 100).toFixed(1)}%
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export const AssetDistChart = memo(AssetDistChartInner);
