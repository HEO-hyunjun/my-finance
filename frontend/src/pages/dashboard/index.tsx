import { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  AlertCircle,
  Wallet,
  Target,
  TrendingUp,
  TrendingDown,
  Calendar,
  Lightbulb,
  DollarSign,
} from 'lucide-react';

import { useDashboardSummary, useDashboardInsights } from '@/features/dashboard/api';
import { useGoal, useAssetTimeline } from '@/features/portfolio/api';
import { useExchangeRate, useMarketPrice } from '@/features/market/api';
import { useBudgetAnalysis } from '@/features/budget/api';
import { useSchedules } from '@/features/schedules/api';

import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';

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

function formatShortDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
}

const ENTRY_TYPE_LABELS: Record<string, string> = {
  income: '수입',
  expense: '지출',
  transfer: '이체',
  adjustment: '잔액조정',
  investment_buy: '매수',
  investment_sell: '매도',
};


// ─── widget error boundary helper ─────────────────────────────────────────────

function WidgetError({ message = '데이터를 불러올 수 없습니다' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <AlertCircle className="mb-2 h-6 w-6 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

// ─── 1. Total Assets Widget ────────────────────────────────────────────────────

function TotalAssetsWidget() {
  const { data, isLoading, isError } = useDashboardSummary();

  return (
    <Card className="col-span-2">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Wallet className="h-4 w-4" />
          총 자산
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        ) : isError ? (
          <WidgetError />
        ) : (
          <div className="space-y-1">
            <p className="text-3xl font-bold tracking-tight">
              {formatKRW(data?.total_assets_krw ?? 0)}
            </p>
            <p className="text-sm text-muted-foreground">
              계좌 {data?.accounts_count ?? 0}개 연동 중
            </p>
            <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">이번 달 수입</p>
                <p className="font-semibold text-green-600">
                  {formatKRW(data?.monthly_income ?? 0)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">이번 달 지출</p>
                <p className="font-semibold text-destructive">
                  {formatKRW(data?.monthly_expense ?? 0)}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 2. Goal Asset Widget ──────────────────────────────────────────────────────

function GoalAssetWidget() {
  const { data, isLoading, isError, error } = useGoal();

  const isNotFound =
    isError &&
    error &&
    typeof error === 'object' &&
    'response' in error &&
    (error as { response?: { status?: number } }).response?.status === 404;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Target className="h-4 w-4" />
          목표 자산
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-4 w-32" />
          </div>
        ) : isNotFound || !data ? (
          <div className="flex flex-col items-center py-6 text-center">
            <Target className="mb-2 h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">목표가 설정되지 않았습니다</p>
            <a
              href="/settings"
              className="mt-2 text-xs text-primary underline underline-offset-2"
            >
              목표 설정하기
            </a>
          </div>
        ) : isError ? (
          <WidgetError />
        ) : (
          <div className="space-y-3">
            <div>
              <p className="text-sm text-muted-foreground">목표 금액</p>
              <p className="text-xl font-bold">{formatKRW(data.target_amount)}</p>
            </div>
            {/* 달성률 바 */}
            <div>
              <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                <span>달성률</span>
                <span>{(data.achievement_rate * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${Math.min(data.achievement_rate * 100, 100)}%` }}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-muted-foreground">현재 자산</p>
                <p className="font-medium">{formatKRW(data.current_amount)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">남은 금액</p>
                <p className="font-medium">{formatKRW(data.remaining_amount)}</p>
              </div>
              {data.monthly_required != null && (
                <div>
                  <p className="text-muted-foreground">월 필요 저축</p>
                  <p className="font-medium">{formatKRW(data.monthly_required)}</p>
                </div>
              )}
              {data.estimated_date && (
                <div>
                  <p className="text-muted-foreground">달성 예상</p>
                  <p className="font-medium">
                    {new Date(data.estimated_date).toLocaleDateString('ko-KR', {
                      year: 'numeric',
                      month: 'short',
                    })}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 3. Asset Timeline Chart Widget ───────────────────────────────────────────

const PERIOD_OPTIONS = ['1W', '1M', '3M', '6M', '1Y', 'ALL'] as const;
type PeriodOption = (typeof PERIOD_OPTIONS)[number];

const BREAKDOWN_CONFIG: { key: string; label: string; color: string }[] = [
  { key: 'investment', label: '투자', color: '#6366f1' },
  { key: 'cash', label: '현금', color: '#f59e0b' },
  { key: 'parking', label: '파킹', color: '#10b981' },
  { key: 'savings', label: '적금', color: '#06b6d4' },
  { key: 'deposit', label: '예금', color: '#8b5cf6' },
];

function AssetTimelineWidget() {
  const [period, setPeriod] = useState<PeriodOption>('1M');
  const { data, isLoading, isError } = useAssetTimeline(period);

  const chartData =
    data?.snapshots.map((s) => ({
      date: formatShortDate(s.snapshot_date),
      total: s.total_krw,
      ...(s.breakdown ?? {}),
    })) ?? [];

  // breakdown에 존재하는 키만 필터
  const activeKeys = BREAKDOWN_CONFIG.filter((cfg) =>
    chartData.some((d) => (d[cfg.key as keyof typeof d] as number) > 0),
  );

  return (
    <Card className="col-span-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4" />
            자산 추이
          </CardTitle>
          <div className="flex gap-1">
            {PERIOD_OPTIONS.map((p) => (
              <Button
                key={p}
                variant={period === p ? 'default' : 'ghost'}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setPeriod(p)}
              >
                {p}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : isError ? (
          <WidgetError />
        ) : chartData.length === 0 ? (
          <div className="flex h-48 items-center justify-center">
            <p className="text-sm text-muted-foreground">데이터가 없습니다</p>
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <defs>
                  {activeKeys.map((cfg) => (
                    <linearGradient key={cfg.key} id={`grad_${cfg.key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={cfg.color} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={cfg.color} stopOpacity={0.02} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(v: number) =>
                    v >= 100_000_000
                      ? `${(v / 100_000_000).toFixed(0)}억`
                      : v >= 10_000
                      ? `${(v / 10_000).toFixed(0)}만`
                      : `${v}`
                  }
                  tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                  axisLine={false}
                  tickLine={false}
                  width={48}
                />
                <RechartsTooltip
                  formatter={(value: number, name: string) => {
                    const cfg = BREAKDOWN_CONFIG.find((c) => c.key === name);
                    return [formatKRW(value), cfg?.label ?? name];
                  }}
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                {activeKeys.map((cfg) => (
                  <Area
                    key={cfg.key}
                    type="monotone"
                    dataKey={cfg.key}
                    stackId="1"
                    stroke={cfg.color}
                    strokeWidth={1.5}
                    fill={`url(#grad_${cfg.key})`}
                    dot={false}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
            {/* 범례 */}
            <div className="mt-2 flex flex-wrap gap-3 justify-center">
              {activeKeys.map((cfg) => (
                <span key={cfg.key} className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: cfg.color }} />
                  {cfg.label}
                </span>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 4. Today's Daily Budget Widget ───────────────────────────────────────────

function DailyBudgetWidget() {
  const { data, isLoading, isError } = useBudgetAnalysis();

  const daily = data?.daily_budget;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <DollarSign className="h-4 w-4" />
          오늘 사용 가능 예산
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-36" />
            <Skeleton className="h-4 w-24" />
          </div>
        ) : isError || !daily ? (
          <WidgetError />
        ) : (
          <div className="space-y-3">
            <div>
              <p className="text-sm text-muted-foreground">하루 가용 예산</p>
              <p className="text-2xl font-bold text-primary">
                {formatKRW(daily.daily_available)}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-muted-foreground">오늘 사용</p>
                <p className="font-semibold text-destructive">
                  {formatKRW(daily.today_spent)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">남은 일수</p>
                <p className="font-semibold">{daily.remaining_days}일</p>
              </div>
              <div>
                <p className="text-muted-foreground">남은 예산</p>
                <p
                  className={`font-semibold ${
                    daily.remaining_budget < 0 ? 'text-destructive' : 'text-green-600'
                  }`}
                >
                  {formatKRW(daily.remaining_budget)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">기간</p>
                <p className="font-medium">
                  {new Date(daily.period_start).toLocaleDateString('ko-KR', {
                    month: 'short',
                    day: 'numeric',
                  })}{' '}
                  ~{' '}
                  {new Date(daily.period_end).toLocaleDateString('ko-KR', {
                    month: 'short',
                    day: 'numeric',
                  })}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 5. Asset Distribution Widget ─────────────────────────────────────────────

const PIE_COLORS = ['#6366f1', '#06b6d4', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'];

function AssetDistributionWidget() {
  const { data: summary, isLoading, isError } = useDashboardSummary();

  const distribution: { label: string; amount: number }[] = (summary?.asset_distribution ?? []).map(
    (d: { label: string; amount: number }) => ({ label: d.label, amount: Number(d.amount) }),
  );
  const total = summary?.total_assets_krw ?? 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">자산 분포</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="mx-auto h-40 w-40 rounded-full" />
        ) : isError ? (
          <WidgetError />
        ) : distribution.length === 0 ? (
          <div className="flex h-40 items-center justify-center">
            <p className="text-sm text-muted-foreground">자산 데이터가 없습니다</p>
          </div>
        ) : (
          <div className="space-y-3">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={distribution}
                  dataKey="amount"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                >
                  {distribution.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip
                  formatter={(value: number, name: string) => [formatKRW(value), name]}
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="text-center text-xs text-muted-foreground">
              총 자산 <span className="font-bold text-foreground">{formatKRW(total)}</span>
            </div>
            <div className="space-y-1">
              {distribution.map((d, i) => (
                <div key={d.label} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-sm"
                      style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                    />
                    {d.label}
                  </span>
                  <span className="font-medium">{formatKRW(d.amount)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 6. Monthly Budget Widget ──────────────────────────────────────────────────

function MonthlyBudgetWidget() {
  const { data, isLoading, isError } = useBudgetAnalysis();

  const categories = data?.category_rates ?? [];
  const fixed = data?.fixed_deductions;

  const STATUS_COLORS: Record<string, string> = {
    normal: 'bg-primary',
    warning: 'bg-yellow-500',
    exceeded: 'bg-destructive',
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">월 예산 현황</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : isError ? (
          <WidgetError />
        ) : (
          <div className="space-y-3">
            {categories.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                카테고리 예산이 없습니다
              </p>
            ) : (
              categories.map((cat) => (
                <div key={cat.category_id}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1">
                      {cat.category_icon && <span>{cat.category_icon}</span>}
                      <span className="font-medium">{cat.category_name}</span>
                    </span>
                    <span className="text-muted-foreground">
                      {formatKRW(cat.spent)} / {formatKRW(cat.monthly_budget)}
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className={`h-full rounded-full transition-all ${
                        STATUS_COLORS[cat.status] ?? 'bg-primary'
                      }`}
                      style={{ width: `${Math.min(cat.usage_rate, 100)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
            {/* 고정비 / 할부 요약 */}
            {fixed && fixed.items.length > 0 && (
              <div className="mt-3 border-t pt-3">
                <p className="mb-2 text-xs font-medium text-muted-foreground">고정비 / 할부</p>
                {fixed.items.slice(0, 4).map((item, i) => (
                  <div key={i} className="flex items-center justify-between py-0.5 text-xs">
                    <span className="flex items-center gap-1">
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          item.is_paid ? 'bg-green-500' : 'bg-muted-foreground'
                        }`}
                      />
                      {item.name}
                    </span>
                    <span className="font-medium">{formatKRW(item.amount)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 7. Recent Transactions Widget ────────────────────────────────────────────

function RecentTransactionsWidget() {
  const { data, isLoading, isError } = useDashboardSummary();
  const entries = data?.recent_entries ?? [];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">최근 내역</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : isError ? (
          <WidgetError />
        ) : entries.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">최근 내역이 없습니다</p>
        ) : (
          <ul className="divide-y">
            {entries.map((entry) => (
              <li key={entry.id} className="flex items-center justify-between py-2.5">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-xs">
                    {ENTRY_TYPE_LABELS[entry.type] ?? entry.type}
                  </Badge>
                  <span className="max-w-[120px] truncate text-sm text-muted-foreground">
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
                  <p className="text-xs text-muted-foreground">
                    {formatDate(entry.transacted_at)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 8. Market Info Widget ─────────────────────────────────────────────────────

function MarketInfoWidget() {
  const { data: exchangeRate, isLoading, isError } = useExchangeRate();
  const { data: goldPrice } = useMarketPrice('KRX:GOLD');

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">시세 정보</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : isError ? (
          <WidgetError />
        ) : (
          <div className="space-y-3">
            {/* USD/KRW 환율 */}
            {exchangeRate && (
              <div className="flex items-center justify-between rounded-lg bg-muted/40 p-3">
                <div>
                  <p className="text-xs text-muted-foreground">{exchangeRate.pair}</p>
                  <p className="text-lg font-bold">
                    {exchangeRate.rate.toLocaleString('ko-KR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">원</span>
                  </p>
                </div>
                {exchangeRate.change != null && (
                  <div className="text-right">
                    <p
                      className={`flex items-center gap-0.5 text-sm font-medium ${
                        exchangeRate.change >= 0 ? 'text-destructive' : 'text-green-600'
                      }`}
                    >
                      {exchangeRate.change >= 0 ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {Math.abs(exchangeRate.change).toFixed(2)}
                    </p>
                    {exchangeRate.change_percent != null && (
                      <p className="text-xs text-muted-foreground">
                        {exchangeRate.change_percent >= 0 ? '+' : ''}
                        {exchangeRate.change_percent.toFixed(2)}%
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
            {/* 금 시세 */}
            {goldPrice && (
              <div className="flex items-center justify-between rounded-lg bg-muted/40 p-3">
                <div>
                  <p className="text-xs text-muted-foreground">{goldPrice.name ?? '금 (KRX)'}</p>
                  <p className="text-lg font-bold">
                    {goldPrice.price.toLocaleString('ko-KR')}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">원/g</span>
                  </p>
                </div>
                {goldPrice.change != null && (
                  <div className="text-right">
                    <p
                      className={`flex items-center gap-0.5 text-sm font-medium ${
                        goldPrice.change >= 0 ? 'text-green-600' : 'text-destructive'
                      }`}
                    >
                      {goldPrice.change >= 0 ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {Math.abs(goldPrice.change).toLocaleString('ko-KR')}
                    </p>
                    {goldPrice.change_percent != null && (
                      <p className="text-xs text-muted-foreground">
                        {goldPrice.change_percent >= 0 ? '+' : ''}
                        {goldPrice.change_percent.toFixed(2)}%
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 9. Payment Schedule Widget ───────────────────────────────────────────────

function PaymentScheduleWidget() {
  const { data: schedules, isLoading, isError } = useSchedules();

  const payments = (schedules ?? [])
    .filter((s) => s.type === 'expense' && s.is_active)
    .sort((a, b) => a.schedule_day - b.schedule_day);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Calendar className="h-4 w-4" />
          월 결제 일정
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : isError ? (
          <WidgetError />
        ) : payments.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            등록된 결제 일정이 없습니다
          </p>
        ) : (
          <ul className="divide-y">
            {payments.map((payment) => (
              <li key={payment.id} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                    {payment.schedule_day}
                  </span>
                  <span className="text-sm">{payment.name}</span>
                </div>
                <span className="text-sm font-semibold text-destructive">
                  {formatKRW(payment.amount)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 10. AI Insights Widget ────────────────────────────────────────────────────

const INSIGHT_SEVERITY_STYLES: Record<
  string,
  { border: string; bg: string; badge: string }
> = {
  info: {
    border: 'border-blue-200',
    bg: 'bg-blue-50/50 dark:bg-blue-950/20',
    badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  },
  warning: {
    border: 'border-yellow-200',
    bg: 'bg-yellow-50/50 dark:bg-yellow-950/20',
    badge: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  },
  success: {
    border: 'border-green-200',
    bg: 'bg-green-50/50 dark:bg-green-950/20',
    badge: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  },
};

const INSIGHT_TYPE_LABELS: Record<string, string> = {
  spending: '지출',
  budget: '예산',
  investment: '투자',
  saving: '저축',
  alert: '알림',
};

function AIInsightsWidget() {
  const { data, isLoading, isError } = useDashboardInsights();
  const insights = data?.insights ?? [];

  return (
    <Card className="col-span-full">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Lightbulb className="h-4 w-4" />
          AI 인사이트
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-24 w-full rounded-lg" />
            ))}
          </div>
        ) : isError ? (
          <WidgetError />
        ) : insights.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            인사이트를 생성하는 중입니다
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {insights.map((insight, i) => {
              const styles =
                INSIGHT_SEVERITY_STYLES[insight.severity] ?? INSIGHT_SEVERITY_STYLES.info;
              return (
                <div
                  key={i}
                  className={`rounded-lg border p-3 ${styles.border} ${styles.bg}`}
                >
                  <div className="mb-1 flex items-center gap-2">
                    <span
                      className={`rounded-full px-1.5 py-0.5 text-xs font-medium ${styles.badge}`}
                    >
                      {INSIGHT_TYPE_LABELS[insight.type] ?? insight.type}
                    </span>
                  </div>
                  <p className="text-sm font-semibold">{insight.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{insight.description}</p>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── main page component ───────────────────────────────────────────────────────

export function Component() {
  return (
    <div className="space-y-4 p-4 md:p-6">
      {/* 1행: 총 자산 (wide) + 목표 자산 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <TotalAssetsWidget />
        <GoalAssetWidget />
      </div>

      {/* 2행: 자산 추이 차트 (full width) */}
      <div className="grid grid-cols-1 gap-4">
        <AssetTimelineWidget />
      </div>

      {/* 3행: 오늘 예산 + 자산 분포 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <DailyBudgetWidget />
        <AssetDistributionWidget />
      </div>

      {/* 4행: 월 예산 + 최근 내역 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <MonthlyBudgetWidget />
        <RecentTransactionsWidget />
      </div>

      {/* 5행: 시세 정보 + 결제 일정 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <MarketInfoWidget />
        <PaymentScheduleWidget />
      </div>

      {/* 6행: AI 인사이트 (full width) */}
      <div className="grid grid-cols-1 gap-4">
        <AIInsightsWidget />
      </div>
    </div>
  );
}
