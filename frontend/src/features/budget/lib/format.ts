export function formatCurrency(amount: number): string {
  try {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'KRW',
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString('ko-KR')} KRW`;
  }
}

export function formatPercent(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}
