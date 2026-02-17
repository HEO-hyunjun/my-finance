import { memo } from 'react';
import type { DashboardTransaction } from '@/shared/types';
import { TRANSACTION_TYPE_LABELS } from '@/shared/types';
import { formatKRW, formatDate } from '@/shared/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { ArrowRight } from 'lucide-react';

interface Props {
  transactions: DashboardTransaction[];
}

const TX_TYPE_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  buy: 'default',
  sell: 'destructive',
  exchange: 'secondary',
};

function RecentTxWidgetInner({ transactions }: Props) {
  if (transactions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">최근 거래</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          <p className="text-sm text-muted-foreground">아직 거래 내역이 없습니다.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">최근 거래</CardTitle>
          <a href="/assets" className="flex items-center gap-1 text-xs text-primary hover:underline">
            전체보기 <ArrowRight className="h-3 w-3" />
          </a>
        </div>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-border">
          {transactions.map((tx) => (
            <div key={tx.id} className="flex items-center justify-between py-2.5">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{tx.asset_name}</p>
                <div className="flex items-center gap-1.5 text-xs">
                  <Badge variant={TX_TYPE_VARIANT[tx.type] ?? 'outline'} className="text-[10px] px-1.5 py-0">
                    {TRANSACTION_TYPE_LABELS[tx.type as keyof typeof TRANSACTION_TYPE_LABELS] ?? tx.type}
                  </Badge>
                  {tx.quantity > 0 && (
                    <span className="text-muted-foreground">
                      {tx.quantity}
                      {tx.asset_type.includes('stock') ? '주' : ''}
                    </span>
                  )}
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">
                  {tx.currency === 'USD' ? `$${tx.unit_price.toLocaleString()}` : formatKRW(tx.quantity * tx.unit_price)}
                </p>
                <p className="text-xs text-muted-foreground">{formatDate(tx.transacted_at)}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export const RecentTxWidget = memo(RecentTxWidgetInner);
