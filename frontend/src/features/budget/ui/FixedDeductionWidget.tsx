import { memo } from 'react';
import { useBudgetAnalysis } from '../api/analysis';
import { formatKRW } from '@/shared/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { Badge } from '@/shared/ui/badge';

function FixedDeductionWidgetInner() {
  const { data, isLoading } = useBudgetAnalysis();

  if (isLoading) return <Skeleton className="h-48 rounded-xl" />;
  if (!data) return null;

  const { fixed_deductions } = data;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm text-muted-foreground">고정비/할부금 차감 현황</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex gap-4 mb-4 text-sm">
          <div className="flex-1 rounded-lg bg-muted p-3 text-center">
            <p className="text-muted-foreground">총 금액</p>
            <p className="font-bold">{formatKRW(fixed_deductions.total_amount)}</p>
          </div>
          <div className="flex-1 rounded-lg bg-green-500/10 p-3 text-center">
            <p className="text-muted-foreground">차감 완료</p>
            <p className="font-bold text-green-600">{formatKRW(fixed_deductions.paid_amount)}</p>
          </div>
          <div className="flex-1 rounded-lg bg-orange-500/10 p-3 text-center">
            <p className="text-muted-foreground">차감 예정</p>
            <p className="font-bold text-orange-600">{formatKRW(fixed_deductions.remaining_amount)}</p>
          </div>
        </div>
        <div className="space-y-2">
          {fixed_deductions.items.map((item, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg border border-border p-2.5 text-sm">
              <div className="flex items-center gap-2">
                <span className={`inline-block h-2 w-2 rounded-full ${item.is_paid ? 'bg-green-500' : 'bg-muted-foreground'}`} />
                <span>{item.name}</span>
                <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                  {item.item_type === 'fixed' ? '고정비' : '할부금'}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">{item.payment_day}일</span>
                <span className="font-medium">{formatKRW(item.amount)}</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export const FixedDeductionWidget = memo(FixedDeductionWidgetInner);
