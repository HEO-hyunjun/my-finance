import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type { AIInsightsResponse, DashboardSummaryResponse } from '@/shared/types';

export const dashboardKeys = {
  all: ['dashboard'] as const,
  summary: () => [...dashboardKeys.all, 'summary'] as const,
  insights: () => [...dashboardKeys.all, 'insights'] as const,
};

export function useDashboardSummary() {
  return useQuery({
    queryKey: dashboardKeys.summary(),
    queryFn: async (): Promise<DashboardSummaryResponse> => {
      const { data } = await apiClient.get('/v1/dashboard/summary');
      return data;
    },
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
  });
}

export function useDashboardInsights() {
  return useQuery({
    queryKey: dashboardKeys.insights(),
    queryFn: async (): Promise<AIInsightsResponse> => {
      const { data } = await apiClient.get('/v1/dashboard/insights');
      return data;
    },
    staleTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}
