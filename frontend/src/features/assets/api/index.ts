import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  Asset,
  AssetCreateRequest,
  AssetUpdateRequest,
  AssetHolding,
  AssetSummary,
  Transaction,
  TransactionCreateRequest,
  TransactionUpdateRequest,
  PaginatedResponse,
  TransferRequest,
  AutoTransfer,
  AutoTransferCreateRequest,
} from '@/shared/types';

// --- Types ---

interface TransactionFilters {
  asset_id?: string;
  asset_type?: string;
  type?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  per_page?: number;
}

// --- Query Keys ---

export const assetKeys = {
  all: ['assets'] as const,
  list: () => [...assetKeys.all, 'list'] as const,
  detail: (id: string) => [...assetKeys.all, 'detail', id] as const,
  summary: () => [...assetKeys.all, 'summary'] as const,
};

export const transactionKeys = {
  all: ['transactions'] as const,
  list: (filters?: TransactionFilters) =>
    [...transactionKeys.all, 'list', filters] as const,
};

// --- Asset Queries ---

export function useAssets() {
  return useQuery({
    queryKey: assetKeys.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<Asset[]>('/v1/assets');
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useAssetDetail(id: string) {
  return useQuery({
    queryKey: assetKeys.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.get<AssetHolding>(`/v1/assets/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useAssetSummary() {
  return useQuery({
    queryKey: assetKeys.summary(),
    queryFn: async () => {
      const { data } = await apiClient.get<AssetSummary>('/v1/assets/summary');
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

// --- Transaction Queries ---

export function useTransactions(filters: TransactionFilters = {}) {
  return useQuery({
    queryKey: transactionKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
      const { data } = await apiClient.get<PaginatedResponse<Transaction>>(
        `/v1/transactions?${params.toString()}`,
      );
      return data;
    },
  });
}

// --- Price Refresh ---

export function useRefreshPrice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ symbol, asset_type }: { symbol: string; asset_type?: string }) => {
      const { data } = await apiClient.post('/v1/market/refresh-price', {
        symbol,
        asset_type,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assetKeys.summary() });
    },
  });
}

export function useRefreshExchangeRate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post('/v1/market/refresh-exchange-rate');
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assetKeys.summary() });
    },
  });
}

export function useRefreshAll() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post<{ success: number; failed: number; total: number }>(
        '/v1/market/refresh-all',
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// --- Mutations ---

export function useCreateAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: AssetCreateRequest) => {
      const { data: result } = await apiClient.post<Asset>('/v1/assets', data);
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
    },
  });
}

export function useUpdateAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: AssetUpdateRequest }) => {
      const { data: result } = await apiClient.patch<Asset>(`/v1/assets/${id}`, data);
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
    },
  });
}

export function useDeleteAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/assets/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
    },
  });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: TransactionCreateRequest) => {
      const { data: result } = await apiClient.post<Transaction>(
        '/v1/transactions',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transactionKeys.all });
      queryClient.invalidateQueries({ queryKey: assetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
    },
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: TransactionUpdateRequest;
    }) => {
      const { data: result } = await apiClient.put<Transaction>(
        `/v1/transactions/${id}`,
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transactionKeys.all });
      queryClient.invalidateQueries({ queryKey: assetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
    },
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/transactions/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transactionKeys.all });
      queryClient.invalidateQueries({ queryKey: assetKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
    },
  });
}

// --- Transfer ---

export const transferKeys = {
  all: ['transfers'] as const,
  autoList: () => [...transferKeys.all, 'auto'] as const,
};

export function useTransfer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: TransferRequest) => {
      const { data: result } = await apiClient.post('/v1/transfers', data);
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assetKeys.all });
      queryClient.invalidateQueries({ queryKey: transactionKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useAutoTransfers() {
  return useQuery({
    queryKey: transferKeys.autoList(),
    queryFn: async () => {
      const { data } = await apiClient.get<AutoTransfer[]>('/v1/transfers/auto');
      return data;
    },
  });
}

export function useCreateAutoTransfer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: AutoTransferCreateRequest) => {
      const { data: result } = await apiClient.post<AutoTransfer>(
        '/v1/transfers/auto',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transferKeys.autoList() });
    },
  });
}

export function useToggleAutoTransfer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data: result } = await apiClient.patch<AutoTransfer>(
        `/v1/transfers/auto/${id}/toggle`,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transferKeys.autoList() });
    },
  });
}

export function useDeleteAutoTransfer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/transfers/auto/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transferKeys.autoList() });
    },
  });
}
