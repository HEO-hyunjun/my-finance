import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  Income,
  IncomeCreateRequest,
  IncomeSummary,
} from '@/shared/types';

export const incomeKeys = {
  all: ['incomes'] as const,
  list: (filters?: Record<string, unknown>) =>
    [...incomeKeys.all, 'list', filters] as const,
  summary: () => [...incomeKeys.all, 'summary'] as const,
};

export interface IncomeFilters {
  is_recurring?: boolean;
  type?: string;
}

interface IncomeListResponse {
  data: Income[];
  total: number;
  page: number;
  per_page: number;
}

export function useIncomes(filters: IncomeFilters = {}) {
  return useQuery({
    queryKey: incomeKeys.list(filters as Record<string, unknown>),
    queryFn: async () => {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
      const { data } = await apiClient.get<IncomeListResponse>(
        `/v1/incomes?${params.toString()}`,
      );
      return data.data;
    },
  });
}

export function useIncomeSummary() {
  return useQuery({
    queryKey: incomeKeys.summary(),
    queryFn: async () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1)
        .toISOString()
        .slice(0, 10);
      const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
        .toISOString()
        .slice(0, 10);
      const { data } = await apiClient.get<IncomeSummary>(
        `/v1/incomes/summary?start=${start}&end=${end}`,
      );
      return data;
    },
  });
}

export function useCreateIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: IncomeCreateRequest) => {
      const { data: result } = await apiClient.post<Income>(
        '/v1/incomes',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: incomeKeys.all });
    },
  });
}

export function useDeleteIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/incomes/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: incomeKeys.all });
    },
  });
}
