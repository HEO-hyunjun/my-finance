import { memo, useMemo } from 'react';
import type { DashboardPayment } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Calendar } from 'lucide-react';

interface Props {
  payments: DashboardPayment[];
}

function PaymentScheduleWidgetInner({ payments }: Props) {
  const total = useMemo(
    () => payments.reduce((s, p) => s + p.amount, 0),
    [payments]
  );

  if (payments.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">이번 달 결제 일정</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          <p className="text-sm text-muted-foreground">등록된 결제 일정이 없습니다.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">이번 달 결제 일정</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-border">
          {payments.map((p, i) => (
            <div key={i} className="flex items-center justify-between py-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Calendar className="h-3 w-3 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">{p.payment_day}일</span>
                  <span className="truncate text-sm">{p.name}</span>
                </div>
                <Badge
                  variant={p.type === 'fixed' ? 'secondary' : 'default'}
                  className="mt-0.5 text-[10px] px-1.5 py-0"
                >
                  {p.type === 'fixed' ? '고정비' : `할부 ${p.remaining ?? ''}`}
                </Badge>
              </div>
              <span className="text-sm font-medium">{formatKRW(p.amount)}</span>
            </div>
          ))}
        </div>

        <div className="mt-3 border-t border-border pt-2 text-right text-xs text-muted-foreground">
          총 {formatKRW(total)}
        </div>
      </CardContent>
    </Card>
  );
}

export const PaymentScheduleWidget = memo(PaymentScheduleWidgetInner);
