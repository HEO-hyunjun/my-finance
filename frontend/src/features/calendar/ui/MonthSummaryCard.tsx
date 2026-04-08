import type { MonthSummary } from '@/shared/types/calendar';
import { Card, CardContent } from '@/shared/ui/card';

interface Props {
  summary: MonthSummary;
}

function formatPeriod(start?: string, end?: string) {
  if (!start || !end) return null;
  const s = new Date(start);
  const e = new Date(end);
  const fmt = (d: Date) => `${d.getMonth() + 1}/${d.getDate()}`;
  return `${fmt(s)} ~ ${fmt(e)}`;
}

export function MonthSummaryCard({ summary }: Props) {
  const period = formatPeriod(summary.budget_period_start, summary.budget_period_end);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-baseline gap-2">
          <p className="text-sm font-medium text-foreground">{summary.month}월 요약</p>
          {period && (
            <span className="text-xs text-muted-foreground">({period})</span>
          )}
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3">
          <div>
            <p className="text-xs text-muted-foreground">수입</p>
            <p className="text-lg font-bold text-amber-600">
              {summary.total_income_amount.toLocaleString()}
              <span className="text-xs font-normal text-muted-foreground">원</span>
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">실제 지출</p>
            <p className="text-lg font-bold text-red-500">
              {summary.total_expense_amount.toLocaleString()}
              <span className="text-xs font-normal text-muted-foreground">원</span>
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">예정 결제</p>
            <p className="text-lg font-bold">
              {summary.total_scheduled_amount.toLocaleString()}
              <span className="text-xs font-normal text-muted-foreground">원</span>
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
