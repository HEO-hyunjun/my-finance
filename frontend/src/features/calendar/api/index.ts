import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type { CalendarEventsResponse } from '@/shared/types';

export const calendarKeys = {
  all: ['calendar'] as const,
  events: (year: number, month: number) =>
    [...calendarKeys.all, 'events', year, month] as const,
};

export function useCalendarEvents(year: number, month: number) {
  return useQuery({
    queryKey: calendarKeys.events(year, month),
    queryFn: async (): Promise<CalendarEventsResponse> => {
      const { data } = await apiClient.get(
        `/v1/calendar/events?year=${year}&month=${month}`,
      );
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
