import type { CalendarEventType } from '@/shared/types/calendar';

export const EVENT_TYPE_CONFIG: Record<
  CalendarEventType,
  { label: string; color: string; bgColor: string }
> = {
  fixed_expense: { label: '고정비', color: '#6B7280', bgColor: 'bg-gray-100' },
  installment: { label: '할부', color: '#3B82F6', bgColor: 'bg-blue-100' },
  maturity: { label: '만기', color: '#10B981', bgColor: 'bg-green-100' },
  expense: { label: '지출', color: '#EF4444', bgColor: 'bg-red-100' },
  income: { label: '수입', color: '#22C55E', bgColor: 'bg-green-100' },
};

export const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'] as const;
