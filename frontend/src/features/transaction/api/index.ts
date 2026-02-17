import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type { Transaction, PaginatedResponse } from '@/shared/types';

// --- Types ---

export interface TransactionFilters {
  asset_type?: string;
  tx_type?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  per_page?: number;
}

// --- Query Keys ---

export const transactionKeys = {
  all: ['transactions'] as const,
  list: (filters: TransactionFilters) =>
    [...transactionKeys.all, 'list', filters] as const,
};

// --- Queries ---

export function useFilteredTransactions(filters: TransactionFilters = {}) {
  return useQuery({
    queryKey: transactionKeys.list(filters),
    queryFn: async (): Promise<PaginatedResponse<Transaction>> => {
      const params = new URLSearchParams();
      if (filters.asset_type) params.set('asset_type', filters.asset_type);
      if (filters.tx_type) params.set('tx_type', filters.tx_type);
      if (filters.start_date) params.set('start_date', filters.start_date);
      if (filters.end_date) params.set('end_date', filters.end_date);
      params.set('page', String(filters.page || 1));
      params.set('per_page', String(filters.per_page || 20));
      const { data } = await apiClient.get<PaginatedResponse<Transaction>>(
        `/v1/transactions?${params.toString()}`,
      );
      return data;
    },
  });
}
