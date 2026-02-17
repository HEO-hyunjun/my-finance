import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type { BudgetAnalysis } from '@/shared/types';

export const budgetAnalysisKeys = {
  all: ['budget-analysis'] as const,
  current: () => [...budgetAnalysisKeys.all, 'current'] as const,
};

export function useBudgetAnalysis() {
  return useQuery({
    queryKey: budgetAnalysisKeys.current(),
    queryFn: async (): Promise<BudgetAnalysis> => {
      const { data } = await apiClient.get('/v1/budget/analysis');
      return data;
    },
  });
}
