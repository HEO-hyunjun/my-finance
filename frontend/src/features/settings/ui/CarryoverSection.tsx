import { useState, useEffect } from 'react';
import { useCategories } from '@/features/budget/api';
import { useAssets } from '@/features/assets/api';
import { useCarryoverSettings, useUpsertCarryoverSetting } from '../api/carryover';
import type { CarryoverType, CarryoverSettingRequest, Asset } from '@/shared/types';
import { CARRYOVER_TYPE_LABELS } from '@/shared/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';

const CARRYOVER_TYPES: CarryoverType[] = ['expire', 'next_month', 'savings', 'transfer', 'deposit'];

const TRANSFER_TARGET_TYPES = new Set(['cash_krw', 'cash_usd', 'parking']);
const SOURCE_ASSET_TYPES = new Set(['cash_krw', 'cash_usd', 'parking', 'bank_account', 'securities']);

interface CategoryRowProps {
  categoryId: string;
  categoryName: string;
  currentType: CarryoverType;
  currentLimit?: number;
  currentSourceAssetId?: string;
  currentAssetId?: string;
  currentAnnualRate?: number;
  assets: Asset[];
  onSave: (data: CarryoverSettingRequest) => void;
  isSaving: boolean;
}

function CategoryRow({
  categoryId,
  categoryName,
  currentType,
  currentLimit,
  currentSourceAssetId,
  currentAssetId,
  currentAnnualRate,
  assets,
  onSave,
  isSaving,
}: CategoryRowProps) {
  const [type, setType] = useState<CarryoverType>(currentType);
  const [limit, setLimit] = useState(currentLimit?.toString() ?? '');
  const [sourceAssetId, setSourceAssetId] = useState(currentSourceAssetId ?? '');
  const [assetId, setAssetId] = useState(currentAssetId ?? '');
  const [annualRate, setAnnualRate] = useState(currentAnnualRate?.toString() ?? '');

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setType(currentType);
    setLimit(currentLimit?.toString() ?? '');
    setSourceAssetId(currentSourceAssetId ?? '');
    setAssetId(currentAssetId ?? '');
    setAnnualRate(currentAnnualRate?.toString() ?? '');
  }, [currentType, currentLimit, currentSourceAssetId, currentAssetId, currentAnnualRate]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const sourceAssets = assets.filter((a) => SOURCE_ASSET_TYPES.has(a.asset_type));

  const filteredAssets = assets.filter((a) => {
    if (type === 'savings') return a.asset_type === 'savings';
    if (type === 'deposit') return a.asset_type === 'deposit';
    if (type === 'transfer') return TRANSFER_TARGET_TYPES.has(a.asset_type);
    return false;
  });

  const handleAssetChange = (id: string) => {
    setAssetId(id);
    if (type === 'deposit' && id) {
      const selected = assets.find((a) => a.id === id);
      if (selected?.interest_rate != null) {
        setAnnualRate(selected.interest_rate.toString());
      }
    }
  };

  const needsAssetTransfer = type === 'savings' || type === 'deposit' || type === 'transfer';
  const hasChanges =
    type !== currentType ||
    (type === 'next_month' && limit !== (currentLimit?.toString() ?? '')) ||
    (needsAssetTransfer && sourceAssetId !== (currentSourceAssetId ?? '')) ||
    (needsAssetTransfer && assetId !== (currentAssetId ?? '')) ||
    (type === 'deposit' && annualRate !== (currentAnnualRate?.toString() ?? ''));

  const handleSave = () => {
    const data: CarryoverSettingRequest = {
      category_id: categoryId,
      carryover_type: type,
    };
    if (type === 'next_month' && limit) {
      data.carryover_limit = Number(limit);
    }
    if ((type === 'savings' || type === 'deposit' || type === 'transfer') && assetId) {
      if (sourceAssetId) {
        data.source_asset_id = sourceAssetId;
      }
      data.target_asset_id = assetId;
      const selected = assets.find((a) => a.id === assetId);
      if (selected) {
        data.target_savings_name = selected.name;
      }
    }
    if (type === 'deposit' && annualRate) {
      data.target_annual_rate = Number(annualRate);
    }
    onSave(data);
  };

  return (
    <div className="rounded-md border border-border px-4 py-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{categoryName}</span>
        <div className="flex items-center gap-2">
          <select
            value={type}
            onChange={(e) => setType(e.target.value as CarryoverType)}
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          >
            {CARRYOVER_TYPES.map((t) => (
              <option key={t} value={t}>
                {CARRYOVER_TYPE_LABELS[t]}
              </option>
            ))}
          </select>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
          >
            {isSaving ? '저장...' : '저장'}
          </Button>
        </div>
      </div>

      {type === 'next_month' && (
        <div>
          <Label className="text-xs">이월 한도 (원)</Label>
          <Input
            type="number"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            placeholder="한도 없음"
            min="0"
          />
        </div>
      )}

      {(type === 'savings' || type === 'deposit' || type === 'transfer') && (
        <>
        <div>
          <Label className="text-xs">출처 자산 (어디서)</Label>
          {sourceAssets.length > 0 ? (
            <select
              value={sourceAssetId}
              onChange={(e) => setSourceAssetId(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              <option value="">선택하세요</option>
              {sourceAssets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}{a.bank_name ? ` (${a.bank_name})` : ''}
                </option>
              ))}
            </select>
          ) : (
            <p className="text-xs text-muted-foreground py-1">
              등록된 출금 가능 자산이 없습니다.
            </p>
          )}
        </div>
        <div>
          <Label className="text-xs">
            대상 {type === 'savings' ? '적금' : type === 'deposit' ? '예금' : '자산'} (어디로)
          </Label>
          {filteredAssets.length > 0 ? (
            <select
              value={assetId}
              onChange={(e) => handleAssetChange(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              <option value="">선택하세요</option>
              {filteredAssets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}{a.bank_name ? ` (${a.bank_name})` : ''}
                </option>
              ))}
            </select>
          ) : (
            <p className="text-xs text-muted-foreground py-1">
              등록된 {type === 'savings' ? '적금' : type === 'deposit' ? '예금' : '현금성'} 자산이 없습니다. 자산 관리에서 먼저 추가해주세요.
            </p>
          )}
        </div>
        </>
      )}

      {type === 'deposit' && (
        <div>
          <Label className="text-xs">연 이율 (%)</Label>
          <Input
            type="number"
            value={annualRate}
            onChange={(e) => setAnnualRate(e.target.value)}
            placeholder="예: 3.5"
            step="0.1"
            min="0"
          />
        </div>
      )}
    </div>
  );
}

export function CarryoverSection() {
  const { data: categories, isLoading: categoriesLoading } = useCategories();
  const { data: settings, isLoading: settingsLoading } = useCarryoverSettings();
  const { data: assets = [], isLoading: assetsLoading } = useAssets();
  const upsertSetting = useUpsertCarryoverSetting();

  const isLoading = categoriesLoading || settingsLoading || assetsLoading;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </CardContent>
      </Card>
    );
  }

  const activeCategories = categories?.filter((c) => c.is_active) ?? [];
  const settingsMap = new Map(settings?.map((s) => [s.category_id, s]) ?? []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>예산 이월 정책</CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          카테고리별 남은 예산의 처리 방식을 설정합니다.
        </p>
      </CardHeader>
      <CardContent>
        {activeCategories.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            활성화된 예산 카테고리가 없습니다.
          </p>
        ) : (
          <div className="space-y-3">
            {activeCategories.map((category) => {
              const setting = settingsMap.get(category.id);
              return (
                <CategoryRow
                  key={category.id}
                  categoryId={category.id}
                  categoryName={category.name}
                  currentType={setting?.carryover_type ?? 'expire'}
                  currentLimit={setting?.carryover_limit}
                  currentSourceAssetId={setting?.source_asset_id}
                  currentAssetId={setting?.target_asset_id}
                  currentAnnualRate={setting?.target_annual_rate}
                  assets={assets}
                  onSave={(data) => upsertSetting.mutate(data)}
                  isSaving={upsertSetting.isPending}
                />
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
