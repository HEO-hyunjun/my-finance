import { Bell, Check, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import {
  useMarkAlertRead,
  useRebalancingAlerts,
} from '@/features/portfolio/api';

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  cash: '현금',
  deposit: '예금',
  savings: '적금',
  parking: '파킹',
  investment: '투자',
};

function formatPercent(ratio: number): string {
  const sign = ratio >= 0 ? '+' : '';
  return `${sign}${(ratio * 100).toFixed(1)}%p`;
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function AlertsList() {
  const { data, isLoading } = useRebalancingAlerts();
  const markRead = useMarkAlertRead();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">리밸런싱 알림</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const alerts = data ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">리밸런싱 알림</CardTitle>
          {alerts.length > 0 && (
            <Badge variant="outline" className="gap-1">
              <Bell className="h-3 w-3" />
              {alerts.filter((a) => !a.is_read).length} / {alerts.length}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            알림이 없습니다.
          </p>
        ) : (
          <ul className="space-y-2">
            {alerts.map((alert) => (
              <li
                key={alert.id}
                className={
                  'rounded-lg border p-3 transition-colors ' +
                  (alert.is_read ? 'bg-muted/20' : 'bg-background')
                }
              >
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">
                      {formatDate(alert.snapshot_date)}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      허용 {(alert.threshold * 100).toFixed(0)}%
                    </Badge>
                    {!alert.is_read && (
                      <Badge className="bg-rose-500/15 text-rose-600 hover:bg-rose-500/20 dark:text-rose-400">
                        미확인
                      </Badge>
                    )}
                  </div>
                  {!alert.is_read && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => markRead.mutate(alert.id)}
                      disabled={markRead.isPending}
                    >
                      <Check className="mr-1 h-4 w-4" />
                      읽음
                    </Button>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(alert.deviations).map(([type, dev]) => (
                    <Badge
                      key={type}
                      variant="outline"
                      className="text-xs font-normal"
                    >
                      {ACCOUNT_TYPE_LABELS[type] ?? type}{' '}
                      <span
                        className={
                          'ml-1 ' +
                          ((dev as number) >= 0
                            ? 'text-rose-600 dark:text-rose-400'
                            : 'text-blue-600 dark:text-blue-400')
                        }
                      >
                        {formatPercent(dev as number)}
                      </span>
                    </Badge>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
