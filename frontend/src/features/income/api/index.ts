import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/shared/api/client';
import type { AxiosError } from 'axios';
import type {
  Income,
  IncomeCreateRequest,
  IncomeUpdateRequest,
  IncomeSummary,
  PaginatedResponse,
} from '@/shared/types';

function getErrorMsg(error: unknown): string {
  const e = error as AxiosError<{ detail?: string }>;
  return e?.response?.data?.detail || '요청 처리 중 오류가 발생했습니다.';
}

// Query Keys

export const incomeKeys = {
  all: ['income'] as const,
  list: () => [...incomeKeys.all, 'list'] as const,
  listFiltered: (filters: Record<string, unknown>) =>
    [...incomeKeys.list(), filters] as const,
  summary: (start?: string, end?: string) =>
    [...incomeKeys.all, 'summary', start, end] as const,
};

// --- List Hook ---

export interface IncomeFilters {
  income_type?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  per_page?: number;
}

export function useIncomes(filters: IncomeFilters = {}) {
  return useQuery({
    queryKey: incomeKeys.listFiltered(filters as Record<string, unknown>),
    queryFn: async () => {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
      const { data } = await apiClient.get<PaginatedResponse<Income>>(
        `/v1/incomes?${params.toString()}`,
      );
      return data;
    },
  });
}

// --- Summary Hook ---

export interface IncomeSummaryFilters {
  start?: string;
  end?: string;
}

export function useIncomeSummary(filters: IncomeSummaryFilters = {}) {
  return useQuery({
    queryKey: incomeKeys.summary(filters.start, filters.end),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.start) params.append('start', filters.start);
      if (filters.end) params.append('end', filters.end);
      const { data } = await apiClient.get<IncomeSummary>(
        `/v1/incomes/summary?${params.toString()}`,
      );
      return data;
    },
  });
}

// --- Create Hook ---

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
      toast.success('수입이 추가되었습니다.');
      queryClient.invalidateQueries({ queryKey: incomeKeys.list() });
      queryClient.invalidateQueries({ queryKey: incomeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: (error) => toast.error(getErrorMsg(error)),
  });
}

// --- Update Hook ---

export function useUpdateIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: IncomeUpdateRequest;
    }) => {
      const { data: result } = await apiClient.put<Income>(
        `/v1/incomes/${id}`,
        data,
      );
      return result;
    },
    onSuccess: () => {
      toast.success('수입이 수정되었습니다.');
      queryClient.invalidateQueries({ queryKey: incomeKeys.list() });
      queryClient.invalidateQueries({ queryKey: incomeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: (error) => toast.error(getErrorMsg(error)),
  });
}

// --- Delete Hook ---

export function useDeleteIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/incomes/${id}`);
    },
    onSuccess: () => {
      toast.success('수입이 삭제되었습니다.');
      queryClient.invalidateQueries({ queryKey: incomeKeys.list() });
      queryClient.invalidateQueries({ queryKey: incomeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: (error) => toast.error(getErrorMsg(error)),
  });
}
