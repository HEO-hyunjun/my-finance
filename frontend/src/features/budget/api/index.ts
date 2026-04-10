import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/shared/api/client';
import type {
  BudgetOverview, CategoryBudget, AllocationCreate, AllocationUpdate,
  PeriodSettingUpdate, BudgetAnalysis,
} from '@/entities/budget/model/types';

function getErrorMsg(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const resp = (error as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail || fallback;
  }
  return fallback;
}

const budgetKeys = {
  all: ['budget'] as const,
  overview: () => [...budgetKeys.all, 'overview'] as const,
  categories: () => [...budgetKeys.all, 'categories'] as const,
  period: () => [...budgetKeys.all, 'period'] as const,
  analysis: (start?: string, end?: string) => [...budgetKeys.all, 'analysis', start, end] as const,
};

export function useBudgetOverview() {
  return useQuery({
    queryKey: budgetKeys.overview(),
    queryFn: async () => {
      const { data } = await apiClient.get<BudgetOverview>('/v1/budget/overview');
      return data;
    },
  });
}

export function useBudgetCategories() {
  return useQuery({
    queryKey: budgetKeys.categories(),
    queryFn: async () => {
      const { data } = await apiClient.get<CategoryBudget[]>('/v1/budget/categories');
      return data;
    },
  });
}

export function useCreateAllocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AllocationCreate) => {
      const { data } = await apiClient.post('/v1/budget/allocations', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: budgetKeys.categories() });
      qc.invalidateQueries({ queryKey: budgetKeys.overview() });
      toast.success('예산이 배분되었습니다');
    },
    onError: (e) => { toast.error(getErrorMsg(e, '예산 배분 실패')); },
  });
}

export function useUpdateAllocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: AllocationUpdate & { id: string }) => {
      const { data } = await apiClient.patch(`/v1/budget/allocations/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: budgetKeys.categories() });
      qc.invalidateQueries({ queryKey: budgetKeys.overview() });
      toast.success('배분이 수정되었습니다');
    },
    onError: (e) => { toast.error(getErrorMsg(e, '배분 수정 실패')); },
  });
}

export function useDeleteAllocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => { await apiClient.delete(`/v1/budget/allocations/${id}`); },
    onSuccess: () => { qc.invalidateQueries({ queryKey: budgetKeys.all }); toast.success('배분이 삭제되었습니다'); },
    onError: (e) => { toast.error(getErrorMsg(e, '배분 삭제 실패')); },
  });
}

export function useBudgetPeriod() {
  return useQuery({
    queryKey: budgetKeys.period(),
    queryFn: async () => {
      const { data } = await apiClient.get<{ period_start_day: number }>('/v1/budget/period');
      return data;
    },
  });
}

export function useUpdateBudgetPeriod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: PeriodSettingUpdate) => {
      const { data } = await apiClient.patch('/v1/budget/period', payload);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: budgetKeys.all }); toast.success('예산 기간이 변경되었습니다'); },
    onError: (e) => { toast.error(getErrorMsg(e, '기간 변경 실패')); },
  });
}

export function useBudgetAnalysis(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: budgetKeys.analysis(startDate, endDate),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (startDate) params.set('start_date', startDate);
      if (endDate) params.set('end_date', endDate);
      const { data } = await apiClient.get<BudgetAnalysis>('/v1/budget/analysis', { params });
      return data;
    },
  });
}

export { budgetKeys };
