import { memo } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardContent } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { formatKRW } from '@/shared/lib/format';
import { getAssetIcon } from '@/shared/lib/icons';
import { ASSET_TYPE_LABELS } from '@/shared/types';
import type { AssetSummary } from '@/shared/types';

interface Props {
  summary: AssetSummary;
}

function AssetSummaryCardInner({ summary }: Props) {
  const isPositive = summary.total_profit_loss >= 0;

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="mb-4">
          <p className="text-sm text-muted-foreground">총 자산</p>
          <p className="text-3xl font-bold tracking-tight">{formatKRW(summary.total_value_krw)}</p>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant={isPositive ? 'default' : 'destructive'} className="gap-1">
              {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {isPositive ? '+' : ''}{summary.total_profit_loss_rate.toFixed(1)}%
            </Badge>
            <span className={`text-sm font-medium ${isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {isPositive ? '+' : ''}{formatKRW(summary.total_profit_loss)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {Object.entries(summary.breakdown).map(([type, value]) => {
            const Icon = getAssetIcon(type);
            return (
              <div key={type} className="rounded-lg bg-muted p-3">
                <div className="flex items-center gap-1.5">
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                  <p className="text-xs text-muted-foreground">
                    {ASSET_TYPE_LABELS[type as keyof typeof ASSET_TYPE_LABELS] || type}
                  </p>
                </div>
                <p className="mt-1 text-sm font-semibold">{formatKRW(value)}</p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export const AssetSummaryCard = memo(AssetSummaryCardInner);
