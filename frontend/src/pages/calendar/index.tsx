import { useState, useMemo } from 'react';
import { useCalendarEvents } from '@/features/calendar/api';
import { CalendarHeader } from '@/features/calendar/ui/CalendarHeader';
import { CalendarGrid } from '@/features/calendar/ui/CalendarGrid';
import { MonthSummaryCard } from '@/features/calendar/ui/MonthSummaryCard';
import { EventList } from '@/features/calendar/ui/EventList';
import { CalendarSkeleton } from '@/features/calendar/ui/CalendarSkeleton';

export function Component() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [selectedDate, setSelectedDate] = useState<string | null>(() => {
    const t = new Date();
    const yyyy = t.getFullYear();
    const mm = String(t.getMonth() + 1).padStart(2, '0');
    const dd = String(t.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  });

  const { data, isLoading } = useCalendarEvents(year, month);

  const selectedEvents = useMemo(() => {
    if (!selectedDate || !data) return [];
    return data.events.filter((e) => e.date === selectedDate);
  }, [selectedDate, data]);

  const handlePrev = () => {
    if (month === 1) {
      setYear((y) => y - 1);
      setMonth(12);
    } else {
      setMonth((m) => m - 1);
    }
    setSelectedDate(null);
  };

  const handleNext = () => {
    if (month === 12) {
      setYear((y) => y + 1);
      setMonth(1);
    } else {
      setMonth((m) => m + 1);
    }
    setSelectedDate(null);
  };

  const handleToday = () => {
    const today = new Date();
    setYear(today.getFullYear());
    setMonth(today.getMonth() + 1);
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    setSelectedDate(`${yyyy}-${mm}-${dd}`);
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-4 md:p-6">
        <CalendarSkeleton />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 md:p-6">
      {data && <MonthSummaryCard summary={data.month_summary} />}

      <CalendarHeader
        year={year}
        month={month}
        onPrev={handlePrev}
        onNext={handleNext}
        onToday={handleToday}
      />

      {data && (
        <CalendarGrid
          year={year}
          month={month}
          selectedDate={selectedDate}
          daySummaries={data.day_summaries}
          onSelectDate={setSelectedDate}
        />
      )}

      {selectedDate && (
        <EventList date={selectedDate} events={selectedEvents} />
      )}
    </div>
  );
}
