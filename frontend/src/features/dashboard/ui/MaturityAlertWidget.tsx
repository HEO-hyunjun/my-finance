import { memo } from 'react';
import type { DashboardMaturityAlert } from '@/shared/types/dashboard';
import { formatKRW } from '@/shared/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { AlertCircle } from 'lucide-react';

interface Props {
  alerts: DashboardMaturityAlert[];
}

function dDayColor(days: number): string {
  if (days <= 7) return 'text-red-600';
  if (days <= 14) return 'text-orange-500';
  return 'text-yellow-600';
}

function MaturityAlertWidgetInner({ alerts }: Props) {
  if (alerts.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-orange-500" />
          <CardTitle className="text-sm">만기 임박</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-border">
          {alerts.map((a, i) => (
            <div key={i} className="py-2.5">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{a.name}</span>
                <span className={`text-sm font-bold ${dDayColor(a.days_remaining)}`}>
                  D-{a.days_remaining}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                <span>
                  {a.bank_name && `${a.bank_name} · `}
                  원금 {formatKRW(a.principal)}
                </span>
                <span>만기일 {a.maturity_date}</span>
              </div>
              {a.maturity_amount != null && (
                <p className="mt-0.5 text-xs text-green-600">
                  예상 수령액 {formatKRW(a.maturity_amount)}
                </p>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export const MaturityAlertWidget = memo(MaturityAlertWidgetInner);
