import { useDashboardSummary } from '@/features/dashboard/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { AlertCircle, Wallet, CreditCard, TrendingUp, TrendingDown } from 'lucide-react';

// ─── helpers ──────────────────────────────────────────────────────────────────

function formatKRW(amount: number): string {
  return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(amount);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const ENTRY_TYPE_LABELS: Record<string, string> = {
  income: '수입',
  expense: '지출',
  transfer: '이체',
  adjustment: '잔액조정',
  investment_buy: '매수',
  investment_sell: '매도',
};

// ─── skeleton / error ─────────────────────────────────────────────────────────

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-48 w-full rounded-xl" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  );
}

function DashboardError({ onRetry }: { onRetry: () => void }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center py-12">
        <AlertCircle className="mb-3 h-10 w-10 text-muted-foreground" aria-hidden="true" />
        <p className="text-muted-foreground">데이터를 불러올 수 없습니다.</p>
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
          다시 시도
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── sub-components ───────────────────────────────────────────────────────────

function SummaryCard({
  title,
  value,
  icon: Icon,
  sub,
}: {
  title: string;
  value: string;
  icon: React.ElementType;
  sub?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">{title}</p>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
        <p className="mt-1 text-xl font-bold">{value}</p>
        {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  );
}

// ─── main component ───────────────────────────────────────────────────────────

export function Component() {
  const { data, isLoading, isError, refetch } = useDashboardSummary();

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <DashboardSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6">
        <DashboardError onRetry={() => refetch()} />
      </div>
    );
  }

  const budget = data?.budget_overview;
  const entries = data?.recent_entries ?? [];

  return (
    <div className="space-y-6 p-6">
      {/* ── 요약 카드 4개 ── */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <SummaryCard
          title="총 자산"
          value={formatKRW(data?.total_assets_krw ?? 0)}
          icon={Wallet}
          sub={`계좌 ${data?.accounts_count ?? 0}개`}
        />
        <SummaryCard
          title="이번 달 수입"
          value={formatKRW(data?.monthly_income ?? 0)}
          icon={TrendingUp}
        />
        <SummaryCard
          title="이번 달 지출"
          value={formatKRW(data?.monthly_expense ?? 0)}
          icon={TrendingDown}
        />
        <SummaryCard
          title="사용 가능 예산"
          value={formatKRW(budget?.available_budget ?? 0)}
          icon={CreditCard}
          sub={budget ? `${budget.period_start} ~ ${budget.period_end}` : undefined}
        />
      </div>

      {/* ── 예산 개요 ── */}
      {budget && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">예산 개요</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm md:grid-cols-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">수입 합계</span>
                <span className="font-medium">{formatKRW(budget.total_income)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">고정 지출</span>
                <span className="font-medium">{formatKRW(budget.total_fixed_expense)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">이체 합계</span>
                <span className="font-medium">{formatKRW(budget.total_transfer)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">배분 완료</span>
                <span className="font-medium">{formatKRW(budget.total_allocated)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">미배분</span>
                <span
                  className={`font-medium ${budget.unallocated < 0 ? 'text-destructive' : 'text-green-600'}`}
                >
                  {formatKRW(budget.unallocated)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">가용 예산</span>
                <span
                  className={`font-semibold ${budget.available_budget < 0 ? 'text-destructive' : 'text-green-600'}`}
                >
                  {formatKRW(budget.available_budget)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── 최근 내역 ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">최근 내역</CardTitle>
        </CardHeader>
        <CardContent>
          {entries.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">최근 내역이 없습니다.</p>
          ) : (
            <ul className="divide-y">
              {entries.map((entry) => (
                <li key={entry.id} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    <Badge variant="secondary">
                      {ENTRY_TYPE_LABELS[entry.type] ?? entry.type}
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      {entry.memo ?? '메모 없음'}
                    </span>
                  </div>
                  <div className="text-right">
                    <p
                      className={`text-sm font-semibold ${
                        entry.amount < 0 ? 'text-destructive' : 'text-green-600'
                      }`}
                    >
                      {formatKRW(entry.amount)}
                    </p>
                    <p className="text-xs text-muted-foreground">{formatDate(entry.transacted_at)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
