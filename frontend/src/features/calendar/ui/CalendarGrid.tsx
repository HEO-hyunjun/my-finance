import type { DaySummary } from '@/shared/types';
import { WEEKDAYS } from '../lib/constants';
import { getCalendarDays, toDateString } from '../lib/utils';
import { CalendarDayCell } from './CalendarDayCell';

interface Props {
  year: number;
  month: number;
  selectedDate: string | null;
  daySummaries: DaySummary[];
  onSelectDate: (date: string) => void;
}

export function CalendarGrid({ year, month, selectedDate, daySummaries, onSelectDate }: Props) {
  const days = getCalendarDays(year, month);
  const summaryMap = new Map(daySummaries.map((s) => [s.date, s]));
  const today = toDateString(new Date());

  return (
    <div className="rounded-xl border border-border bg-card">
      {/* 요일 헤더 */}
      <div className="grid grid-cols-7 border-b border-border">
        {WEEKDAYS.map((day, i) => (
          <div
            key={day}
            className={`py-2 text-center text-xs font-medium ${
              i === 0 ? 'text-red-400' : i === 6 ? 'text-blue-400' : 'text-muted-foreground'
            }`}
          >
            {day}
          </div>
        ))}
      </div>

      {/* 날짜 그리드 */}
      <div className="grid grid-cols-7">
        {days.map((day) => {
          const dateStr = toDateString(day.date);
          return (
            <CalendarDayCell
              key={dateStr}
              date={day.date}
              isCurrentMonth={day.isCurrentMonth}
              isToday={dateStr === today}
              isSelected={dateStr === selectedDate}
              summary={summaryMap.get(dateStr)}
              onClick={() => onSelectDate(dateStr)}
            />
          );
        })}
      </div>
    </div>
  );
}
