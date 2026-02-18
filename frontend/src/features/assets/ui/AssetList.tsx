import { memo } from 'react';
import type { AssetHolding } from '@/shared/types';
import { AssetCard } from './AssetCard';

interface Props {
  holdings: AssetHolding[];
  onAssetClick?: (id: string) => void;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  onRefresh?: (symbol: string, assetType: string) => void;
  deletingId?: string | null;
  refreshingSymbol?: string | null;
}

function AssetListInner({ holdings, onAssetClick, onEdit, onDelete, onRefresh, deletingId, refreshingSymbol }: Props) {
  if (holdings.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center">
        <p className="text-muted-foreground">등록된 자산이 없습니다.</p>
        <p className="mt-1 text-sm text-muted-foreground">자산을 추가하여 포트폴리오를 관리하세요.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {holdings.map((holding) => (
        <AssetCard
          key={holding.id}
          holding={holding}
          onClick={() => onAssetClick?.(holding.id)}
          onEdit={onEdit}
          onDelete={onDelete}
          onRefresh={onRefresh}
          isDeleting={deletingId === holding.id}
          isRefreshing={refreshingSymbol === holding.symbol}
        />
      ))}
    </div>
  );
}

export const AssetList = memo(AssetListInner);
