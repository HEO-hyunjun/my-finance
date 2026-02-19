import { memo } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown, Wallet } from 'lucide-react';
import { Card, CardContent } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { formatKRW, formatPercent } from '@/shared/lib/format';
import type { DashboardAssetSummary } from '@/shared/types';

interface Props {
  summary: DashboardAssetSummary;
}

function TotalAssetWidgetInner({ summary }: Props) {
  const { total_value_krw, total_invested_krw, total_profit_loss, total_profit_loss_rate, daily_change, daily_change_rate } = summary;
  const isPositive = total_profit_loss >= 0;
  const isDailyPositive = (daily_change ?? 0) >= 0;

  if (total_value_krw === 0 && total_invested_krw === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center py-8">
          <Wallet className="mb-3 h-10 w-10 text-muted-foreground" />
          <p className="text-muted-foreground">아직 등록된 자산이 없습니다.</p>
          <Link to="/assets" className="mt-2 text-sm text-primary hover:underline">
            자산 추가하기 &rarr;
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">내 총 자산</p>
        <p className="mt-1 text-3xl font-bold tracking-tight">{formatKRW(total_value_krw)}</p>
        <div className="mt-2 flex items-center gap-2">
          <Badge variant={isPositive ? 'default' : 'destructive'} className="gap-1">
            {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {formatPercent(total_profit_loss_rate)}
          </Badge>
          <span className={`text-sm font-medium ${isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {isPositive ? '+' : ''}{formatKRW(Math.abs(total_profit_loss))}
          </span>
        </div>
        {daily_change != null && (
          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
            <span>전일대비</span>
            <span className={isDailyPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
              {isDailyPositive ? '+' : ''}{formatKRW(daily_change)}
              {daily_change_rate != null && ` (${formatPercent(daily_change_rate)})`}
            </span>
          </div>
        )}
        <p className="mt-2 text-xs text-muted-foreground">
          투자금 {formatKRW(total_invested_krw)}
        </p>
      </CardContent>
    </Card>
  );
}

export const TotalAssetWidget = memo(TotalAssetWidgetInner);
