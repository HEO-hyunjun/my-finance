import { useState, useCallback, useMemo } from 'react';
import { Plus, RefreshCw } from 'lucide-react';
import {
  useAssets,
  useAssetSummary,
  useTransactions,
  useCreateAsset,
  useUpdateAsset,
  useDeleteAsset,
  useDeleteTransaction,
  useRefreshPrice,
  useRefreshAll,
  useAutoTransfers,
  useCreateAutoTransfer,
  useToggleAutoTransfer,
  useDeleteAutoTransfer,
} from '@/features/assets/api';
import { AssetSummaryCard } from '@/features/assets/ui/AssetSummaryCard';
import { AssetList } from '@/features/assets/ui/AssetList';
import { TransactionList } from '@/features/assets/ui/TransactionList';
import { AddAssetModal } from '@/features/assets/ui/AddAssetModal';
import { EditAssetModal } from '@/features/assets/ui/EditAssetModal';
import { AutoTransferList } from '@/features/assets/ui/AutoTransferList';
import { AddAutoTransferModal } from '@/features/assets/ui/AddAutoTransferModal';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';
import type { AssetUpdateRequest } from '@/shared/types';

export function Component() {
  const [showAddAsset, setShowAddAsset] = useState(false);
  const [editingAssetId, setEditingAssetId] = useState<string | null>(null);
  const [txPage, setTxPage] = useState(1);
  const [showAddAutoTransfer, setShowAddAutoTransfer] = useState(false);

  const { data: assets = [] } = useAssets();
  const { data: summary, isLoading: summaryLoading } = useAssetSummary();
  const { data: txData } = useTransactions({ page: txPage, per_page: 10 });
  const { data: autoTransfers = [] } = useAutoTransfers();

  const createAsset = useCreateAsset();
  const updateAsset = useUpdateAsset();
  const deleteAsset = useDeleteAsset();
  const deleteTx = useDeleteTransaction();
  const refreshPrice = useRefreshPrice();
  const refreshAll = useRefreshAll();
  const createAutoTransfer = useCreateAutoTransfer();
  const toggleAutoTransfer = useToggleAutoTransfer();
  const deleteAutoTransfer = useDeleteAutoTransfer();

  const editingAsset = useMemo(
    () => (editingAssetId ? assets.find((a) => a.id === editingAssetId) ?? null : null),
    [editingAssetId, assets],
  );

  const [deletingAssetId, setDeletingAssetId] = useState<string | null>(null);
  const [refreshingSymbol, setRefreshingSymbol] = useState<string | null>(null);
  const handleDeleteAsset = useCallback((id: string) => {
    setDeletingAssetId(id);
    deleteAsset.mutate(id, {
      onSettled: () => setDeletingAssetId(null),
    });
  }, [deleteAsset]);
  const handleRefreshPrice = useCallback((symbol: string, assetType: string) => {
    setRefreshingSymbol(symbol);
    refreshPrice.mutate(
      { symbol, asset_type: assetType },
      { onSettled: () => setRefreshingSymbol(null) },
    );
  }, [refreshPrice]);
  const handleDeleteTx = useCallback((id: string) => deleteTx.mutate(id), [deleteTx]);
  const handleOpenAddAsset = useCallback(() => setShowAddAsset(true), []);
  const handleCloseAddAsset = useCallback(() => setShowAddAsset(false), []);
  const handleSubmitAsset = useCallback(
    (data: Parameters<typeof createAsset.mutate>[0]) => {
      createAsset.mutate(data, { onSuccess: () => setShowAddAsset(false) });
    },
    [createAsset],
  );
  const handleEditAsset = useCallback((id: string) => setEditingAssetId(id), []);
  const handleCloseEdit = useCallback(() => setEditingAssetId(null), []);
  const handleSubmitEdit = useCallback(
    (data: AssetUpdateRequest) => {
      if (!editingAssetId) return;
      updateAsset.mutate(
        { id: editingAssetId, data },
        { onSuccess: () => setEditingAssetId(null) },
      );
    },
    [editingAssetId, updateAsset],
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
          <div className="flex gap-2">
            <Button
              onClick={() => refreshAll.mutate()}
              size="sm"
              variant="outline"
              disabled={refreshAll.isPending}
            >
              <RefreshCw className={`mr-1.5 h-4 w-4 ${refreshAll.isPending ? 'animate-spin' : ''}`} />
              {refreshAll.isPending ? '새로고침 중...' : '전체 새로고침'}
            </Button>
            <Button onClick={handleOpenAddAsset} size="sm">
              <Plus className="mr-1.5 h-4 w-4" />
              자산 추가
            </Button>
          </div>
        </div>
        <AssetList
          holdings={summary?.holdings || []}
          onEdit={handleEditAsset}
          onDelete={handleDeleteAsset}
          onRefresh={handleRefreshPrice}
          deletingId={deletingAssetId}
          refreshingSymbol={refreshingSymbol}
        />
      </div>

      {/* Auto Transfers */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">자동이체</h2>
          <Button onClick={() => setShowAddAutoTransfer(true)} size="sm">
            <Plus className="mr-1.5 h-4 w-4" />
            자동이체 추가
          </Button>
        </div>
        <AutoTransferList
          autoTransfers={autoTransfers}
          onToggle={(id) => toggleAutoTransfer.mutate(id)}
          onDelete={(id) => deleteAutoTransfer.mutate(id)}
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

      <EditAssetModal
        isOpen={!!editingAssetId}
        onClose={handleCloseEdit}
        onSubmit={handleSubmitEdit}
        asset={editingAsset}
        isLoading={updateAsset.isPending}
      />

      <AddAutoTransferModal
        isOpen={showAddAutoTransfer}
        onClose={() => setShowAddAutoTransfer(false)}
        onSubmit={(data) => {
          createAutoTransfer.mutate(data, {
            onSuccess: () => setShowAddAutoTransfer(false),
          });
        }}
        assets={assets}
        isLoading={createAutoTransfer.isPending}
      />
    </div>
  );
}
