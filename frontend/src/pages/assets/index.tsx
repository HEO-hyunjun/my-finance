import { useState, useCallback } from 'react';
import { Plus } from 'lucide-react';
import {
  useAssetSummary,
  useTransactions,
  useCreateAsset,
  useDeleteAsset,
  useDeleteTransaction,
} from '@/features/assets/api';
import { AssetSummaryCard } from '@/features/assets/ui/AssetSummaryCard';
import { AssetList } from '@/features/assets/ui/AssetList';
import { TransactionList } from '@/features/assets/ui/TransactionList';
import { AddAssetModal } from '@/features/assets/ui/AddAssetModal';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';

export function Component() {
  const [showAddAsset, setShowAddAsset] = useState(false);
  const [txPage, setTxPage] = useState(1);

  const { data: summary, isLoading: summaryLoading } = useAssetSummary();
  const { data: txData } = useTransactions({ page: txPage, per_page: 10 });

  const createAsset = useCreateAsset();
  const deleteAsset = useDeleteAsset();
  const deleteTx = useDeleteTransaction();

  const [deletingAssetId, setDeletingAssetId] = useState<string | null>(null);
  const handleDeleteAsset = useCallback((id: string) => {
    setDeletingAssetId(id);
    deleteAsset.mutate(id, {
      onSettled: () => setDeletingAssetId(null),
    });
  }, [deleteAsset]);
  const handleDeleteTx = useCallback((id: string) => deleteTx.mutate(id), [deleteTx]);
  const handleOpenAddAsset = useCallback(() => setShowAddAsset(true), []);
  const handleCloseAddAsset = useCallback(() => setShowAddAsset(false), []);
  const handleSubmitAsset = useCallback(
    (data: Parameters<typeof createAsset.mutate>[0]) => {
      createAsset.mutate(data, { onSuccess: () => setShowAddAsset(false) });
    },
    [createAsset],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      {/* Summary */}
      {summaryLoading ? (
        <Skeleton className="h-32 w-full rounded-xl" />
      ) : summary ? (
        <AssetSummaryCard summary={summary} />
      ) : null}

      {/* Asset List */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">보유 자산</h2>
          <Button onClick={handleOpenAddAsset} size="sm">
            <Plus className="mr-1.5 h-4 w-4" />
            자산 추가
          </Button>
        </div>
        <AssetList
          holdings={summary?.holdings || []}
          onDelete={handleDeleteAsset}
          deletingId={deletingAssetId}
        />
      </div>

      {/* Transaction List */}
      <div>
        <h2 className="mb-3 text-lg font-semibold">거래 내역</h2>
        <TransactionList
          transactions={txData?.data || []}
          total={txData?.total || 0}
          page={txPage}
          perPage={10}
          onPageChange={setTxPage}
          onDelete={handleDeleteTx}
        />
      </div>

      {/* Modals */}
      <AddAssetModal
        isOpen={showAddAsset}
        onClose={handleCloseAddAsset}
        onSubmit={handleSubmitAsset}
        isLoading={createAsset.isPending}
      />
    </div>
  );
}
