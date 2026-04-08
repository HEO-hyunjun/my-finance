import { memo } from 'react';
import type { DashboardMarketInfo } from '@/shared/types/dashboard';
import { formatKRW } from '@/shared/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface Props {
  market: DashboardMarketInfo;
}

const ChangeIndicator = memo(function ChangeIndicator({ change }: { change?: number }) {
  if (change == null || change === 0) return null;
  // 한국 관행: 상승 = 빨강, 하락 = 파랑
  const isUp = change > 0;
  return (
    <span className={`flex items-center gap-0.5 text-xs font-medium ${isUp ? 'text-red-500' : 'text-blue-500'}`}>
      {isUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
      {Math.abs(change).toLocaleString()}
    </span>
  );
});

function MarketInfoWidgetInner({ market }: Props) {
  const { exchange_rate, gold_price } = market;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">시세 정보</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">USD/KRW</span>
            <div className="flex items-center gap-2 text-right">
              <span className="text-sm font-bold">{formatKRW(exchange_rate.price)}</span>
              <ChangeIndicator change={exchange_rate.change} />
            </div>
          </div>

          {gold_price && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">금 (g)</span>
              <div className="flex items-center gap-2 text-right">
                <span className="text-sm font-bold">{formatKRW(gold_price.price)}</span>
                <ChangeIndicator change={gold_price.change} />
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export const MarketInfoWidget = memo(MarketInfoWidgetInner);
