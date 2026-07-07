import { useState, useEffect } from 'react';
import { useAppSettings, useUpdateAppSettings } from '@/features/settings/api/settings-api';
import { useGoal, useSetGoal } from '@/features/portfolio/api';
import { DEFAULT_ASSET_TYPE_COLORS } from '@/shared/lib/asset-colors';
import { ASSET_TYPE_LABELS } from '@/shared/types/common';
import type { AssetType } from '@/shared/types/common';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/ui/tabs';
import { Button } from '@/shared/ui/button';

const WIDGET_CONFIG: { key: string; label: string }[] = [
  { key: 'totalAssets', label: '총 자산' },
  { key: 'goalAsset', label: '목표 자산' },
  { key: 'assetTimeline', label: '자산 추이' },
  { key: 'dailyBudget', label: '오늘 예산' },
  { key: 'assetDistribution', label: '자산 분포' },
  { key: 'monthlyBudget', label: '월 예산 현황' },
  { key: 'recentTransactions', label: '최근 내역' },
  { key: 'marketInfo', label: '시세 정보' },
  { key: 'paymentSchedule', label: '결제 일정' },
  { key: 'aiInsights', label: 'AI 인사이트' },
];

const COLOR_KEYS: AssetType[] = [
  'stock_kr', 'stock_us', 'gold', 'cash_krw', 'cash_usd',
  'deposit', 'savings', 'parking',
];

interface DashboardSettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  defaultTab?: string;
}

export function DashboardSettingsDialog({ isOpen, onClose, defaultTab = 'widgets' }: DashboardSettingsDialogProps) {
  const { data: settings } = useAppSettings();
  const updateSettings = useUpdateAppSettings();
  const { data: goal } = useGoal();
  const setGoal = useSetGoal();

  // 목표 자산
  const [targetAmount, setTargetAmount] = useState('');
  const [targetDate, setTargetDate] = useState('');

  // 위젯 on/off
  const [widgets, setWidgets] = useState<Record<string, boolean>>({});

  // 색상
  const [colors, setColors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (isOpen) {
      setTargetAmount(goal?.target_amount ? String(goal.target_amount) : '');
      setTargetDate(goal?.target_date ?? '');

      const saved = settings?.dashboard_widgets ?? {};
      const initial: Record<string, boolean> = {};
      WIDGET_CONFIG.forEach((w) => { initial[w.key] = saved[w.key] !== false; });
      setWidgets(initial);

      setColors({ ...DEFAULT_ASSET_TYPE_COLORS, ...(settings?.asset_type_colors ?? {}) });
    }
  }, [isOpen, goal, settings]);

  const handleSaveGoal = () => {
    const amount = Number(targetAmount);
    if (!isNaN(amount) && amount > 0) {
      setGoal.mutate({ target_amount: amount, target_date: targetDate || null });
    }
  };

  const handleColorChange = (key: string, color: string) => {
    const updated = { ...colors, [key]: color };
    setColors(updated);
    updateSettings.mutate({ asset_type_colors: updated });
  };

  const handleWidgetToggle = (key: string) => {
    const updated = { ...widgets, [key]: !widgets[key] };
    setWidgets(updated);
    updateSettings.mutate({ dashboard_widgets: updated });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>대시보드 설정</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue={defaultTab} className="mt-2">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="widgets">위젯</TabsTrigger>
            <TabsTrigger value="goal">목표자산</TabsTrigger>
            <TabsTrigger value="colors">차트색상</TabsTrigger>
          </TabsList>

          {/* 위젯 on/off */}
          <TabsContent value="widgets" className="space-y-1 pt-2">
            <p className="text-xs text-muted-foreground mb-2">표시할 위젯을 선택하세요.</p>
            {WIDGET_CONFIG.map((w) => (
              <label
                key={w.key}
                className="flex items-center justify-between rounded-lg border px-3 py-2.5 cursor-pointer hover:bg-accent transition-colors"
              >
                <span className="text-sm">{w.label}</span>
                <input
                  type="checkbox"
                  checked={widgets[w.key] !== false}
                  onChange={() => handleWidgetToggle(w.key)}
                  className="h-4 w-4 rounded"
                />
              </label>
            ))}
          </TabsContent>

          {/* 목표 자산 */}
          <TabsContent value="goal" className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label>목표 금액 (원)</Label>
              <Input
                type="number"
                min="0"
                value={targetAmount}
                onChange={(e) => setTargetAmount(e.target.value)}
                placeholder="예: 100000000"
              />
            </div>
            <div className="space-y-1.5">
              <Label>목표 날짜 (선택)</Label>
              <Input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
              />
            </div>
            <Button
              onClick={handleSaveGoal}
              disabled={setGoal.isPending || !targetAmount}
              className="w-full"
            >
              {setGoal.isPending ? '저장 중...' : '목표 저장'}
            </Button>
            {goal && (
              <p className="text-xs text-muted-foreground text-center">
                현재 달성률: {goal.achievement_rate.toFixed(1)}%
              </p>
            )}
          </TabsContent>

          {/* 차트 색상 */}
          <TabsContent value="colors" className="space-y-1 pt-2">
            <p className="text-xs text-muted-foreground mb-2">자산 유형별 차트 색상을 설정하세요.</p>
            <div className="grid grid-cols-2 gap-2">
              {COLOR_KEYS.map((key) => (
                <label
                  key={key}
                  className="flex items-center gap-2 rounded-lg border p-2.5 cursor-pointer hover:bg-accent transition-colors"
                >
                  <input
                    type="color"
                    value={colors[key] ?? DEFAULT_ASSET_TYPE_COLORS[key] ?? '#888888'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="h-7 w-7 cursor-pointer rounded border-0 shrink-0"
                  />
                  <span className="text-sm">{ASSET_TYPE_LABELS[key] ?? key}</span>
                </label>
              ))}
            </div>
            <button
              onClick={() => {
                setColors({ ...DEFAULT_ASSET_TYPE_COLORS });
                updateSettings.mutate({ asset_type_colors: { ...DEFAULT_ASSET_TYPE_COLORS } });
              }}
              className="mt-2 w-full text-center text-xs text-muted-foreground hover:text-foreground transition-colors py-1"
            >
              기본 색상으로 초기화
            </button>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
