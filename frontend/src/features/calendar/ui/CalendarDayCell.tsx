import type { DaySummary, CalendarEventType } from '@/shared/types/calendar';
import { EVENT_TYPE_CONFIG } from '../lib/constants';
import { formatAmount } from '../lib/utils';

interface Props {
  date: Date;
  isCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  summary?: DaySummary;
  onClick: () => void;
}

export function CalendarDayCell({
  date,
  isCurrentMonth,
  isToday,
  isSelected,
  summary,
  onClick,
}: Props) {
  return (
    <button
      onClick={onClick}
      className={`flex h-14 flex-col items-center justify-start gap-0.5 border-b border-r border-border p-1 transition-colors md:h-20 ${
        !isCurrentMonth ? 'text-muted-foreground/30' : ''
      } ${isSelected ? 'bg-primary/5' : 'hover:bg-muted/50'}`}
    >
      <span
        className={`text-xs md:text-sm ${
          isToday
            ? 'flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground'
            : ''
        }`}
      >
        {date.getDate()}
      </span>

      {/* 수입/지출 금액 표시 */}
      {summary && isCurrentMonth && (
        <div className="hidden flex-col items-center gap-0 md:flex">
          {summary.total_income > 0 && (
            <span className="text-[10px] font-medium text-green-600">
              +{formatAmount(summary.total_income)}
            </span>
          )}
          {summary.total_expense > 0 && (
            <span className="text-[10px] font-medium text-red-500">
              -{formatAmount(summary.total_expense)}
            </span>
          )}
        </div>
      )}

      {/* 이벤트 dot 표시 (모바일) */}
      {summary && (
        <div className="flex gap-0.5 md:hidden">
          {summary.event_types.map((type) => (
            <span
              key={type}
              className="h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: EVENT_TYPE_CONFIG[type as CalendarEventType].color }}
            />
          ))}
        </div>
      )}
    </button>
  );
}
