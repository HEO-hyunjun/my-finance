import type { ImportStatus, DedupStatus } from '@/entities/import/model/types';

export const STATUS_META: Record<ImportStatus, { label: string; className: string }> = {
  uploaded: { label: '분석 대기', className: 'bg-muted text-muted-foreground' },
  parsing: { label: '분석 중', className: 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300' },
  review: { label: '리뷰 대기', className: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300' },
  committed: { label: '커밋됨', className: 'bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-300' },
  failed: { label: '실패', className: 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300' },
};

export const DEDUP_META: Record<DedupStatus, { label: string; className: string }> = {
  new: { label: '신규', className: 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300' },
  probable: { label: '유사 중복', className: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300' },
  exact: { label: '중복', className: 'bg-muted text-muted-foreground' },
};

export function formatKRW(amount: number): string {
  try {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency', currency: 'KRW', maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString('ko-KR')} KRW`;
  }
}

export function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(iso));
  } catch {
    return iso;
  }
}
