import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  RecurringIncome,
  RecurringIncomeCreateRequest,
  RecurringIncomeUpdateRequest,
  IncomeSummary,
} from '@/shared/types';

export const recurringIncomeKeys = {
  all: ['recurring-incomes'] as const,
  list: () => [...recurringIncomeKeys.all, 'list'] as const,
  summary: () => [...recurringIncomeKeys.all, 'summary'] as const,
};

export function useRecurringIncomes() {
  return useQuery({
    queryKey: recurringIncomeKeys.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<RecurringIncome[]>(
        '/v1/recurring-incomes',
      );
      return data;
    },
  });
}

export function useIncomeSummary() {
  return useQuery({
    queryKey: recurringIncomeKeys.summary(),
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

export function useCreateRecurringIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: RecurringIncomeCreateRequest) => {
      const { data: result } = await apiClient.post<RecurringIncome>(
        '/v1/recurring-incomes',
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: recurringIncomeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['income'] });
    },
  });
}

export function useUpdateRecurringIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: RecurringIncomeUpdateRequest }) => {
      const { data: result } = await apiClient.put<RecurringIncome>(
        `/v1/recurring-incomes/${id}`,
        data,
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: recurringIncomeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['income'] });
    },
  });
}

export function useDeleteRecurringIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/recurring-incomes/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: recurringIncomeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['income'] });
    },
  });
}

export function useToggleRecurringIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.patch<RecurringIncome>(
        `/v1/recurring-incomes/${id}/toggle`,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: recurringIncomeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['income'] });
    },
  });
}
