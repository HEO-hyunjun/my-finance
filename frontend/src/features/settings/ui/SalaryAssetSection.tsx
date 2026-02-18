import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';
import type { Asset } from '@/shared/types';

interface Props {
  currentAssetId?: string;
  assets: Asset[];
  onUpdate: (assetId: string | null) => void;
  isLoading: boolean;
}

export function SalaryAssetSection({ currentAssetId, assets, onUpdate, isLoading }: Props) {
  const [assetId, setAssetId] = useState(currentAssetId || '');

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">급여 입금 계좌</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">
          급여가 입금되는 자산을 선택하면 급여일에 자동으로 해당 계좌에 입금 처리됩니다.
        </p>
        <div className="flex items-center gap-3">
          <Label className="shrink-0 text-sm">입금 계좌</Label>
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
          <Button
            onClick={() => onUpdate(assetId || null)}
            disabled={isLoading || assetId === (currentAssetId || '')}
          >
            저장
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
