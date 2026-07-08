import { useState } from 'react';
import { Settings } from 'lucide-react';

import { useAppSettings } from '@/features/settings/api/settings-api';
import { Button } from '@/shared/ui/button';

import { TotalAssetsWidget } from '@/features/dashboard/ui/TotalAssetsWidget';
import { GoalAssetWidget } from '@/features/dashboard/ui/GoalAssetWidget';
import { AssetTimelineWidget } from '@/features/dashboard/ui/AssetTimelineWidget';
import { DailyBudgetWidget } from '@/features/dashboard/ui/DailyBudgetWidget';
import { AssetDistributionWidget } from '@/features/dashboard/ui/AssetDistributionWidget';
import { MonthlyBudgetWidget } from '@/features/dashboard/ui/MonthlyBudgetWidget';
import { RecentTransactionsWidget } from '@/features/dashboard/ui/RecentTransactionsWidget';
import { MarketInfoWidget } from '@/features/dashboard/ui/MarketInfoWidget';
import { PaymentScheduleWidget } from '@/features/dashboard/ui/PaymentScheduleWidget';
import { AIInsightsWidget } from '@/features/dashboard/ui/AIInsightsWidget';
import { DashboardSettingsDialog } from '@/features/dashboard/ui/DashboardSettingsDialog';

// ─── main page component ───────────────────────────────────────────────────────

export function Component() {
  const [settingsTab, setSettingsTab] = useState<string | null>(null);
  const { data: settings } = useAppSettings();

  const w = settings?.dashboard_widgets ?? {};
  const show = (key: string) => w[key] !== false;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">대시보드</h1>
        <Button variant="ghost" size="sm" onClick={() => setSettingsTab('widgets')}>
          <Settings className="h-4 w-4" />
        </Button>
      </div>

      {/* 1행: 총 자산 + 목표 자산 */}
      {(show('totalAssets') || show('goalAsset')) && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {show('totalAssets') && <TotalAssetsWidget />}
          {show('goalAsset') && <GoalAssetWidget onOpenSettings={() => setSettingsTab('goal')} />}
        </div>
      )}

      {/* 2행: 자산 추이 차트 */}
      {show('assetTimeline') && (
        <div className="grid grid-cols-1 gap-4">
          <AssetTimelineWidget />
        </div>
      )}

      {/* 3행: 오늘 예산 + 자산 분포 */}
      {(show('dailyBudget') || show('assetDistribution')) && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {show('dailyBudget') && <DailyBudgetWidget />}
          {show('assetDistribution') && <AssetDistributionWidget />}
        </div>
      )}

      {/* 4행: 월 예산 + 최근 내역 */}
      {(show('monthlyBudget') || show('recentTransactions')) && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {show('monthlyBudget') && <MonthlyBudgetWidget />}
          {show('recentTransactions') && <RecentTransactionsWidget />}
        </div>
      )}

      {/* 5행: 시세 정보 + 결제 일정 */}
      {(show('marketInfo') || show('paymentSchedule')) && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {show('marketInfo') && <MarketInfoWidget />}
          {show('paymentSchedule') && <PaymentScheduleWidget />}
        </div>
      )}

      {/* 6행: AI 인사이트 */}
      {show('aiInsights') && (
        <div className="grid grid-cols-1 gap-4">
          <AIInsightsWidget />
        </div>
      )}

      {/* 설정 모달 */}
      <DashboardSettingsDialog
        isOpen={settingsTab !== null}
        onClose={() => setSettingsTab(null)}
        defaultTab={settingsTab ?? 'widgets'}
      />
    </div>
  );
}
