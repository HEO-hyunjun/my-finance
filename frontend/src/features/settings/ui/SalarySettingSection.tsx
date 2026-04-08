import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';
import type { Asset } from '@/shared/types/common';
import { formatKRW } from '@/shared/lib/format';

interface Props {
  currentDay: number;
  currentAssetId?: string;
  currentAmount?: number;
  assets: Asset[];
  onUpdate: (data: {
    salary_day?: number;
    salary_asset_id?: string | null;
    salary_amount?: number | null;
  }) => void;
  isLoading: boolean;
}

export function SalarySettingSection({
  currentDay,
  currentAssetId,
  currentAmount,
  assets,
  onUpdate,
  isLoading,
}: Props) {
  const [day, setDay] = useState(currentDay);
  const [assetId, setAssetId] = useState(currentAssetId || '');
  const [amount, setAmount] = useState(currentAmount?.toString() || '');

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setDay(currentDay);
    setAssetId(currentAssetId || '');
    setAmount(currentAmount?.toString() || '');
  }, [currentDay, currentAssetId, currentAmount]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const hasChanges =
    day !== currentDay ||
    assetId !== (currentAssetId || '') ||
    amount !== (currentAmount?.toString() || '');

  const handleSave = () => {
    const update: Parameters<typeof onUpdate>[0] = {};
    if (day !== currentDay) update.salary_day = day;
    if (assetId !== (currentAssetId || ''))
      update.salary_asset_id = assetId || null;
    if (amount !== (currentAmount?.toString() || ''))
      update.salary_amount = amount ? Number(amount) : null;
    onUpdate(update);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">급여 설정</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">
          급여일 기준으로 예산 기간이 계산되며, 수입 추가 시 급여 유형을
          선택하면 아래 설정값이 자동으로 적용됩니다.
        </p>

        <div className="space-y-3">
          {/* 급여일 */}
          <div className="flex items-center gap-3">
            <Label className="w-20 shrink-0 text-sm">급여일</Label>
            <select
              value={day}
              onChange={(e) => setDay(Number(e.target.value))}
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
            >
              {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
                <option key={d} value={d}>
                  매월 {d}일
                </option>
              ))}
            </select>
          </div>

          {/* 입금 계좌 */}
          <div className="flex items-center gap-3">
            <Label className="w-20 shrink-0 text-sm">입금 계좌</Label>
            <select
              value={assetId}
              onChange={(e) => setAssetId(e.target.value)}
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
            >
              <option value="">선택 안함</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* 급여 금액 */}
          <div className="flex items-center gap-3">
            <Label className="w-20 shrink-0 text-sm">급여 금액</Label>
            <Input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              min={0}
              className="flex-1"
            />
          </div>
        </div>

        {amount && Number(amount) > 0 && (
          <p className="text-xs text-primary">
            매월 {day}일에 {formatKRW(Number(amount))}원 급여
          </p>
        )}

        {day !== 1 && (
          <p className="text-xs text-muted-foreground">
            예산 기간: 매월 {day}일 ~ 다음 달 {day - 1}일
          </p>
        )}

        <Button
          onClick={handleSave}
          disabled={isLoading || !hasChanges}
          className="w-full"
        >
          저장
        </Button>
      </CardContent>
    </Card>
  );
}
