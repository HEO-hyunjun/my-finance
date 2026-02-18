import { memo, useMemo } from 'react';
import type { AutoTransfer } from '@/shared/types';
import { formatKRW } from '@/shared/lib/format';
import { Button } from '@/shared/ui/button';
import { cn } from '@/shared/lib/utils';

interface Props {
  autoTransfers: AutoTransfer[];
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
}

function AutoTransferListInner({ autoTransfers, onToggle, onDelete }: Props) {
  const totalActive = useMemo(
    () => autoTransfers.filter((at) => at.is_active).reduce((sum, at) => sum + at.amount, 0),
    [autoTransfers],
  );

  if (autoTransfers.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground">
        등록된 자동이체가 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {autoTransfers.map((at) => (
        <div
          key={at.id}
          className={cn(
            'flex items-center justify-between rounded-lg border bg-card p-3',
            at.is_active ? 'border-border' : 'border-border opacity-50',
          )}
        >
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">{at.name}</span>
              <span className="text-sm font-semibold">{formatKRW(at.amount)}</span>
            </div>
            <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
              <span>{at.source_asset_name || '출금계좌'}</span>
              <span>→</span>
              <span>{at.target_asset_name || '입금계좌'}</span>
              <span className="ml-1">매월 {at.transfer_day}일</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={() => onToggle(at.id)}
              variant={at.is_active ? 'default' : 'secondary'}
              size="sm"
              className="h-auto rounded-full px-3 py-1 text-xs"
            >
              {at.is_active ? 'ON' : 'OFF'}
            </Button>
            <Button
              onClick={() => onDelete(at.id)}
              variant="ghost"
              size="sm"
              className="h-auto px-2 py-1 text-xs text-destructive hover:text-destructive"
            >
              삭제
            </Button>
          </div>
        </div>
      ))}

      <div className="rounded-lg bg-muted p-3 text-right text-sm">
        <span className="text-muted-foreground">월 합계: </span>
        <span className="font-semibold">{formatKRW(totalActive)}</span>
      </div>
    </div>
  );
}

export const AutoTransferList = memo(AutoTransferListInner);
