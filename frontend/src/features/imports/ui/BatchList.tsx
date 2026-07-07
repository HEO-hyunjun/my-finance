import { useState } from 'react';
import { Trash2, ChevronRight } from 'lucide-react';
import { useImports, useDeleteImport } from '@/features/imports/api';
import { STATUS_META, formatDate } from '@/features/imports/lib/status';
import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';

interface Props {
  onSelect: (batchId: string) => void;
}

export function BatchList({ onSelect }: Props) {
  const { data: batches = [], isLoading } = useImports();
  const deleteImport = useDeleteImport();
  const [deleteId, setDeleteId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
      </div>
    );
  }

  if (batches.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          가져온 파일이 없습니다. 위에서 파일을 업로드해보세요.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {batches.map((b) => {
        const meta = STATUS_META[b.status];
        const openable = b.status === 'review' || b.status === 'committed';
        return (
          <div
            key={b.id}
            className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3"
          >
            <button
              type="button"
              disabled={!openable}
              onClick={() => openable && onSelect(b.id)}
              className="flex min-w-0 flex-1 items-center gap-3 text-left disabled:cursor-default"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{b.filename}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {formatDate(b.created_at)}
                  {b.row_count != null ? ` · ${b.row_count}건` : ''}
                  {b.source_bank ? ` · ${b.source_bank}` : ''}
                </p>
                {b.status === 'failed' && b.error && (
                  <p className="truncate text-xs text-destructive">{b.error}</p>
                )}
              </div>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${meta.className}`}>
                {meta.label}
              </span>
              {openable && <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />}
            </button>
            {b.status !== 'committed' && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 shrink-0 p-0 text-destructive hover:text-destructive"
                onClick={() => setDeleteId(b.id)}
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span className="sr-only">삭제</span>
              </Button>
            )}
          </div>
        );
      })}

      <ConfirmDialog
        open={deleteId !== null}
        onOpenChange={(open) => { if (!open) setDeleteId(null); }}
        title="가져오기 배치를 삭제하시겠습니까?"
        description="스테이징된 내역이 삭제됩니다. 이미 커밋된 거래에는 영향이 없습니다."
        confirmLabel="삭제"
        variant="destructive"
        onConfirm={() => {
          if (deleteId) deleteImport.mutate(deleteId);
          setDeleteId(null);
        }}
      />
    </div>
  );
}
