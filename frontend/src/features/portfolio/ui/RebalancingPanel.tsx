import { useState } from 'react';
import { AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { cn } from '@/shared/lib/utils';
import { useRebalancingAnalysis } from '@/features/portfolio/api';

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  cash: '현금',
  deposit: '예금',
  savings: '적금',
  parking: '파킹',
  investment: '투자',
};

function formatPercent(ratio: number): string {
  return `${(ratio * 100).toFixed(1)}%`;
}

function formatDeviation(deviation: number): string {
  const sign = deviation >= 0 ? '+' : '';
  return `${sign}${(deviation * 100).toFixed(1)}%p`;
}

interface Suggestion {
  asset_type?: string;
  action?: string;
  amount?: number;
  [key: string]: unknown;
}

export function RebalancingPanel() {
  const [thresholdPercent, setThresholdPercent] = useState(5);
  const threshold = thresholdPercent / 100;
  const { data, isLoading } = useRebalancingAnalysis(threshold);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">리밸런싱 분석</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const hasTargets = (data?.targets?.length ?? 0) > 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">리밸런싱 분석</CardTitle>
          {hasTargets &&
            (data?.needs_rebalancing ? (
              <Badge variant="destructive" className="gap-1">
                <AlertTriangle className="h-3 w-3" />
                리밸런싱 필요
              </Badge>
            ) : (
              <Badge className="gap-1 bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/20 dark:text-emerald-400">
                <CheckCircle2 className="h-3 w-3" />
                균형 상태
              </Badge>
            ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <Label className="w-28 shrink-0 text-sm">허용 편차</Label>
          <Input
            type="number"
            min={1}
            max={20}
            step={1}
            value={thresholdPercent}
            onChange={(e) => setThresholdPercent(Number(e.target.value) || 5)}
            className="w-24 text-right"
          />
          <span className="text-sm text-muted-foreground">%</span>
          <span className="ml-auto text-sm text-muted-foreground">
            총 편차 {data ? formatPercent(data.total_deviation) : '—'}
          </span>
        </div>

        {!hasTargets ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            목표 비중이 설정되어 있지 않습니다. 위에서 목표 비중을 먼저
            설정해주세요.
          </p>
        ) : (
          <div className="overflow-hidden rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr className="text-left">
                  <th className="px-3 py-2 font-medium">자산 유형</th>
                  <th className="px-3 py-2 text-right font-medium">목표</th>
                  <th className="px-3 py-2 text-right font-medium">현재</th>
                  <th className="px-3 py-2 text-right font-medium">편차</th>
                </tr>
              </thead>
              <tbody>
                {data!.targets.map((t) => {
                  const exceeded = Math.abs(t.deviation) > threshold;
                  return (
                    <tr key={t.id} className="border-t">
                      <td className="px-3 py-2">
                        {ACCOUNT_TYPE_LABELS[t.asset_type] ?? t.asset_type}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {formatPercent(t.target_ratio)}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {formatPercent(t.current_ratio)}
                      </td>
                      <td
                        className={cn(
                          'px-3 py-2 text-right font-medium',
                          exceeded
                            ? t.deviation > 0
                              ? 'text-rose-600 dark:text-rose-400'
                              : 'text-blue-600 dark:text-blue-400'
                            : 'text-muted-foreground',
                        )}
                      >
                        {formatDeviation(t.deviation)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {hasTargets && (data?.suggestions?.length ?? 0) > 0 && (
          <div className="space-y-2">
            <Label className="text-sm font-medium">제안</Label>
            <ul className="space-y-1 rounded-lg border bg-muted/30 p-3 text-sm">
              {(data!.suggestions as unknown as Suggestion[]).map((s, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {s.action ?? '조정'}
                  </Badge>
                  <span>
                    {s.asset_type
                      ? ACCOUNT_TYPE_LABELS[s.asset_type] ?? s.asset_type
                      : '—'}
                  </span>
                  {typeof s.amount === 'number' && (
                    <span className="ml-auto text-muted-foreground">
                      {new Intl.NumberFormat('ko-KR', {
                        style: 'currency',
                        currency: 'KRW',
                        maximumFractionDigits: 0,
                      }).format(s.amount)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
