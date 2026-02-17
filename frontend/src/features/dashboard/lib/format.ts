const krwFormatter = new Intl.NumberFormat('ko-KR');

export function formatKRW(amount: number, compact?: boolean): string {
  if (compact && Math.abs(amount) >= 100_000_000) {
    const eok = amount / 100_000_000;
    return `₩${eok.toFixed(1)}억`;
  }
  if (compact && Math.abs(amount) >= 10_000) {
    const man = Math.round(amount / 10_000);
    return `₩${krwFormatter.format(man)}만`;
  }
  return `₩${krwFormatter.format(Math.round(amount))}`;
}

export function formatPercent(rate: number): string {
  const sign = rate >= 0 ? '+' : '';
  return `${sign}${rate.toFixed(2)}%`;
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
}
