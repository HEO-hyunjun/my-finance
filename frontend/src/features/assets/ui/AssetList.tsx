import { memo } from 'react';
import type { AssetHolding } from '@/shared/types';
import { AssetCard } from './AssetCard';

interface Props {
  holdings: AssetHolding[];
  onAssetClick?: (id: string) => void;
  onDelete?: (id: string) => void;
  deletingId?: string | null;
}

function AssetListInner({ holdings, onAssetClick, onDelete, deletingId }: Props) {
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
          onDelete={onDelete}
          isDeleting={deletingId === holding.id}
        />
      ))}
    </div>
  );
}

export const AssetList = memo(AssetListInner);
