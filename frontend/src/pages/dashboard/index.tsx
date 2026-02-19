import { useDashboardSummary } from '@/features/dashboard/api';
import { useAppSettings } from '@/features/settings/api/settings-api';
import { TotalAssetWidget } from '@/features/dashboard/ui/TotalAssetWidget';
import { AssetDistChart } from '@/features/dashboard/ui/AssetDistChart';
import { BudgetStatusWidget } from '@/features/dashboard/ui/BudgetStatusWidget';
import { RecentTxWidget } from '@/features/dashboard/ui/RecentTxWidget';
import { MarketInfoWidget } from '@/features/dashboard/ui/MarketInfoWidget';
import { PaymentScheduleWidget } from '@/features/dashboard/ui/PaymentScheduleWidget';
import { MaturityAlertWidget } from '@/features/dashboard/ui/MaturityAlertWidget';
import { GoalTrackerWidget } from '@/features/dashboard/ui/GoalTrackerWidget';
import { AssetTimelineWidget } from '@/features/dashboard/ui/AssetTimelineWidget';
import { DailyBudgetWidget } from '@/features/dashboard/ui/DailyBudgetWidget';
import { AIInsightWidget } from '@/features/dashboard/ui/AIInsightWidget';
import { Card, CardContent } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { Button } from '@/shared/ui/button';
import { AlertCircle } from 'lucide-react';

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-28 w-full rounded-xl" />
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-72 rounded-xl" />
      </div>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
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

export function Component() {
  const { data, isLoading, isError, refetch } = useDashboardSummary();
  const { data: appSettings } = useAppSettings();

  return (
    <div className="space-y-6 p-4 md:p-6">
      {isLoading && <DashboardSkeleton />}
      {isError && <DashboardError onRetry={() => refetch()} />}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <TotalAssetWidget summary={data.asset_summary} />
            <GoalTrackerWidget />
          </div>

          <AIInsightWidget />
          <AssetTimelineWidget assetTypeColors={appSettings?.asset_type_colors} />

          <DailyBudgetWidget budget={data.budget_summary} />
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <AssetDistChart breakdown={data.asset_summary.breakdown} assetTypeColors={appSettings?.asset_type_colors} />
            <BudgetStatusWidget budget={data.budget_summary} />
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            <RecentTxWidget transactions={data.recent_transactions} />
            <div className="space-y-6">
              <MarketInfoWidget market={data.market_info} />
              <PaymentScheduleWidget payments={data.upcoming_payments} />
            </div>
            {data.maturity_alerts.length > 0 && (
              <MaturityAlertWidget alerts={data.maturity_alerts} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
