import { Calendar } from 'lucide-react';
import { useSchedules } from '@/features/schedules/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { formatKRW } from '@/features/dashboard/lib/widget-format';
import { WidgetError } from './WidgetError';

export function PaymentScheduleWidget() {
  const { data: schedules, isLoading, isError } = useSchedules();

  const payments = (schedules ?? [])
    .filter((s) => s.type === 'expense' && s.is_active)
    .sort(
      (a, b) =>
        (a.schedule_day === 0 ? 32 : a.schedule_day) -
        (b.schedule_day === 0 ? 32 : b.schedule_day)
    );

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Calendar className="h-4 w-4" />
          월 결제 일정
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : isError ? (
          <WidgetError />
        ) : payments.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            등록된 결제 일정이 없습니다
          </p>
        ) : (
          <ul className="divide-y">
            {payments.map((payment) => (
              <li key={payment.id} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 min-w-6 items-center justify-center rounded-full bg-primary/10 px-1.5 text-xs font-bold text-primary">
                    {payment.schedule_day === 0 ? '말일' : payment.schedule_day}
                  </span>
                  <span className="text-sm">{payment.name}</span>
                </div>
                <span className="text-sm font-semibold text-destructive">
                  {formatKRW(payment.amount)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
