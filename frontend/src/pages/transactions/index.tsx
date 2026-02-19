import { useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { TransactionFilter } from '@/features/transaction/ui/TransactionFilter';
import { useFilteredTransactions } from '@/features/transaction/api';
import { TransactionList } from '@/features/assets/ui/TransactionList';
import { EditTransactionModal } from '@/features/assets/ui/EditTransactionModal';
import { useDeleteTransaction, useUpdateTransaction } from '@/features/assets/api';
import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import type { Transaction } from '@/shared/types';

interface Filters {
  asset_type?: string;
  tx_type?: string;
  start_date?: string;
  end_date?: string;
}

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState<Filters>({});
  const [editingTx, setEditingTx] = useState<Transaction | null>(null);
  const [confirmState, setConfirmState] = useState<{ action: () => void } | null>(null);
  const page = Number(searchParams.get('page')) || 1;
  const perPage = 20;

  const { data, isLoading, isError, refetch } = useFilteredTransactions({
    ...filters,
    page,
    per_page: perPage,
  });
  const deleteTx = useDeleteTransaction();
  const updateTx = useUpdateTransaction();

  const handleFilterChange = (newFilters: Filters) => {
    setFilters(newFilters);
    setSearchParams((prev) => { prev.delete('page'); return prev; });
  };

  const handleEdit = useCallback((tx: Transaction) => setEditingTx(tx), []);

  const handleDelete = useCallback(
    (id: string) => {
      setConfirmState({ action: () => deleteTx.mutate(id) });
    },
    [deleteTx],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Filter */}
      <TransactionFilter onFilterChange={handleFilterChange} />

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-10 w-full" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center p-12 text-center">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" aria-hidden="true" />
            <p className="text-muted-foreground mb-4">거래 내역을 불러올 수 없습니다.</p>
            <Button onClick={() => refetch()}>다시 시도</Button>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {data && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              총 <span className="font-semibold text-foreground">{data.total.toLocaleString()}</span>건
            </p>
          </div>

          <TransactionList
            transactions={data.data}
            total={data.total}
            page={page}
            perPage={perPage}
            onPageChange={(p) => setSearchParams((prev) => { prev.set('page', String(p)); return prev; })}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        </>
      )}

      {/* 수정 모달 */}
      {editingTx && (
        <EditTransactionModal
          transaction={editingTx}
          isOpen={!!editingTx}
          onClose={() => setEditingTx(null)}
          onSubmit={(data) => updateTx.mutate(data)}
          isLoading={updateTx.isPending}
        />
      )}

      {/* 삭제 확인 */}
      <ConfirmDialog
        open={confirmState !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmState(null);
        }}
        title="삭제하시겠습니까?"
        description="이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={() => confirmState?.action()}
        variant="destructive"
      />
    </div>
  );
}
