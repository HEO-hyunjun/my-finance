export interface CalendarDay {
  date: Date;
  isCurrentMonth: boolean;
}

/**
 * 해당 월의 캘린더 그리드 데이터를 생성.
 * 7열 x 6행 (이전 달 / 현재 달 / 다음 달 날짜 포함)
 */
export function getCalendarDays(year: number, month: number): CalendarDay[] {
  const firstDay = new Date(year, month - 1, 1);
  const lastDay = new Date(year, month, 0);
  const startDayOfWeek = firstDay.getDay(); // 0(일) ~ 6(토)
  const totalDays = lastDay.getDate();

  const days: CalendarDay[] = [];

  // 이전 달 날짜 (빈 칸)
  const prevLastDay = new Date(year, month - 1, 0).getDate();
  for (let i = startDayOfWeek - 1; i >= 0; i--) {
    days.push({
      date: new Date(year, month - 2, prevLastDay - i),
      isCurrentMonth: false,
    });
  }

  // 현재 달 날짜
  for (let d = 1; d <= totalDays; d++) {
    days.push({
      date: new Date(year, month - 1, d),
      isCurrentMonth: true,
    });
  }

  // 다음 달 날짜 (6행 채우기)
  const remaining = 42 - days.length;
  for (let d = 1; d <= remaining; d++) {
    days.push({
      date: new Date(year, month, d),
      isCurrentMonth: false,
    });
  }

  return days;
}

/** Date → "2026-02-15" 문자열 변환 */
export function toDateString(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** 금액 포맷 (만 단위 축약) */
export function formatAmount(amount: number): string {
  if (amount >= 10000) {
    return `${Math.round(amount / 10000)}만`;
  }
  return amount.toLocaleString();
}
