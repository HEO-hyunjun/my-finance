import { useMemo } from 'react';
import type { CalendarEvent, CalendarEventType } from '@/shared/types/calendar';
import { EVENT_TYPE_CONFIG } from '../lib/constants';
import { formatKRW } from '@/shared/lib/format';
import { Card } from '@/shared/ui/card';

interface Props {
  date: string;
  events: CalendarEvent[];
}

const EXPENSE_TYPES = new Set<string>(['expense', 'fixed_expense', 'installment']);

export function EventList({ date, events }: Props) {
  const d = new Date(date);
  const label = `${d.getMonth() + 1}월 ${d.getDate()}일`;

  const { expenseEvents, incomeEvents, expenseTotal, incomeTotal } = useMemo(() => {
    const exp: CalendarEvent[] = [];
    const inc: CalendarEvent[] = [];
    let expSum = 0;
    let incSum = 0;

    for (const e of events) {
      if (e.type === 'income') {
        inc.push(e);
        incSum += e.amount;
      } else if (EXPENSE_TYPES.has(e.type)) {
        exp.push(e);
        expSum += e.amount;
      } else {
        // maturity 등 기타 이벤트는 수입 쪽에 표시
        inc.push(e);
        incSum += e.amount;
      }
    }

    return { expenseEvents: exp, incomeEvents: inc, expenseTotal: expSum, incomeTotal: incSum };
  }, [events]);

  if (events.length === 0) {
    return (
      <Card className="p-6 text-center">
        <p className="text-sm text-muted-foreground">{label} - 일정이 없습니다.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold">{label}</h3>
        <div className="flex gap-4 text-sm">
          {incomeTotal > 0 && (
            <span className="text-amber-600 font-medium">+{formatKRW(incomeTotal)}</span>
          )}
          {expenseTotal > 0 && (
            <span className="text-red-500 font-medium">-{formatKRW(expenseTotal)}</span>
          )}
        </div>
      </div>

      {/* 수입 섹션 */}
      {incomeEvents.length > 0 && (
        <Card>
          <div className="border-b border-border px-4 py-2.5">
            <p className="text-xs font-semibold text-amber-600">수입 · 기타</p>
          </div>
          <div className="divide-y divide-border">
            {incomeEvents.map((event, i) => (
              <EventRow key={i} event={event} isIncome />
            ))}
          </div>
        </Card>
      )}

      {/* 지출 섹션 */}
      {expenseEvents.length > 0 && (
        <Card>
          <div className="border-b border-border px-4 py-2.5">
            <p className="text-xs font-semibold text-red-500">지출</p>
          </div>
          <div className="divide-y divide-border">
            {expenseEvents.map((event, i) => (
              <EventRow key={i} event={event} />
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function EventRow({ event, isIncome }: { event: CalendarEvent; isIncome?: boolean }) {
  const config = EVENT_TYPE_CONFIG[event.type as CalendarEventType];

  return (
    <div className="flex items-center justify-between px-4 py-3">
      <div className="flex items-center gap-3 min-w-0">
        <span
          className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
          style={{ backgroundColor: event.color || config.color }}
        />
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{event.title}</p>
          <p className="text-xs text-muted-foreground truncate">
            {config.label}
            {event.description ? ` · ${event.description}` : ''}
            {event.source_asset_name ? ` · ${event.source_asset_name}` : ''}
          </p>
        </div>
      </div>
      <span
        className={`ml-2 flex-shrink-0 text-sm font-medium ${
          isIncome ? 'text-amber-600' : 'text-red-500'
        }`}
      >
        {isIncome ? '+' : '-'}{formatKRW(event.amount)}
      </span>
    </div>
  );
}
