import { useAppSettings, useUpdateAppSettings } from '../api/settings-api';
import { ASSET_TYPE_LABELS } from '@/shared/types';
import type { AssetType } from '@/shared/types';
import { DEFAULT_ASSET_TYPE_COLORS } from '@/shared/lib/asset-colors';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';

const ASSET_TYPES: AssetType[] = [
  'stock_kr', 'stock_us', 'gold', 'cash_krw', 'cash_usd',
  'deposit', 'savings', 'parking',
];

export function AssetTypeColorSection() {
  const { data: settings, isLoading } = useAppSettings();
  const update = useUpdateAppSettings();

  if (isLoading) return <Skeleton className="h-48 w-full" />;

  const currentColors: Record<string, string> = {
    ...DEFAULT_ASSET_TYPE_COLORS,
    ...(settings?.asset_type_colors ?? {}),
  };

  const handleColorChange = (assetType: string, color: string) => {
    const merged = { ...currentColors, [assetType]: color };
    update.mutate({ asset_type_colors: merged });
  };

  const handleReset = () => {
    update.mutate({ asset_type_colors: { ...DEFAULT_ASSET_TYPE_COLORS } });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>자산 유형별 차트 색상</CardTitle>
          <Button variant="ghost" size="sm" onClick={handleReset} disabled={update.isPending}>
            초기화
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {ASSET_TYPES.map((type) => (
            <label
              key={type}
              className="flex cursor-pointer items-center gap-2 rounded-lg border border-border p-2.5 transition-colors hover:bg-accent"
            >
              <input
                type="color"
                value={currentColors[type] ?? DEFAULT_ASSET_TYPE_COLORS[type]}
                onChange={(e) => handleColorChange(type, e.target.value)}
                className="h-7 w-7 cursor-pointer rounded border-0"
              />
              <span className="text-sm font-medium">{ASSET_TYPE_LABELS[type]}</span>
            </label>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
